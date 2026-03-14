from langchain_core.tools import tool

@tool
def check_critic_version():
    """检查Critic Agent版本"""
    return "Critic Agent v1.0.0"
