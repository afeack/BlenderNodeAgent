# services/workflow/chat_centric_state_machine.py

from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from internal.manager import session_manager

class ChatCentricState(TypedDict):
    """
    Chat 中心化架构的状态定义
    """
    user_input: str
    current_state: str  # INIT, PROCESSING, FINALIZING
    chat_history: List[Dict[str, Any]]
    node_graph: Optional[Dict[str, Any]] = None
    error_list: List[str]

# 状态定义
INIT = "INIT"
PROCESSING = "PROCESSING"
FINALIZING = "FINALIZING"

class ChatCentricStateMachine:
    """
    Chat 中心化架构的状态机实现
    Chat Agent作为总指挥，通过tool calling协调其他Agent
    状态机只负责初始化和最终处理
    """
    
    def __init__(self, chat_agent, state_callback=None):
        self.chat_agent = chat_agent
        self.state_callback = state_callback
        # 移除checkpointer，确保每次调用都是全新的状态
        self.graph = self._build_graph()
        self.runnable = self.graph.compile()
    
    def _build_graph(self):
        """
        构建 Chat 中心化的状态图（简化为单节点架构）
        """
        graph = StateGraph(ChatCentricState)
        
        # 定义节点
        graph.add_node("init", self._init_node)
        graph.add_node("process", self._process_node)
        graph.add_node("finalize", self._finalize_node)
        
        # 定义边
        graph.set_entry_point("init")
        graph.add_edge("init", "process")
        graph.add_edge("process", "finalize")
        graph.add_edge("finalize", END)
        
        return graph
    
    async def _init_node(self, state: ChatCentricState) -> ChatCentricState:
        """
        初始化节点
        """
        print(f"[DEBUG] _init_node called")
        
        # 通知状态变更
        if hasattr(self, 'state_callback') and self.state_callback:
            await self.state_callback({
                "state": INIT,
                "message": "初始化 Chat 中心化架构",
                "agent": "system"
            })
        
        # 初始化状态
        state["current_state"] = PROCESSING
        state["error_list"] = []
        
        print(f"[DEBUG] _init_node completed, new state: {state.get('current_state')}")
        
        # 通知状态变更
        if hasattr(self, 'state_callback') and self.state_callback:
            await self.state_callback({
                "state": PROCESSING,
                "message": "开始处理用户请求",
                "agent": "system"
            })
        
        return state
    
    async def _process_node(self, state: ChatCentricState) -> ChatCentricState:
        """
        处理用户请求节点
        Chat Agent作为总指挥，通过tool calling协调其他Agent
        """
        print(f"[DEBUG] _process_node called with user_input: {state.get('user_input')}")
        
        # 通知状态变更
        if hasattr(self, 'state_callback') and self.state_callback:
            await self.state_callback({
                "state": PROCESSING,
                "message": f"处理用户请求: {state['user_input'][:50]}...",
                "agent": "chat"
            })
        
        # 记录到记忆
        session_manager.add_message(
            "chat_agent",
            f"[用户请求] {state['user_input']}"
        )
        
        # 构建 Chat Agent 输入
        chat_input = {
            "user_input": state["user_input"],
            "chat_history": state.get("chat_history", [])
        }
        
        print(f"[DEBUG] Calling Chat Agent with input: {chat_input}")
        
        # 调用 Chat Agent（作为总指挥）
        try:
            response = await self.chat_agent.ainvoke(chat_input)
            
            print(f"[DEBUG] Chat Agent response type: {type(response)}")
            print(f"[DEBUG] Chat Agent response keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
            
            # 提取输出
            chat_output = response.get("output", "")
            print(f"[DEBUG] Chat Agent output length: {len(chat_output)} chars")
            print(f"[DEBUG] Chat Agent output preview: {chat_output[:200]}...")
            
            # 检查 intermediate_steps 中的工具调用结果
            intermediate_steps = response.get("intermediate_steps", [])
            print(f"[DEBUG] Number of intermediate steps: {len(intermediate_steps)}")
            
            # 打印 intermediate_steps 的详细信息以便调试
            for i, step in enumerate(intermediate_steps):
                print(f"[DEBUG] Intermediate step {i} type: {type(step)}")
                print(f"[DEBUG] Intermediate step {i} repr: {repr(step)}")
                # 如果是元组，打印元组的内容
                if isinstance(step, tuple):
                    print(f"[DEBUG] Intermediate step {i} tuple length: {len(step)}")
                    for j, item in enumerate(step):
                        print(f"[DEBUG] Intermediate step {i} item {j} type: {type(item)}")
                        print(f"[DEBUG] Intermediate step {i} item {j} repr: {repr(item)}")
            
            # 检查是否包含材质节点数据
            import re
            import json
            
            # 尝试从输出中提取节点数据
            node_graph = None
            
            # 1. 首先检查 intermediate_steps 中的 submit_material_result 工具调用
            for step in intermediate_steps:
                try:
                    # 检查是否是 tuple 格式的 intermediate_steps
                    if isinstance(step, tuple) and len(step) == 2:
                        action, observation = step
                        print(f"[DEBUG] Processing tuple step: action={repr(action)}, observation={repr(observation)}")
                        
                        # 检查 action 是否是 AgentAction 对象
                        if hasattr(action, 'tool'):
                            # 检查是否是 submit_material_result 工具调用
                            if action.tool == "submit_material_result":
                                # 获取工具调用的输入
                                tool_input = action.tool_input
                                print(f"[DEBUG] Found submit_material_result tool call with input: {repr(tool_input)}")
                                # 处理工具输入
                                if isinstance(tool_input, dict):
                                    submit_data = tool_input
                                elif isinstance(tool_input, str):
                                    # 尝试解析 JSON 字符串
                                    try:
                                        submit_data = json.loads(tool_input)
                                    except json.JSONDecodeError as e:
                                        print(f"[ERROR] Failed to parse tool_input JSON: {e}")
                                        continue
                                else:
                                    continue
                                
                                from models.material import MaterialGraph
                                node_graph = MaterialGraph(
                                    material_name=submit_data.get("material_name", "UnnamedMaterial"),
                                    nodes=submit_data.get("nodes", []),
                                    connections=submit_data.get("connections", [])
                                )
                                print(f"[DEBUG] Successfully extracted node graph from AgentAction")
                                print(f"[DEBUG] Extracted material name: {node_graph.material_name}")
                                print(f"[DEBUG] Extracted nodes count: {len(node_graph.nodes)}")
                                print(f"[DEBUG] Extracted connections count: {len(node_graph.connections)}")
                                break
                        
                        # 检查 action 是否是字典格式
                        elif isinstance(action, dict):
                            # 检查是否是 submit_material_result 工具调用
                            if action.get("tool") == "submit_material_result":
                                # 获取工具调用的输入
                                tool_input = action.get("tool_input", {})
                                print(f"[DEBUG] Found submit_material_result tool call with input: {repr(tool_input)}")
                                # 处理工具输入
                                if isinstance(tool_input, dict):
                                    submit_data = tool_input
                                elif isinstance(tool_input, str):
                                    # 尝试解析 JSON 字符串
                                    try:
                                        submit_data = json.loads(tool_input)
                                    except json.JSONDecodeError as e:
                                        print(f"[ERROR] Failed to parse tool_input JSON: {e}")
                                        continue
                                else:
                                    continue
                                
                                from models.material import MaterialGraph
                                node_graph = MaterialGraph(
                                    material_name=submit_data.get("material_name", "UnnamedMaterial"),
                                    nodes=submit_data.get("nodes", []),
                                    connections=submit_data.get("connections", [])
                                )
                                print(f"[DEBUG] Successfully extracted node graph from tuple intermediate steps (dict format)")
                                print(f"[DEBUG] Extracted material name: {node_graph.material_name}")
                                print(f"[DEBUG] Extracted nodes count: {len(node_graph.nodes)}")
                                print(f"[DEBUG] Extracted connections count: {len(node_graph.connections)}")
                                break

                        # 检查 action 是否是字符串格式（React Agent 格式）
                        elif isinstance(action, str):
                            print(f"[DEBUG] Processing string action: {repr(action)}")
                            # 检查是否是 submit_material_result 工具调用
                            if "Action: submit_material_result" in action:
                                # 查找 Action Input 部分
                                input_match = re.search(r"Action Input:\s*(.*)", action)
                                if input_match:
                                    json_str = input_match.group(1).strip()
                                    print(f"[DEBUG] Found submit_material_result tool call with input: {repr(json_str)}")
                                    # 尝试解析 JSON
                                    try:
                                        submit_data = json.loads(json_str)
                                        from models.material import MaterialGraph
                                        node_graph = MaterialGraph(
                                            material_name=submit_data.get("material_name", "UnnamedMaterial"),
                                            nodes=submit_data.get("nodes", []),
                                            connections=submit_data.get("connections", [])
                                        )
                                        print(f"[DEBUG] Successfully extracted node graph from string action")
                                        print(f"[DEBUG] Extracted material name: {node_graph.material_name}")
                                        print(f"[DEBUG] Extracted nodes count: {len(node_graph.nodes)}")
                                        print(f"[DEBUG] Extracted connections count: {len(node_graph.connections)}")
                                        break
                                    except Exception as e:
                                        print(f"[ERROR] Failed to parse submit_material_result input: {e}")
                    # 检查是否是字典格式的 intermediate_steps
                    elif isinstance(step, dict):
                        print(f"[DEBUG] Processing dict step: {repr(step)}")
                        # 检查是否是 submit_material_result 工具调用
                        if step.get("tool") == "submit_material_result":
                            # 获取工具调用的输入
                            tool_input = step.get("tool_input", {})
                            print(f"[DEBUG] Found submit_material_result tool call with input: {repr(tool_input)}")
                            # 处理工具输入
                            if isinstance(tool_input, dict):
                                submit_data = tool_input
                            elif isinstance(tool_input, str):
                                # 尝试解析 JSON 字符串
                                try:
                                    submit_data = json.loads(tool_input)
                                except json.JSONDecodeError as e:
                                    print(f"[ERROR] Failed to parse tool_input JSON: {e}")
                                    continue
                            else:
                                continue
                            
                            from models.material import MaterialGraph
                            node_graph = MaterialGraph(
                                material_name=submit_data.get("material_name", "UnnamedMaterial"),
                                nodes=submit_data.get("nodes", []),
                                connections=submit_data.get("connections", [])
                            )
                            print(f"[DEBUG] Successfully extracted node graph from dict intermediate steps")
                            print(f"[DEBUG] Extracted material name: {node_graph.material_name}")
                            print(f"[DEBUG] Extracted nodes count: {len(node_graph.nodes)}")
                            print(f"[DEBUG] Extracted connections count: {len(node_graph.connections)}")
                            break

                except Exception as e:
                    print(f"[ERROR] Failed to extract from intermediate step: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # 检查是否是聊天响应
            if node_graph is None:
                # 没有节点数据，可能是聊天响应
                if "chat_response" not in chat_output:
                    # 创建一个聊天响应
                    node_graph = {"chat_response": chat_output}
                    print(f"[DEBUG] Created chat response")
                else:
                    # 输出中已经包含了chat_response
                    print(f"[DEBUG] Chat output already contains response")
            
            state["node_graph"] = node_graph
            
            # 进入最终状态
            state["current_state"] = FINALIZING
            print(f"[DEBUG] _process_node completed, transitioning to FINALIZING")
            
            if hasattr(self, 'state_callback') and self.state_callback:
                await self.state_callback({
                    "state": FINALIZING,
                    "message": "提交最终结果",
                    "agent": "chat"
                })
            
        except Exception as e:
            error_msg = f"Chat Agent 执行失败: {str(e)}"
            print(f"[ERROR] Chat Agent exception: {error_msg}")
            print(f"[ERROR] Exception type: {type(e).__name__}")
            state["error_list"].append(error_msg)
            session_manager.add_message("system", error_msg)
            
            # 即使出错也进入最终状态
            state["current_state"] = FINALIZING
            
        return state
    
    async def _finalize_node(self, state: ChatCentricState) -> ChatCentricState:
        """
        最终处理节点
        """
        # 通知状态变更
        if hasattr(self, 'state_callback') and self.state_callback:
            await self.state_callback({
                "state": FINALIZING,
                "message": "流程结束，准备输出结果",
                "agent": "system"
            })
        
        # 记录到记忆
        if state.get("node_graph"):
            if isinstance(state["node_graph"], dict) and "chat_response" in state["node_graph"]:
                # 聊天响应
                session_manager.add_message(
                    "chat_agent",
                    f"[执行成功] 聊天功能完成: {state['node_graph']['chat_response'][:100]}..."
                )
            else:
                # 材质生成
                node_count = len(state["node_graph"].nodes) if hasattr(state["node_graph"], 'nodes') else 0
                session_manager.add_message(
                    "state_machine",
                    f"[执行成功] 状态机工作流完成，生成材质节点图，包含 {node_count} 个节点"
                )
        
        # 记录错误
        if state.get("error_list"):
            session_manager.add_message(
                "system",
                f"[流程结束] 错误数: {len(state['error_list'])}"
            )
        
        # 确保状态为 END
        state["current_state"] = "END"
        
        return state
    
    async def run(self, user_input: str, chat_history: List[Dict[str, Any]] = None, session_id: str = None) -> Dict[str, Any]:
        """
        运行 Chat 中心化状态机
        
        参数:
            user_input: 用户输入
            chat_history: 对话历史（可选）
            session_id: 会话ID（可选，现在仅用于日志记录）
        
        返回:
            最终状态
        """
        print(f"[DEBUG] ChatCentricStateMachine.run() called with user_input: {user_input}")
        print(f"[DEBUG] Session ID: {session_id}")
        
        initial_state = {
            "user_input": user_input,
            "current_state": INIT,
            "chat_history": chat_history or [],
            "node_graph": None,
            "error_list": []
        }
        
        print(f"[DEBUG] Initial state: {initial_state}")
        
        # 移除checkpointer配置，确保每次调用都是全新的状态
        print(f"[DEBUG] Invoking state machine without checkpointer")
        
        result = await self.runnable.ainvoke(initial_state)
        
        print(f"[DEBUG] State machine completed")
        print(f"[DEBUG] Final state keys: {result.keys()}")
        print(f"[DEBUG] Final current_state: {result.get('current_state')}")
        print(f"[DEBUG] Final node_graph: {result.get('node_graph')}")
        
        return result
