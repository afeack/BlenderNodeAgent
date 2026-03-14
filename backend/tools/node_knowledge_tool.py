# tools/node_knowledge_tool.py
import json
import os
from typing import List, Dict, Any
from langchain_core.tools import StructuredTool
from pathlib import Path
import difflib  # 用于字符串相似度匹配
# 获取项目根目录，定位配置文件夹下的数据库
BASE_DIR = Path(__file__).parent.parent
NODE_DB_PATH = BASE_DIR / "data" / "blender_nodes_db.json"

def load_node_database() -> List[Dict[str, Any]]:
    """加载 Blender 节点数据库"""
    if not os.path.exists(NODE_DB_PATH):
        # 备选逻辑：如果路径不匹配，尝试在当前工作目录寻找
        fallback_path = Path("Blender_node\blender_nodes_db.json")
        if fallback_path.exists():
            with open(fallback_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    
    with open(NODE_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data

def format_node_for_llm(node: Dict[str, Any]) -> str:
    """将节点格式化为 LLM 易读的字符串，突出显示 Socket 名称"""
    lines = [f"### Node: {node.get('node_type')} ({node.get('label', 'N/A')})"]
    
    inputs = node.get("inputs", [])
    if inputs:
        inp_names = [f"'{inp['name']}' ({inp['type']})" for inp in inputs]
        lines.append(f"  - Inputs (Sockets): {', '.join(inp_names)}")
    
    outputs = node.get("outputs", [])
    if outputs:
        out_names = [f"'{out['name']}' ({out['type']})" for out in outputs]
        lines.append(f"  - Outputs (Sockets): {', '.join(out_names)}")
    
    return "\n".join(lines)

def query_blender_node_docs(query: str) -> str:
    nodes = load_node_database()
    query_clean = query.replace("type:", "").strip()
    
    # 获取数据库中所有的 node_type 列表，用于纠错
    all_types = [n.get("node_type") for n in nodes if n.get("node_type")]
    
    # 1. 尝试精准匹配
    target_node = next((n for n in nodes if n.get("node_type").lower() == query_clean.lower()), None)
    
    if target_node:
        return f"✅ 验证成功！节点 '{target_node['node_type']}' 的官方 Sockets 为：\n{format_node_for_llm(target_node)}"
    
    # 2. 如果精准匹配失败，启动“纠偏模式”
    # 寻找最相似的 3 个官方节点名
    closest_matches = difflib.get_close_matches(query_clean, all_types, n=3, cutoff=0.4)
    
    if closest_matches:
        correction_info = ""
        for match in closest_matches:
            match_node = next(n for n in nodes if n.get("node_type") == match)
            correction_info += f"\n--- 建议更正为：{match} ---\n{format_node_for_llm(match_node)}"
        
        return (f"❌ 警告：数据库中没有 '{query_clean}'。你可能指的是以下官方节点？\n"
                f"请重新使用建议的节点名和对应的 Sockets 构建 JSON。\n" + correction_info)

    return f"❌ 严重错误：完全找不到与 '{query_clean}' 相关的官方节点。"

# tools/node_knowledge_tool.py

# 确保 get_node_knowledge_tool 的 StructuredTool 定义极其明确
def get_node_knowledge_tool():
    return StructuredTool.from_function(
        func=query_blender_node_docs,
        name="query_blender_node_documentation",
        description="Search for Blender nodes. Use keywords like 'scratch' or 'glossy', or use 'type:ShaderNodeName' for exact sockets.",
        # 显式定义 schema 减少模型幻觉
    )