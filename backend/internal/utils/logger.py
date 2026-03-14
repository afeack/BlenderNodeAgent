# utils/logger.py
import os
import logging
import traceback
from pathlib import Path
from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List, Optional
from internal.config.settings import settings

# --- 1. 日志目录与文件配置 ---
# 优先从 settings 读取，如果没有则默认为项目根目录下的 logs
LOG_DIR = Path(getattr(settings, "LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 确保文件名存在
LOG_FILE_NAME = getattr(settings, "LOG_FILE", "blender_agent.log")
LOG_FILE_PATH = LOG_DIR / LOG_FILE_NAME

# --- 2. 配置文件日志器 ---
file_logger = logging.getLogger("BlenderAgentCompleteLogger")
file_logger.setLevel(logging.INFO)

# 彻底清理旧的 handler，防止在某些 IDE 或环境下重复加载
if file_logger.hasHandlers():
    file_logger.handlers.clear()

file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
# 格式化：包含时间戳和消息
formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
file_logger.addHandler(file_handler)
file_logger.propagate = False 

class BlenderAgentCallbackHandler(BaseCallbackHandler):
    """
    针对 Blender Agent 定制的完整生命周期监控器
    负责记录 Agent 的：思考(Thought) -> 行动(Action) -> 观察(Observation) -> 结果(Final Answer)
    """

    def _log(self, message: str, level: str = "info"):
        """统一输出通道：终端 + 物理文件"""
        print(message)
        if level == "info":
            file_logger.info(message.strip())
        elif level == "error":
            file_logger.error(message.strip())

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any):
        self._log(f"[DEBUG] Chain started with inputs: {inputs}", level="info")

    def on_agent_action(self, action: Any, **kwargs: Any):
        """当 Agent 决定调用工具时触发：记录完整的思考和参数"""
        tool_name = getattr(action, 'tool', 'UnknownTool')
        tool_input = getattr(action, 'tool_input', '')
        
        self._log(f"[DEBUG] Agent action: {tool_name} with input: {tool_input}", level="info")

    def on_tool_end(self, output: str, **kwargs: Any):
        """记录工具返回的原始数据（Observation）"""
        self._log(f"[DEBUG] Tool output: {output[:200]}...", level="info")

    def on_llm_end(self, response: Any, **kwargs: Any):
        """统计 Token 消耗并记录 LLM 原始生成"""
        usage = "N/A"
        try:
            # 兼容多种 Token 统计路径 (适配 LangChain 1.x 与 通义千问插件)
            if hasattr(response, 'llm_output') and response.llm_output:
                usage = response.llm_output.get("token_usage", usage)
            elif hasattr(response, 'generations') and response.generations:
                for gen in response.generations[0]:
                    if hasattr(gen, 'message'):
                        meta = getattr(gen.message, 'response_metadata', {})
                        usage = meta.get("token_usage", gen.message.additional_kwargs.get("token_usage", usage))
                        break
        except:
            usage = "获取统计失败"

        self._log(f"[DEBUG] Token usage: {usage}", level="info")

    def on_agent_finish(self, finish: Any, **kwargs: Any):
        """当 Agent 给出最终答案时触发"""
        output = finish.return_values.get('output', '')
        self._log(f"[DEBUG] Agent finished with output length: {len(output)} chars", level="info")

    def on_chain_error(self, error: Exception, **kwargs: Any):
        if isinstance(error, GeneratorExit):
            return  # 忽略正常退出的信号
        
        err_stack = traceback.format_exc()
        err_type = type(error).__name__
        
        msg = f"\n[ERROR] {err_type}: {str(error)}\n"
        msg += f"Stack trace:\n{err_stack}"
        
        self._log(msg, level="error")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any):
        self._log(f"[DEBUG] Chain ended with outputs keys: {list(outputs.keys())}", level="info")