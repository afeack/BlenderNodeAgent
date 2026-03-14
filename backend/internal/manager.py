# manager.py
from langchain_community.chat_message_histories import ChatMessageHistory
from typing import Dict, Any, List
from internal.config.settings import settings
from internal.memory.manager import MemoryManager
from langchain_core.messages import BaseMessage
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        # 存储对话历史：{ "会话ID": ChatMessageHistory }
        self.sessions: Dict[str, ChatMessageHistory] = {}
        # 存储材质快照：{ "会话ID": MaterialGraph对象 }
        self.last_graphs: Dict[str, Any] = {}
        self.current_session_id = "Default_Material"
        
        # 集成长期+短期记忆管理系统
        self.memory_manager = MemoryManager()
        self.settings = settings
        
        logger.info("[OK] SessionManager initialized, long-term memory system activated")

    def get_current_history(self) -> ChatMessageHistory:
        """获取当前会话的历史记录"""
        if self.current_session_id not in self.sessions:
            self.sessions[self.current_session_id] = ChatMessageHistory()
        return self.sessions[self.current_session_id]

    def get_current_graph(self):
        """获取当前会话最后一次生成的材质 JSON (用于注入 Context)"""
        graph = self.last_graphs.get(self.current_session_id)
        # 如果存在快照，返回其字典格式
        if not graph:
            return None
        # 优先使用 model_dump（pydantic v2），否则 fallback 到其他方式
        if hasattr(graph, 'model_dump'):
            try:
                return self._convert_to_frontend_format(graph.model_dump())
            except Exception:
                pass
        if hasattr(graph, 'json'):
            try:
                import json
                graph_dict = json.loads(graph.json())
                return self._convert_to_frontend_format(graph_dict)
            except Exception:
                pass
        return self._convert_to_frontend_format(graph)

    def update_graph(self, graph_obj):
        """更新当前会话的材质快照"""
        self.last_graphs[self.current_session_id] = graph_obj

    def switch_session(self, session_id: str):
        """切换会话"""
        self.current_session_id = session_id
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatMessageHistory()
        
        # 同时在内存管理器中切换会话
        self.memory_manager.switch_session(session_id)
        
        return f"[OK] Switched to project: {session_id}"

    def list_sessions(self):
        """列出所有项目"""
        return list(self.sessions.keys())

    def clear_current(self):
        """重置当前项目"""
        if self.current_session_id in self.sessions:
            self.sessions[self.current_session_id].clear()
        if self.current_session_id in self.last_graphs:
            del self.last_graphs[self.current_session_id]
        
        # 同时清空该会话的短期记忆
        self.memory_manager.clear_short_term(self.current_session_id)
        
        return f"[OK] Project '{self.current_session_id}' memory and snapshot have been reset"

    def get_graph(self, session_id: str):
        """按会话 ID 获取材质快照（返回可序列化结构或 None）"""
        graph = self.last_graphs.get(session_id)
        if not graph:
            return None
        # 优先使用 model_dump（pydantic v2），否则 fallback 到其他方式
        if hasattr(graph, 'model_dump'):
            try:
                return self._convert_to_frontend_format(graph.model_dump())
            except Exception:
                pass
        if hasattr(graph, 'json'):
            try:
                import json
                graph_dict = json.loads(graph.json())
                return self._convert_to_frontend_format(graph_dict)
            except Exception:
                pass
        return self._convert_to_frontend_format(graph)
    
    def _convert_to_frontend_format(self, graph_data: any):
        """将材质数据转换为前端期望的格式"""
        if not graph_data:
            return None
        
        # 确保返回的结构包含前端需要的字段
        frontend_format = {
            "material_name": graph_data.get("material_name", "UnnamedMaterial"),
            "nodes": graph_data.get("nodes", []),
            "connections": graph_data.get("connections", [])
        }
        
        # 确保每个节点都有必要的字段
        for node in frontend_format["nodes"]:
            if "node_id" not in node:
                node["node_id"] = f"node_{id(node)}"
            if "node_type" not in node:
                node["node_type"] = "ShaderNodeBsdfPrincipled"
            if "properties" not in node:
                node["properties"] = []
        
        # 确保每个连接都有必要的字段
        for conn in frontend_format["connections"]:
            required_fields = ["from_node", "from_socket", "to_node", "to_socket"]
            for field in required_fields:
                if field not in conn:
                    conn[field] = ""
        
        return frontend_format
    
    def add_message(self, role: str, content: str):
        """添加消息到当前会话的记忆系统
        
        Args:
            role: "user" 或 "assistant"
            content: 消息内容
        """
        # 添加到短期记忆
        self.memory_manager.add_short_term_message(
            session_id=self.current_session_id,
            speaker=role,
            content=content
        )
        
        # 同时保持向后兼容性
        history = self.get_current_history()
        if role == "user":
            from langchain_core.messages import HumanMessage
            history.add_user_message(content)
        else:
            from langchain_core.messages import AIMessage
            history.add_ai_message(content)
    
    def get_agent_context(self) -> Dict[str, Any]:
        """为 Agent 准备增强的上下文（包含长期+短期记忆）
        
        Returns:
            包含对话历史和相关历史记忆的上下文字典
        """
        try:
            # 降级：返回基础对话历史
            return {"messages": self.get_current_history().messages}
        except Exception as e:
            logger.error(f"[ERROR] Failed to get Agent context: {str(e)}")
            # 降级：返回基础对话历史
            return {"messages": self.get_current_history().messages}
    
    def check_and_archive(self) -> bool:
        """检查是否需要归档到长期记忆
        
        Returns:
            True 表示执行了归档，False 表示未超过阈值
        """
        try:
            stats = self.memory_manager.get_session_stats(self.current_session_id)
            
            # 检查轮数是否超过阈值
            user_turns = stats.get('user_turns', 0)
            if user_turns >= self.settings.ARCHIVE_THRESHOLD:
                logger.info(f"⏳ 触发长期记忆归档（轮数: {user_turns}）")
                self.memory_manager.archive_to_long_term(self.current_session_id)
                return True
            
            return False
        except Exception as e:
            logger.error(f"[ERROR] Archive check failed: {str(e)}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取当前会话的记忆统计
        
        Returns:
            包含轮数、token数等统计信息的字典
        """
        try:
            stats = self.memory_manager.get_session_stats(self.current_session_id)
            return {
                "turn_count": stats.turn_count,
                "token_count": stats.token_count,
                "messages_count": len(stats.messages),
                "last_updated": stats.last_updated.isoformat() if stats.last_updated else None
            }
        except Exception as e:
            logger.error(f"[ERROR] Failed to get memory statistics: {str(e)}")
            return {}


# 全局单例供 main.py 使用
session_manager = SessionManager()