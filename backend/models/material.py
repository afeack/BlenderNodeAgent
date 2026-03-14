#数据定义。使用 Pydantic 定义节点、连接、属性的标准 JSON 结构，确保模型输出符合 Blender 要求。
from __future__ import annotations
from typing import List, Optional, Any
from pydantic import BaseModel, Field 

class NodeProperty(BaseModel):
    """材质节点的属性设置，例如粗糙度、颜色数值等"""
    name: str = Field(description="Blender 节点中的属性名称，如 'Roughness', 'Base Color'")
    value: Any = Field(description="属性的具体数值")

class NodeConnection(BaseModel):
    """节点间的连线逻辑"""
    from_node: str = Field(description="源节点的 ID")
    from_socket: str = Field(description="源节点的输出端口名称")
    to_node: str = Field(description="目标节点的 ID")
    to_socket: str = Field(description="目标节点的输入端口名称")

class BlenderNode(BaseModel):
    """单个 Blender 节点的定义"""
    node_id: str = Field(description="节点的唯一自定义 ID")
    node_type: str = Field(description="Blender 节点的官方类名，如 'ShaderNodeBsdfPrincipled'")
    properties: List[NodeProperty] = Field(default_factory=list, description="预设的静态属性列表")

class MaterialGraph(BaseModel):
    """最终输出的完整材质图表"""
    material_name: str = Field(description="材质的名称")
    nodes: List[BlenderNode] = Field(description="节点列表")
    connections: List[NodeConnection] = Field(description="连接列表")
    
class MaterialResponse(BaseModel):
    status: str
    mode: str = "chat" # 新增：标记当前属于什么指令
    material_data: Optional[dict] = None
    ai_remarks: str = ""
    error: Optional[str] = None