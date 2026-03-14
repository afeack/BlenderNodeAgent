"""
统一的记忆管理器 - 整合短期和长期记忆
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from internal.config.settings import settings
from internal.memory.db_models import MemoryDatabase
from internal.memory.extractor import memory_extractor
from internal.memory.vector_search import VectorSearchEngine, EmbeddingAPI


@dataclass
class MemoryContext:
    """记忆上下文"""
    short_term: List[Dict[str, Any]]     # 最近的对话
    long_term: Dict[str, Any]             # 长期记忆
    node_graph: Optional[Dict] = None      # 当前节点图


class MemoryManager:
    """统一的记忆管理器"""
    
    def __init__(self):
        # 初始化数据库
        self.db = MemoryDatabase(settings.LONG_TERM_DB_PATH)
        
        # 初始化向量搜索
        embedding_api = None
        if settings.ENABLE_VECTOR_SEARCH:
            embedding_api = EmbeddingAPI(settings.DASHSCOPE_API_KEY, settings.EMBEDDING_MODEL)
        
        self.vector_engine = VectorSearchEngine(self.db, embedding_api)
        self.vector_engine.similarity_threshold = settings.VECTOR_SIMILARITY_THRESHOLD
        
        # 短期记忆存储 (会话隔离)
        self.short_term_memory: Dict[str, List[Dict[str, Any]]] = {}
    
    # ==================== 短期记忆接口 ====================
    
    def add_short_term_message(self, session_id: str, speaker: str, 
                               content: str, tokens: int = 0):
        """添加短期记忆"""
        if session_id not in self.short_term_memory:
            self.short_term_memory[session_id] = []
        
        message = {
            "speaker": speaker,
            "content": content,
            "tokens": tokens,
            "timestamp": self._get_timestamp()
        }
        
        self.short_term_memory[session_id].append(message)
    
    def get_short_term_context(self, session_id: str, max_turns: Optional[int] = None) -> List[Dict]:
        """获取短期记忆上下文"""
        if max_turns is None:
            max_turns = settings.MAX_SHORT_TERM_TURNS
        
        messages = self.short_term_memory.get(session_id, [])
        
        # 返回最近的 max_turns
        return messages[-max_turns:] if len(messages) > max_turns else messages
    
    def should_archive(self, session_id: str) -> bool:
        """检查是否应该归档"""
        messages = self.short_term_memory.get(session_id, [])
        
        # 轮数触发
        num_turns = len([m for m in messages if m['speaker'] == 'user'])
        if num_turns > settings.ARCHIVE_THRESHOLD:
            return True
        
        # Token 触发
        total_tokens = sum(m.get('tokens', 0) for m in messages)
        if total_tokens > settings.MAX_SHORT_TERM_TOKENS:
            return True
        
        return False
    
    async def archive_to_long_term(self, session_id: str) -> bool:
        """将短期记忆归档到长期记忆"""
        if not settings.AUTO_ARCHIVE_ENABLED or not settings.LONG_TERM_MEMORY_ENABLED:
            return False
        
        messages = self.short_term_memory.get(session_id, [])
        if not messages:
            return False
        
        try:
            # 1. 转换为 LLM 格式
            llm_messages = self._convert_to_llm_format(messages)
            
            # 2. 使用 LLM 提取关键信息
            extracted = memory_extractor.extract_memories(llm_messages)
            
            # 3. 存入数据库
            await self._store_extracted_memories(session_id, extracted)
            
            # 4. 清空旧的短期记忆（保留最近的档案）
            archive_count = len(messages) - settings.MAX_SHORT_TERM_TURNS
            if archive_count > 0:
                self.short_term_memory[session_id] = messages[-settings.MAX_SHORT_TERM_TURNS:]
            
            return True
        except Exception:
            return False
    
    async def _store_extracted_memories(self, session_id: str, extracted: Dict[str, Any]):
        """存储提取的记忆"""
        # 存储材质
        for material in extracted.get('materials', []):
            self.db.insert_material(
                session_id,
                material.get('name', ''),
                material.get('properties', {})
            )
        
        # 存储配方
        for recipe in extracted.get('recipes', []):
            self.db.insert_recipe(
                session_id,
                recipe.get('name', ''),
                recipe.get('description', ''),
                recipe.get('nodes_config', {}),
                recipe.get('connections', []),
                recipe.get('tags', '')
            )
        
        # 存储偏好
        for pref in extracted.get('preferences', []):
            self.db.insert_preference(
                session_id,
                pref.get('key', ''),
                pref.get('value', {}),
                pref.get('confidence', 0.8)
            )
        
        # 存储摘要
        if extracted.get('summary'):
            self.db.insert_summary(
                session_id,
                extracted['summary'],
                extracted.get('key_decisions', {}),
                [m.get('name') for m in extracted.get('materials', [])]
            )
    
    # ==================== 长期记忆接口 ====================
    
    async def query_long_term(self, session_id: str, query_type: str = "all",
                             limit: int = 10) -> Dict[str, Any]:
        """查询长期记忆"""
        result = {}
        
        if query_type in ['all', 'material']:
            result['materials'] = self.db.query_materials(session_id, limit)
        
        if query_type in ['all', 'recipe']:
            result['recipes'] = self.db.query_recipes(session_id, limit=limit)
        
        if query_type in ['all', 'preference']:
            result['preferences'] = self.db.query_preferences(session_id, limit)
        
        if query_type in ['all', 'summary']:
            result['summaries'] = self.db.query_summaries(session_id, limit=3)
        
        return result
    
    async def search_long_term(self, query: str, session_id: str,
                              top_k: int = 5) -> Dict[str, Any]:
        """语义搜索长期记忆"""
        search_results = await self.vector_engine.semantic_search(
            query, session_id, top_k=top_k
        )
        
        # 分组结果
        result = {
            'materials': [],
            'recipes': [],
            'preferences': []
        }
        
        for sr in search_results:
            if sr.memory_type == 'material':
                result['materials'].append({
                    'data': sr.data,
                    'score': sr.score
                })
            elif sr.memory_type == 'recipe':
                result['recipes'].append({
                    'data': sr.data,
                    'score': sr.score
                })
            elif sr.memory_type == 'preference':
                result['preferences'].append({
                    'data': sr.data,
                    'score': sr.score
                })
        
        return result
    
    # ==================== 整合接口 ====================
    
    async def get_full_context(self, session_id: str, 
                               node_graph: Optional[Dict] = None) -> MemoryContext:
        """
        为 Agent 准备完整的记忆上下文
        
        包含：
        1. 短期记忆（最近N轮对话）
        2. 长期记忆（关键信息）
        3. 当前节点图
        """
        # 短期记忆
        short_term = self.get_short_term_context(session_id)
        
        # 长期记忆
        long_term_data = await self.query_long_term(session_id, query_type='all')
        
        # 检查是否需要归档
        if self.should_archive(session_id):
            await self.archive_to_long_term(session_id)
        
        return MemoryContext(
            short_term=short_term,
            long_term=long_term_data,
            node_graph=node_graph
        )
    
    async def cleanup_old_memories(self) -> int:
        """清理旧的长期记忆"""
        if not settings.LONG_TERM_MEMORY_ENABLED:
            return 0
        
        return self.db.cleanup_old_records(
            retention_days=settings.MEMORY_RETENTION_DAYS,
            min_frequency=settings.MIN_MEMORY_FREQUENCY
        )
    
    # ==================== 辅助方法 ====================
    
    def switch_session(self, session_id: str):
        """切换到新会话，初始化会话数据"""
        if session_id not in self.short_term_memory:
            self.short_term_memory[session_id] = []
        return session_id
    
    def clear_session(self, session_id: str):
        """清空会话的短期记忆"""
        if session_id in self.short_term_memory:
            self.short_term_memory[session_id] = []
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计信息"""
        messages = self.short_term_memory.get(session_id, [])
        total_tokens = sum(m.get('tokens', 0) for m in messages)
        user_turns = len([m for m in messages if m['speaker'] == 'user'])
        
        return {
            'total_messages': len(messages),
            'user_turns': user_turns,
            'total_tokens': total_tokens,
            'needs_archive': self.should_archive(session_id),
            'short_term_turns_limit': settings.MAX_SHORT_TERM_TURNS,
            'short_term_tokens_limit': settings.MAX_SHORT_TERM_TOKENS
        }
    
    def _convert_to_llm_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """转换为LLM格式"""
        return [
            {
                'role': msg['speaker'],
                'content': msg['content']
            }
            for msg in messages
        ]
    
    @staticmethod
    def _get_timestamp() -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def close(self):
        """关闭资源"""
        self.db.close()


# 全局实例
memory_manager = MemoryManager()
