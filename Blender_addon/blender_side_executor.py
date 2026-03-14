import bpy
import json

# --- 核心逻辑：节点构建器 ---
class BlenderAgentInterpreter:
    @staticmethod
    def fix_socket_name(node_type, socket_name):
        """处理 Blender 4.2+ 端口命名变更"""
        if node_type == 'ShaderNodeBsdfPrincipled':
            mapping = {
                'Base Color': 'Base Color',
                'Specular': 'Specular IOR Level', # 4.0+ 变更
                'Roughness': 'Roughness',
                'Metallic': 'Metallic',
                'Normal': 'Normal'
            }
            return mapping.get(socket_name, socket_name)
        return socket_name

    @staticmethod
    def rebuild_material(data):
        if not data: return
            
        mat_name = data.get("material_name", "AI_Generated_Material")
        mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        node_map = {}
        # 1. 创建节点
        for n_data in data.get('nodes', []):
            try:
                b_node = nodes.new(type=n_data['node_type'])
                b_node.name = n_data['node_id']
                node_map[n_data['node_id']] = b_node
                
                for prop in n_data.get('properties', []):
                    # 自动修正端口名
                    fixed_name = BlenderAgentInterpreter.fix_socket_name(n_data['node_type'], prop['name'])
                    if fixed_name in b_node.inputs:
                        b_node.inputs[fixed_name].default_value = prop['value']
                    elif hasattr(b_node, prop['name']):
                        setattr(b_node, prop['name'], prop['value'])
            except Exception as e:
                print(f"⚠️ 节点 {n_data.get('node_id')} 失败: {e}")

        # 2. 建立连接
        for conn in data.get('connections', []):
            try:
                from_n = node_map[conn['from_node']]
                to_n = node_map[conn['to_node']]
                # 同样修正连接时的端口名
                to_socket = BlenderAgentInterpreter.fix_socket_name(to_n.bl_idname, conn['to_socket'])
                links.new(from_n.outputs[conn['from_socket']], to_n.inputs[to_socket])
            except Exception as e:
                print(f"🔗 连接失败: {e}")

# --- Operator: 从剪贴板读取 ---
class AGENT_OT_ReadClipboard(bpy.types.Operator):
    bl_idname = "agent.read_clipboard"
    bl_label = "1. 从剪贴板提取数据"
    
    def execute(self, context):
        raw_data = context.window_manager.clipboard
        try:
            payload = json.loads(raw_data)
            if payload.get("protocol") == "BLENDER_NODE_AGENT":
                mat_data = payload.get("material_data", {})
                # 将数据暂存在场景属性中
                context.scene.ai_temp_json = json.dumps(mat_data)
                context.scene.ai_mat_name_input = mat_data.get("material_name", "New_Material")
                self.report({'INFO'}, f"成功读取: {context.scene.ai_mat_name_input}")
            else:
                self.report({'ERROR'}, "剪贴板数据格式不正确")
        except:
            self.report({'ERROR'}, "剪贴板内不是有效的 JSON")
        return {'FINISHED'}

# --- Operator: 正式应用 ---
class AGENT_OT_ApplyMaterial(bpy.types.Operator):
    bl_idname = "agent.apply_material"
    bl_label = "2. 生成节点"
    
    def execute(self, context):
        if not context.scene.ai_temp_json:
            self.report({'WARNING'}, "请先读取剪贴板")
            return {'CANCELLED'}
        
        data = json.loads(context.scene.ai_temp_json)
        # 使用用户在输入框里改过的名字
        data["material_name"] = context.scene.ai_mat_name_input
        
        BlenderAgentInterpreter.rebuild_material(data)
        self.report({'INFO'}, f"材质 {data['material_name']} 已生成")
        return {'FINISHED'}

# --- UI 面板 ---
class AGENT_PT_Panel(bpy.types.Panel):
    bl_label = "Blender AI 材质专家 (Clipboard版)"
    bl_idname = "AGENT_PT_clipboard_panel"
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'AI Agent'

    def draw(self, context):
        layout, scene = self.layout, context.scene
        
        box = layout.box()
        box.label(text="第一步: 获取数据", icon='COPY_ID')
        box.operator("agent.read_clipboard", icon='IMPORT')

        if scene.ai_temp_json:
            box = layout.box()
            box.label(text="第二步: 确认并生成", icon='MATERIAL')
            box.prop(scene, "ai_mat_name_input", text="材质名称")
            box.operator("agent.apply_material", text="立即生成节点", icon='NODE_SEL')

# --- 注册 ---
def register():
    bpy.utils.register_class(AGENT_OT_ReadClipboard)
    bpy.utils.register_class(AGENT_OT_ApplyMaterial)
    bpy.utils.register_class(AGENT_PT_Panel)
    
    bpy.types.Scene.ai_temp_json = bpy.props.StringProperty(name="Temp Data")
    bpy.types.Scene.ai_mat_name_input = bpy.props.StringProperty(name="材质名称")

def unregister():
    bpy.utils.unregister_class(AGENT_PT_Panel)
    bpy.utils.unregister_class(AGENT_OT_ApplyMaterial)
    bpy.utils.unregister_class(AGENT_OT_ReadClipboard)

if __name__ == "__main__":
    register()