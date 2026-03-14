"""
长期记忆数据库初始化脚本
"""

import os
import logging
from internal.memory.db_models import MemoryDatabase
from internal.config.settings import settings

logger = logging.getLogger(__name__)

def init_memory_database():
    """初始化长期记忆数据库
    
    - 创建数据库文件（如果不存在）
    - 创建必要的表和索引
    - 设置初始配置
    """
    db_path = settings.LONG_TERM_DB_PATH
    
    try:
        # 确保数据库目录存在
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        # 初始化数据库 (MemoryDatabase 在 __init__ 中自动初始化)
        db = MemoryDatabase(db_path)
        
        logger.info(f"[OK] Long-term memory database initialized: {db_path}")
        
        # 记录数据库信息
        db_exists = os.path.exists(db_path)
        db_size = os.path.getsize(db_path) if db_exists else 0
        logger.info(f"[INFO] Database file size: {db_size} bytes")
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Long-term memory database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    # 直接运行此脚本来初始化数据库
    logging.basicConfig(level=logging.INFO)
    init_memory_database()
    print("[OK] Database initialization completed")
