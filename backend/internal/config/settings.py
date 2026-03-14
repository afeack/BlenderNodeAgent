# config/settings.py


from dotenv import load_dotenv
import os

# 加载 .env 文件（如果存在）
load_dotenv()

class Settings:
    """全局应用配置中心（安全版）"""
    # ✅ 非敏感配置（硬编码）
    MODEL_NAME: str = "qwen3.5-35b-a3b"
    # 增加 OpenAI 兼容入口
    DASHSCOPE_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "NOT_SET")
    MODEL_TEMPERATURE: float = 0  # 生成温度，越低越保守
    MAX_REVISION_ATTEMPTS: int = 3

    # 🌐 服务器配置
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

    # ⚠️ 敏感配置（从 .env 读取，启动时验证）
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "NOT_SET")
    
    # 获取项目根目录 (settings.py 的上一级的上一级)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 定义日志文件夹
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    
    # 仅定义文件名，不要在 settings 里用 getcwd() 锁死路径
    LOG_FILE = "blender_agent.log"
    
    # 🧠 短期记忆配置
    MAX_SHORT_TERM_TURNS: int = int(os.getenv("MAX_SHORT_TERM_TURNS", "5"))
    MAX_SHORT_TERM_TOKENS: int = int(os.getenv("MAX_SHORT_TERM_TOKENS", "8000"))
    SHORT_TERM_TOKEN_BUFFER: int = int(os.getenv("SHORT_TERM_TOKEN_BUFFER", "2000"))
    
    # 📚 长期记忆配置
    LONG_TERM_MEMORY_ENABLED: bool = os.getenv("LONG_TERM_MEMORY_ENABLED", "true").lower() == "true"
    LONG_TERM_DB_PATH: str = os.getenv("LONG_TERM_DB_PATH", os.path.join(os.path.dirname(BASE_DIR), "data", "memory.db"))
    
    # 自动归档配置
    AUTO_ARCHIVE_ENABLED: bool = os.getenv("AUTO_ARCHIVE_ENABLED", "true").lower() == "true"
    ARCHIVE_THRESHOLD: int = int(os.getenv("ARCHIVE_THRESHOLD", "10"))  # 超过10轮时开始归档
    
    # 向量搜索配置
    ENABLE_VECTOR_SEARCH: bool = os.getenv("ENABLE_VECTOR_SEARCH", "true").lower() == "true"
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # 可使用新API
    VECTOR_SIMILARITY_THRESHOLD: float = float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.7"))
    
    # 长期记忆清理配置
    MEMORY_RETENTION_DAYS: int = int(os.getenv("MEMORY_RETENTION_DAYS", "90"))  # 90天后删除未访问的记录
    MIN_MEMORY_FREQUENCY: int = int(os.getenv("MIN_MEMORY_FREQUENCY", "5"))    # 最少访问频率

# 初始化配置实例
settings = Settings()

# 🔒 启动时验证关键敏感配置
if settings.DASHSCOPE_API_KEY == "NOT_SET":
    raise ValueError(
        "❌ DASHSCOPE_API_KEY 未配置！\n"
        "请在项目根目录创建 .env 文件并添加:\n"
        "DASHSCOPE_API_KEY=your_actual_key_here\n"
        "获取方式：https://dashscope.console.aliyun.com/apikey"
    )