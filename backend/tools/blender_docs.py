# tools/blender_docs.py 外部知识库。提供查询 Blender 端口名称的工具以及 Agent 提交结果的伪工具函数。

from langchain_core.tools import tool
from models.material import MaterialGraph # 导入你的模型

@tool(args_schema=MaterialGraph) # 关键：在这里绑定 Schema
def submit_material_result(material_name: str, nodes: list, connections: list):
    """
    当材质节点图构建完成后，必须调用此工具提交最终结果。
    该工具接收完整的节点列表和连接信息。
    """
    # 这里不需要做复杂逻辑，直接返回数据即可，AgentExecutor 会捕获这个输出
    return {
        "material_name": material_name,
        "nodes": nodes,
        "connections": connections
    }