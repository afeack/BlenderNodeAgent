"""
长期记忆与短期记忆系统
"""

__all__ = [
    'memory_manager',
    'MemoryDatabase',
    'memory_extractor',
    'VectorSearchEngine',
    'EmbeddingAPI'
]

# 延迟导入以避免循环依赖
def __getattr__(name):
    if name == 'memory_manager':
        from internal.memory.manager import memory_manager
        return memory_manager
    elif name == 'MemoryDatabase':
        from internal.memory.db_models import MemoryDatabase
        return MemoryDatabase
    elif name == 'memory_extractor':
        from internal.memory.extractor import memory_extractor
        return memory_extractor
    elif name == 'VectorSearchEngine':
        from internal.memory.vector_search import VectorSearchEngine
        return VectorSearchEngine
    elif name == 'EmbeddingAPI':
        from internal.memory.vector_search import EmbeddingAPI
        return EmbeddingAPI
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
