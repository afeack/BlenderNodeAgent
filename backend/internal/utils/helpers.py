#预处理/后校验。包含对节点图完整性的静态校验。
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig


def validate_node_graph(output: Any) -> Any:
    """
    后处理函数：强制校验输出的结构。
    如果 Agent 忘记生成 ShaderNodeOutputMaterial，这里可以进行逻辑干预。
    """
    # 检查是否包含输出节点
    has_output = any(node.node_type == "ShaderNodeOutputMaterial" for node in output.nodes)
    
    if not has_output:
        # 自动补全一个输出节点
        from models.material import BlenderNode
        output.nodes.append(BlenderNode(
            node_id="final_output_fallback",
            node_type="ShaderNodeOutputMaterial"
        ))
        
    return output