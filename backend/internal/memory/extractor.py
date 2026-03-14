"""
使用 LLM 从对话中提取长期记忆信息
"""

import json
import hashlib
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from internal.config.settings import settings


class MemoryExtractor:
    """使用LLM提取关键信息到长期记忆"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            openai_api_key=settings.DASHSCOPE_API_KEY,
            openai_api_base=settings.DASHSCOPE_API_BASE,
            temperature=0,
            max_tokens=2000
        )
    
    def extract_memories(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        从对话消息中提取长期记忆
        
        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}, ...]
        
        Returns:
            {"materials": [...], "recipes": [...], "preferences": [...], "summary": "..."}
        """
        # 将消息转换为文本格式
        conversation_text = self._messages_to_text(messages)
        
        # 构建提示词
        extraction_prompt = f"""
你是一个智能信息提取系统。请从下面的对话中提取以下信息，并以 JSON 格式返回：

【对话内容】
{conversation_text}

【提取任务】
请从上面的对话中提取：
1. materials: 用户涉及的材质信息，格式为 [{{"name": "gold", "properties": {{"ior": 0.47, "metallic": 1.0, ...}}, "description": "..."}}]
2. recipes: 生成的节点配方或操作步骤，格式为 [{{"name": "...", "description": "...", "tags": ["tag1", "tag2"]}}]
3. preferences: 用户的设计偏好，格式为 [{{"key": "color_preference", "value": "warm_tones", "confidence": 0.9}}]
4. summary: 对话的核心摘要，200字以内

【重要提示】
- 仅提取对话中明确提及的信息
- 对于不确定的信息，设置 confidence < 0.6
- 返回有效的 JSON 格式
- 如果某类信息不存在，返回空数组

请直接返回 JSON，不要包含其他文字。
"""
        
        try:
            response = self.llm.invoke(extraction_prompt)
            result_text = response.content.strip()
            
            # 尝试解析 JSON
            extracted = json.loads(result_text)
            
            print(f"[OK] Memory extraction successful: materials={len(extracted.get('materials', []))}, "
                  f"recipes={len(extracted.get('recipes', []))}, "
                  f"preferences={len(extracted.get('preferences', []))}")
            
            return extracted
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 解析失败: {e}")
            print(f"原始响应: {result_text[:200]}")
            return {"materials": [], "recipes": [], "preferences": [], "summary": ""}
        except Exception as e:
            print(f"[ERROR] Memory extraction failed: {e}")
            return {"materials": [], "recipes": [], "preferences": [], "summary": ""}
    
    def extract_materials_only(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """仅提取材质信息"""
        memories = self.extract_memories(messages)
        return memories.get("materials", [])
    
    def extract_recipes_only(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """仅提取配方信息"""
        memories = self.extract_memories(messages)
        return memories.get("recipes", [])
    
    def extract_preferences_only(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """仅提取偏好信息"""
        memories = self.extract_memories(messages)
        return memories.get("preferences", [])
    
    def _messages_to_text(self, messages: List[Dict[str, str]]) -> str:
        """将消息列表转换为可读的文本"""
        text_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                text_parts.append(f"用户: {content}")
            elif role == "assistant":
                text_parts.append(f"AI: {content}")
            else:
                text_parts.append(f"{role}: {content}")
        return "\n".join(text_parts)
    
    @staticmethod
    def _hash_content(content: str) -> str:
        """计算内容哈希（用于向量去重）"""
        return hashlib.md5(content.encode()).hexdigest()


# 全局实例
memory_extractor = MemoryExtractor()
