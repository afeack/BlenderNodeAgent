"""
长期记忆数据库模型和操作
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading

class MemoryDatabase:
    """SQLite 长期记忆数据库管理"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.local = threading.local()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地数据库连接"""
        if not hasattr(self.local, 'connection') or self.local.connection is None:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            self.local.connection = conn
        return self.local.connection
    
    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 表1: 材质库
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS material_library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                material_name TEXT NOT NULL,
                properties JSON,
                frequency INTEGER DEFAULT 1,
                access_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, material_name)
            )
        ''')
        
        # 表2: 节点配方
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS node_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                recipe_name TEXT NOT NULL,
                description TEXT,
                nodes_config JSON,
                connections JSON,
                tags TEXT,
                rating FLOAT DEFAULT 0,
                frequency INTEGER DEFAULT 1,
                access_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 表3: 对话摘要
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                summary_text TEXT,
                key_decisions JSON,
                materials_used JSON,
                nodes_created JSON,
                date_start TIMESTAMP,
                date_end TIMESTAMP,
                frequency INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 表4: 用户偏好
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value JSON,
                confidence_score FLOAT DEFAULT 0.8,
                frequency INTEGER DEFAULT 1,
                access_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, preference_key)
            )
        ''')
        
        # 表5: 嵌入向量 (用于向量搜索)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,  -- "material", "recipe", "summary", "preference"
                memory_id INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                embedding JSON,  -- 存储向量数组
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(memory_type, memory_id)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_material_session ON material_library(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipe_session ON node_recipes(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summary_session ON chat_summary(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_preference_session ON user_preferences(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_embedding_session ON embeddings(session_id)')
        
        conn.commit()
        print("[OK] 长期记忆数据库初始化成功")
    
    # ==================== 材质库操作 ====================
    
    def insert_material(self, session_id: str, material_name: str, properties: Dict) -> bool:
        """插入或更新材质库"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO material_library (session_id, material_name, properties)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id, material_name) DO UPDATE SET
                    properties = excluded.properties,
                    frequency = frequency + 1,
                    access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            ''', (session_id, material_name, json.dumps(properties)))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] 插入材质库失败: {e}")
            return False
    
    def query_materials(self, session_id: str, limit: int = 10) -> List[Dict]:
        """查询会话的材质库"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, material_name, properties, frequency, last_accessed
                FROM material_library
                WHERE session_id = ?
                ORDER BY frequency DESC, last_accessed DESC
                LIMIT ?
            ''', (session_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询材质库失败: {e}")
            return []
    
    # ==================== 节点配方操作 ====================
    
    def insert_recipe(self, session_id: str, recipe_name: str, 
                      description: str, nodes_config: Dict, 
                      connections: List, tags: str = "") -> bool:
        """插入节点配方"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO node_recipes 
                (session_id, recipe_name, description, nodes_config, connections, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, recipe_name, description, 
                  json.dumps(nodes_config), json.dumps(connections), tags))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] 插入配方失败: {e}")
            return False
    
    def query_recipes(self, session_id: str, tags: List[str] = None, limit: int = 10) -> List[Dict]:
        """查询节点配方"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if tags:
                # 按标签查询
                placeholders = ','.join(['?' for _ in tags])
                cursor.execute(f'''
                    SELECT id, recipe_name, description, nodes_config, connections, tags, frequency
                    FROM node_recipes
                    WHERE session_id = ? AND (
                        {' OR '.join([f"tags LIKE ?" for _ in tags])}
                    )
                    ORDER BY frequency DESC, last_accessed DESC
                    LIMIT ?
                ''', [session_id] + [f'%{tag}%' for tag in tags] + [limit])
            else:
                cursor.execute('''
                    SELECT id, recipe_name, description, nodes_config, connections, tags, frequency
                    FROM node_recipes
                    WHERE session_id = ?
                    ORDER BY frequency DESC, last_accessed DESC
                    LIMIT ?
                ''', (session_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询配方失败: {e}")
            return []
    
    # ==================== 对话摘要操作 ====================
    
    def insert_summary(self, session_id: str, summary_text: str,
                      key_decisions: Dict = None, materials_used: List = None) -> bool:
        """插入对话摘要"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO chat_summary 
                (session_id, summary_text, key_decisions, materials_used, date_start, date_end)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (session_id, summary_text, 
                  json.dumps(key_decisions or {}), 
                  json.dumps(materials_used or [])))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] 插入摘要失败: {e}")
            return False
    
    def query_summaries(self, session_id: str, limit: int = 5) -> List[Dict]:
        """查询对话摘要"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, summary_text, key_decisions, materials_used, created_at
                FROM chat_summary
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (session_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询摘要失败: {e}")
            return []
    
    # ==================== 用户偏好操作 ====================
    
    def insert_preference(self, session_id: str, preference_key: str, 
                         preference_value: Dict, confidence_score: float = 0.8) -> bool:
        """插入或更新用户偏好"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO user_preferences 
                (session_id, preference_key, preference_value, confidence_score)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, preference_key) DO UPDATE SET
                    preference_value = excluded.preference_value,
                    confidence_score = excluded.confidence_score,
                    frequency = frequency + 1,
                    access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            ''', (session_id, preference_key, json.dumps(preference_value), confidence_score))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] 插入偏好失败: {e}")
            return False
    
    def query_preferences(self, session_id: str, limit: int = 10) -> List[Dict]:
        """查询用户偏好"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT preference_key, preference_value, confidence_score, frequency
                FROM user_preferences
                WHERE session_id = ?
                ORDER BY frequency DESC, confidence_score DESC
                LIMIT ?
            ''', (session_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询偏好失败: {e}")
            return []
    
    # ==================== 向量操作 ====================
    
    def insert_embedding(self, memory_type: str, memory_id: int, 
                        content_hash: str, embedding: List[float]) -> bool:
        """插入向量嵌入"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO embeddings (memory_type, memory_id, content_hash, embedding)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(memory_type, memory_id) DO UPDATE SET
                    embedding = excluded.embedding,
                    updated_at = CURRENT_TIMESTAMP
            ''', (memory_type, memory_id, content_hash, json.dumps(embedding)))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] 插入向量失败: {e}")
            return False
    
    def query_embedding(self, memory_type: str, memory_id: int) -> Optional[List[float]]:
        """查询向量"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT embedding FROM embeddings
                WHERE memory_type = ? AND memory_id = ?
            ''', (memory_type, memory_id))
            result = cursor.fetchone()
            if result:
                return json.loads(result['embedding'])
            return None
        except Exception as e:
            print(f"[ERROR] 查询向量失败: {e}")
            return None
    
    # ==================== 清理操作 ====================
    
    def cleanup_old_records(self, retention_days: int = 90, min_frequency: int = 5) -> int:
        """清理旧的、不常访问的记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
        
        deleted_count = 0
        try:
            # 清理旧的材质库记录
            cursor.execute('''
                DELETE FROM material_library
                WHERE date(last_accessed) < date(?)
                AND frequency < ?
            ''', (cutoff_date, min_frequency))
            deleted_count += cursor.rowcount
            
            # 清理旧的配方记录
            cursor.execute('''
                DELETE FROM node_recipes
                WHERE date(last_accessed) < date(?)
                AND frequency < ?
            ''', (cutoff_date, min_frequency))
            deleted_count += cursor.rowcount
            
            # 清理旧的偏好记录
            cursor.execute('''
                DELETE FROM user_preferences
                WHERE date(last_accessed) < date(?)
                AND frequency < ?
            ''', (cutoff_date, min_frequency))
            deleted_count += cursor.rowcount
            
            conn.commit()
            print(f"🧹 清理了 {deleted_count} 条旧记录")
            return deleted_count
        except Exception as e:
            print(f"[ERROR] 清理旧记录失败: {e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self.local, 'connection') and self.local.connection:
            self.local.connection.close()
            self.local.connection = None
