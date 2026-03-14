from langchain_core.tools import tool

@tool
def check_artist_version():
    """检查Artist Agent版本"""
    return "Artist Agent v1.0.0"
