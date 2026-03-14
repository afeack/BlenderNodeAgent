"""
向量搜索和相似性匹配
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import asyncio


@dataclass
class VectorSearchResult:
    """向量搜索结果"""
    memory_type: str      # "material", "recipe", "summary", "preference"
    memory_id: int
    score: float          # 相似度分数 (0-1)
    data: Dict[str, Any]


class VectorSearchEngine:
    """向量搜索引擎"""
    
    def __init__(self, db, embedding_api=None):
        self.db = db
        self.embedding_api = embedding_api  # 可选的外部 embedding API
        self.similarity_threshold = 0.7
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        获取文本的向量表示
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        if self.embedding_api:
            return await self.embedding_api.embed_texts(texts)
        else:
            # 默认方案：使用简单的 hash 向量（演示用）
            return [self._simple_hash_to_vector(text) for text in texts]
    
    async def semantic_search(self, query: str, session_id: str, 
                             memory_types: List[str] = None,
                             top_k: int = 5) -> List[VectorSearchResult]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            session_id: 会话ID
            memory_types: 要搜索的记忆类型
            top_k: 返回前K个结果
            
        Returns:
            搜索结果列表
        """
        if memory_types is None:
            memory_types = ["material", "recipe", "preference"]
        
        # 获取查询的向量
        query_vector = await self.get_embeddings([query])
        query_vector = query_vector[0] if query_vector else None
        
        if not query_vector:
            return []
        
        results = []
        
        # 在每种记忆类型中搜索
        for memory_type in memory_types:
            if memory_type == "material":
                candidates = self.db.query_materials(session_id, limit=50)
                texts = [f"{m['material_name']}: {m.get('properties', {})}" for m in candidates]
            elif memory_type == "recipe":
                candidates = self.db.query_recipes(session_id, limit=50)
                texts = [f"{r['recipe_name']}: {r.get('description', '')}" for r in candidates]
            elif memory_type == "preference":
                candidates = self.db.query_preferences(session_id, limit=50)
                texts = [f"{p['preference_key']}: {p.get('preference_value', {})}" for p in candidates]
            else:
                continue
            
            # 计算相似度
            candidate_vectors = await self.get_embeddings(texts)
            for i, (candidate, vector) in enumerate(zip(candidates, candidate_vectors)):
                similarity = self._cosine_similarity(query_vector, vector)
                
                if similarity > self.similarity_threshold:
                    result = VectorSearchResult(
                        memory_type=memory_type,
                        memory_id=candidate.get('id', i),
                        score=similarity,
                        data=dict(candidate)
                    )
                    results.append(result)
        
        # 按相似度排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def _simple_hash_to_vector(self, text: str) -> List[float]:
        """
        简单的哈希到向量映射（演示用）
        
        注: 生产环境应使用真实的 embedding API
        """
        import hashlib
        
        # 使用文本的哈希值生成伪向量
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**31))
        return np.random.randn(384).tolist()  # 384维向量


class EmbeddingAPI:
    """嵌入向量API接口（可用新API）"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """
        初始化嵌入API
        
        Args:
            api_key: API密钥
            model: 模型名称 (text-embedding-3-small, text-embedding-3-large等)
        """
        self.api_key = api_key
        self.model = model
        self._client = None
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """获取文本向量"""
        # TODO: 集成真实的 embedding API
        # 示例实现：
        # from openai import AsyncOpenAI
        # client = AsyncOpenAI(api_key=self.api_key)
        # response = await client.embeddings.create(
        #     model=self.model,
        #     input=texts
        # )
        # return [item.embedding for item in response.data]
        
        print(f"⚠️ 使用占位符 embedding API，建议配置真实API")
        # 返回占位符
        import numpy as np
        np.random.seed(42)
        return [np.random.randn(1536).tolist() for _ in texts]
    
    async def embed_single(self, text: str) -> List[float]:
        """获取单个文本向量"""
        result = await self.embed_texts([text])
        return result[0] if result else []
