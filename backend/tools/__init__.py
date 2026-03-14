# tools/__init__.py
from langchain_core.tools import StructuredTool
from models.material import MaterialGraph
from tools.node_knowledge_tool import get_node_knowledge_tool
from tools.physical_properties_tool import (
    lookup_material_properties,
    search_materials_by_keyword,
    list_all_categories,
    list_category_materials,
    extract_and_enrich_materials
)

# 1. 重新定义提交函数逻辑，使其能够处理多种输入格式
def submit_func(data=None, material_name=None, nodes=None, connections=None):
    """
    当你准备好最终的材质节点方案时，调用此工具进行输出。
    
    参数:可以是以下格式：
    格式1: 单个data参数 - data可以是字典或JSON字符串
    格式2: 三个独立参数 - material_name, nodes, connections
    
    返回:
        包含材质数据的字典
    """
    import json
    from models.material import MaterialGraph
    
    material_name_result = "UnnamedMaterial"
    nodes_result = []
    connections_result = []
    
    try:
        # 处理单个data参数的情况
        if data is not None:
            # 处理字符串格式
            if isinstance(data, str):
                try:
                    # 解析JSON字符串
                    parsed_data = json.loads(data)
                    material_name_result = parsed_data.get("material_name", "UnnamedMaterial")
                    nodes_result = parsed_data.get("nodes", [])
                    connections_result = parsed_data.get("connections", [])
                except json.JSONDecodeError:
                    # 如果解析失败，使用默认值
                    pass
            
            # 处理字典格式
            elif isinstance(data, dict):
                # 检查是否是嵌套格式
                if "material_name" in data:
                    material_name_value = data["material_name"]
                    
                    # 检查material_name是否是JSON字符串
                    if isinstance(material_name_value, str) and material_name_value.startswith('{'):
                        try:
                            # 解析嵌套的JSON字符串
                            nested_data = json.loads(material_name_value)
                            material_name_result = nested_data.get("material_name", "UnnamedMaterial")
                            nodes_result = nested_data.get("nodes", [])
                            connections_result = nested_data.get("connections", [])
                        except json.JSONDecodeError:
                            # 如果解析失败，使用默认值
                            material_name_result = material_name_value
                    else:
                        # 直接使用字典中的值
                        material_name_result = material_name_value
                        nodes_result = data.get("nodes", [])
                        connections_result = data.get("connections", [])
        # 处理三个独立参数的情况
        elif material_name is not None:
            material_name_result = material_name
            nodes_result = nodes or []
            connections_result = connections or []
    except Exception as e:
        # 任何异常都使用默认值
        pass
    
    # 创建MaterialGraph对象
    material_graph = MaterialGraph(
        material_name=material_name_result,
        nodes=nodes_result,
        connections=connections_result
    )
    
    # 材质数据提交成功
    result = {
        "material_name": material_name_result,
        "nodes": nodes_result,
        "connections": connections_result
    }
    
    # 打印提交的材质数据信息
    print(f"[DEBUG] submit_material_result called with:")
    print(f"[DEBUG] Material name: {material_name_result}")
    print(f"[DEBUG] Nodes count: {len(nodes_result)}")
    print(f"[DEBUG] Connections count: {len(connections_result)}")
    
    return result

# 2. 包装成 StructuredTool
submit_material_result = StructuredTool.from_function(
    func=submit_func,
    name="submit_material_result",
    description="这是最终提交工具。当你准备好最终的材质节点方案时，必须调用此工具提交最终的材质数据。调用此工具后，系统会自动处理你的输出，无需再手动输出 JSON。"
)

# 3. 物理属性查询工具（新增）
physical_properties_lookup = StructuredTool.from_function(
    func=lookup_material_properties,
    name="lookup_material_properties",
    description="查询材质的物理属性（IOR、颜色、金属度等）。输入材质英文名称（如 'gold', 'glass', 'water'）获取详细的物理参数和描述。",
)

search_materials = StructuredTool.from_function(
    func=search_materials_by_keyword,
    name="search_materials",
    description="按关键词搜索可用的材质。例如搜索'金属'或'玻璃'来查找相关材质列表。",
)

list_material_categories = StructuredTool.from_function(
    func=list_all_categories,
    name="list_material_categories",
    description="列出所有可用的材质分类（如金属、非金属、液体等）。",
)

# 材质注入工具：自动检测用户输入中的材质并注入其物理参数
enrich_materials_tool = StructuredTool.from_function(
    func=extract_and_enrich_materials,
    name="enrich_materials_with_properties",
    description="智能分析用户输入，自动检测其中提到的材质名称，并为每个检测到的材质注入详细的物理参数信息（IOR、颜色、金属度等）。这有助于后续的材质节点生成。",
)

# 4. 统一工具列表 (这就是 get_blender_agent 需要的 tools 列表)
def get_Material_tools():
    return [
        get_node_knowledge_tool(),
        physical_properties_lookup,      # 查询单个材质
        search_materials,                # 搜索材质
        list_material_categories,        # 列出分类
        enrich_materials_tool,           # 材质注入（新增）
    ]

def get_Material_tools_without_submit():
    return [
        get_node_knowledge_tool(),
        physical_properties_lookup,      # 查询单个材质
        search_materials,                # 搜索材质
        list_material_categories,        # 列出分类
        enrich_materials_tool,           # 材质注入（新增）
    ]
    
# Agent调用工具
def call_artist_agent_func(instruction: str) -> str:
    """
    调用Artist Agent获取风格设计方案
    
    参数:
        instruction: 给Artist Agent的简洁指令
    
    返回:
        Artist Agent返回的风格设计方案
    """
    import asyncio
    from services.artist_agent.artist_agent import artist_agent
    try:
        result = asyncio.run(artist_agent.ainvoke({
            "user_input": instruction,
            "chat_history": []
        }))
        return result.get("output", "")
    except Exception as e:
        return f"Artist Agent调用失败: {str(e)}"

def call_material_agent_func(instruction: str, style: str = "") -> str:
    """
    调用Material Agent生成材质节点
    
    参数:
        instruction: 给Material Agent的简洁指令
        style: 风格方案（可选）
    
    返回:
        Material Agent返回的节点JSON
    """
    import asyncio
    from services.material_agent.agent_executor import blender_agent
    try:
        result = asyncio.run(blender_agent.ainvoke({
            "user_input": instruction,
            "chat_history": [],
            "style": style,
            "context": ""
        }))
        return result.get("output", "")
    except Exception as e:
        return f"Material Agent调用失败: {str(e)}"

def call_critic_agent_func(graph: str, style: str = "") -> str:
    """
    调用Critic Agent审计材质节点图
    
    参数:
        graph: 节点图JSON字符串
        style: 风格方案（可选）
    
    返回:
        Critic Agent返回的审计结果和建议
    """
    import asyncio
    from services.critic_agent.critic_agent import critic_agent
    try:
        result = asyncio.run(critic_agent.ainvoke({
            "graph": graph,
            "style": style,
            "context": "",
            "chat_history": []
        }))
        return result.get("output", "")
    except Exception as e:
        return f"Critic Agent调用失败: {str(e)}"

# 包装成StructuredTool
call_artist_agent = StructuredTool.from_function(
    func=call_artist_agent_func,
    name="call_artist_agent",
    description="调用Artist Agent获取材质风格设计方案。参数instruction: 给Artist Agent的简洁指令，描述用户需求和期望的风格。返回风格设计方案，包括风格类型、色彩方案、材质特性等。",
)

call_material_agent = StructuredTool.from_function(
    func=call_material_agent_func,
    name="call_material_agent",
    description="调用Material Agent生成Blender材质节点图。参数instruction: 给Material Agent的简洁指令，描述要生成的材质；参数style: 风格方案（可选）。返回节点JSON数据，包含nodes和connections。",
)

call_critic_agent = StructuredTool.from_function(
    func=call_critic_agent_func,
    name="call_critic_agent",
    description="调用Critic Agent审计材质节点图。参数graph: 节点图JSON字符串；参数style: 风格方案（可选）。返回审计结果，包括是否通过、发现的问题和修复建议。",
)

def get_chat_tools():
    return [
        get_node_knowledge_tool(),  # 添加节点知识库查询工具
        call_artist_agent,  # 调用Artist Agent
        call_material_agent,  # 调用Material Agent
        call_critic_agent,  # 调用Critic Agent
        submit_material_result,  # 添加提交工具
    ]

def get_critic_tools():
    return [
        get_node_knowledge_tool(),  # 查询节点知识
        physical_properties_lookup,  # 查询材质物理属性
    ]

def get_artist_tools():
    from tools.artist_agent_tool import check_artist_version
    return [
        check_artist_version,  # 检查Artist Agent版本
    ]
