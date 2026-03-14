import sys
import os
import traceback
import json
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# 1. 环境准备
load_dotenv(dotenv_path="../.env")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. 导入核心组件
from services.workflow.chat_centric_state_machine import ChatCentricStateMachine
from internal.manager import session_manager
from services.chat_agent.chat_agent import get_blender_chat_agent
from services.material_agent.agent_executor import blender_agent
from services.artist_agent.artist_agent import artist_agent
from services.critic_agent.critic_agent import critic_agent
from internal.config.settings import settings
from internal.memory.init_db import init_memory_database
import uuid
import logging

# 设置日志级别
logger = logging.getLogger(__name__)

app = FastAPI(title="BlenderNodeAgent Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 添加CORS预检请求处理
@app.options("/{path:path}")
async def options_handler(path: str):
    return {"message": "OK"}

# 启动事件：初始化长期记忆数据库
@app.on_event("startup")
async def startup_event():
    try:
        init_memory_database()
        logger.info("长期记忆数据库初始化成功")
    except Exception as e:
        logger.error(f"长期记忆数据库初始化失败: {e}")

# 请求模型
class ChatRequest(BaseModel):
    message: str
    session_id: str

# SSE 消息格式化函数
def format_sse_message(data: Dict[str, Any]) -> str:
    """将数据格式化为 SSE 消息格式"""
    return f"data: {json.dumps(data)}\n\n"

# WebSocket 连接管理
ws_connections: Dict[str, List[WebSocket]] = {}

async def notify_state_updated(session_id: str, state_info: Dict[str, Any]):
    """通知前端状态变更"""
    if session_id in ws_connections:
        alive = []
        for ws in ws_connections[session_id]:
            try:
                await ws.send_json({"type": "state_updated", "session_id": session_id, "state": state_info})
                alive.append(ws)
            except Exception:
                pass
        ws_connections[session_id] = alive

async def notify_graph_ready(session_id: str):
    """通知前端节点图已准备好可以获取"""
    if session_id in ws_connections:
        alive = []
        for ws in ws_connections[session_id]:
            try:
                await ws.send_json({"type": "graph_ready", "session_id": session_id})
                alive.append(ws)
            except Exception:
                pass
        ws_connections[session_id] = alive

async def notify_task_completed(session_id: str):
    """通知前端任务完成"""
    if session_id in ws_connections:
        alive = []
        for ws in ws_connections[session_id]:
            try:
                await ws.send_json({"type": "task_completed", "session_id": session_id})
                alive.append(ws)
            except Exception:
                pass
        ws_connections[session_id] = alive

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 端点，用于实时状态更新"""
    await websocket.accept()
    
    if session_id not in ws_connections:
        ws_connections[session_id] = []
    ws_connections[session_id].append(websocket)
    
    try:
        # 使用心跳机制保持连接活跃
        while True:
            try:
                # 设置超时，避免阻塞
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # 发送心跳消息
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        ws_connections[session_id] = [ws for ws in ws_connections.get(session_id, []) if ws != websocket]
        if not ws_connections[session_id]:
            del ws_connections[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if session_id in ws_connections:
            ws_connections[session_id] = [ws for ws in ws_connections[session_id] if ws != websocket]
            if not ws_connections[session_id]:
                del ws_connections[session_id]

@app.get('/api/config')
async def get_config(request: Request):
    """返回前端需要的配置信息"""
    # 获取客户端请求的主机名
    client_host = request.client.host if request.client else "127.0.0.1"
    # 如果服务器绑定在 0.0.0.0，使用客户端连接的主机名
    server_host = client_host if settings.SERVER_HOST == "0.0.0.0" else settings.SERVER_HOST
    config = {
        "server_host": server_host,
        "server_port": settings.SERVER_PORT
    }
    return config

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    async def event_generator():
        try:
            # A. 会话管理 + 内存初始化
            session_manager.switch_session(request.session_id)
            chat_history = session_manager.get_current_history()
            last_graph = session_manager.get_current_graph()
            
            # 添加用户消息到内存系统
            session_manager.add_message("user", request.message)
            
            # 获取增强的 Agent 上下文（包含长期+短期记忆）
            try:
                agent_context = session_manager.get_agent_context()
                context_messages = agent_context.get("messages", chat_history.messages)
            except Exception:
                pass  # 静默处理上下文获取失败
                context_messages = chat_history.messages
            
            full_reply_text = ""
            
            # B. 使用状态机处理，并实现流式输出
            
            # 优先使用多智能体工作流
            use_multi_agent = True
            
            if use_multi_agent:
                yield format_sse_message({'type': 'thought', 'content': '启用多智能体工作流，正在协调多个专业智能体...'})

                # 创建新的Chat Agent实例，避免状态混乱
                current_chat_agent = get_blender_chat_agent()
                
                # 用于收集SSE消息的队列
                sse_messages = []
                
                # 状态变更回调函数，用于向前端发送通知
                async def session_state_callback(state_info):
                    """会话级别的状态变更回调函数"""
                    # 将状态变更消息添加到队列中
                    sse_messages.append(format_sse_message({'type': 'thought', 'content': f"{state_info['agent']}: {state_info['message']}"}))
                
                # 重新初始化状态机，使用会话级别的回调
                # 使用 Chat 中心化架构
                session_state_machine = ChatCentricStateMachine(
                    chat_agent=current_chat_agent, 
                    state_callback=session_state_callback
                )
                
                # [记忆记录] 状态机工作流开始
                session_manager.add_message(
                    "state_machine",
                    f"[执行开始] 启动状态机工作流: {request.message[:100]}..."
                )
                
                yield format_sse_message({'type': 'thought', 'content': '状态机工作流启动...'})
                
                # 执行状态机工作流
                result = await session_state_machine.run(request.message, session_id=request.session_id)
                
                # 发送状态机执行过程中的消息
                for msg in sse_messages:
                    yield msg
                
                yield format_sse_message({'type': 'thought', 'content': '状态机工作流完成'})
                
                if result.get("node_graph"):
                    # 成功生成材质
                    if isinstance(result["node_graph"], dict) and "chat_response" in result["node_graph"]:
                        # 聊天功能
                        chat_response = result["node_graph"]["chat_response"]
                        
                        # 流式传输聊天响应
                        yield format_sse_message({'type': 'text', 'content': chat_response})
                        
                        session_manager.add_message(
                            "chat_agent",
                            f"[执行成功] 聊天功能完成: {chat_response[:100]}..."
                        )
                    else:
                        # 材质生成 - 先存储到session_manager，不直接发送
                        session_manager.update_graph(result["node_graph"])
                        
                        # [记忆记录] 状态机工作流成功
                        node_count = len(result["node_graph"].nodes) if hasattr(result["node_graph"], 'nodes') else 0
                        session_manager.add_message(
                            "state_machine",
                            f"[执行成功] 状态机工作流完成，生成材质节点图，包含 {node_count} 个节点"
                        )
                        
                        # 通知前端节点数据已准备好（通过WebSocket）
                        try:
                            await notify_graph_ready(request.session_id)
                        except Exception as _e:
                            logger.warning(f"Failed to notify websocket client: {_e}")
                
                if not result.get("node_graph"):
                    # 生成失败：无有效节点数据
                    error_msg = ", ".join(result.get('error_list', ['Unknown error']))
                    
                    # [记忆记录] 状态机工作流失败
                    session_manager.add_message(
                        "state_machine",
                        f"[执行完成] 状态机工作流结束，但未生成有效节点。错误: {error_msg[:80]}"
                    )
                    
                    yield format_sse_message({'type': 'error', 'content': f'生成失败: {error_msg}'})
            
            # C. 更新对话历史 + AI 响应到内存系统
            chat_history.add_user_message(request.message)
            chat_history.add_ai_message(full_reply_text)
            session_manager.add_message("assistant", full_reply_text)
            
            # D. 检查是否需要归档到长期记忆
            archive_triggered = session_manager.check_and_archive()
            if archive_triggered:
                # 获取更新后的统计信息
                stats = session_manager.get_memory_stats()
                print(f"📊 归档后内存统计: {stats}")
                yield format_sse_message({'type': 'memory_archived', 'stats': stats})
            
            # E. 发送结束信号
            yield format_sse_message({'type': 'done', 'content': 'finished'})

        except Exception as e:
            # 捕获最外层（流式过程或会话管理）的严重错误
            traceback.print_exc()
            yield format_sse_message({'type': 'error', 'content': f'系统异常: {str(e)}'})
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get('/api/memory/stats/{session_id}')
async def get_memory_stats_endpoint(session_id: str):
    """获取指定会话的内存统计信息
    
    返回：
    - turn_count: 对话轮数
    - token_count: 已用 token 数
    - messages_count: 短期记忆消息数
    - last_updated: 最后更新时间
    """
    try:
        session_manager.switch_session(session_id)
        stats = session_manager.get_memory_stats()
        return {
            "session_id": session_id,
            "stats": stats,
            "success": True
        }
    except Exception as e:
        return {
            "session_id": session_id,
            "error": str(e),
            "success": False
        }

@app.post('/api/memory/archive/{session_id}')
async def manually_archive_memory(session_id: str):
    """手动触发指定会话的内存归档（用于测试和维护）
    
    返回：
    - success: 是否成功
    - message: 操作结果消息
    - stats: 归档后的统计信息
    """
    try:
        session_manager.switch_session(session_id)
        session_manager.check_and_archive()
        stats = session_manager.get_memory_stats()
        return {
            "session_id": session_id,
            "success": True,
            "message": "内存归档成功",
            "stats": stats
        }
    except Exception as e:
        return {
            "session_id": session_id,
            "success": False,
            "message": f"内存归档失败: {str(e)}"
        }

@app.get('/api/graph/{session_id}')
async def get_graph_endpoint(session_id: str):
    """获取指定会话的当前节点图
    
    返回：
    - session_id: 会话ID
    - graph: 节点图数据
    - success: 是否成功
    """
    try:
        session_manager.switch_session(session_id)
        graph = session_manager.get_graph(session_id)
        
        if graph is None:
            return {
                "session_id": session_id,
                "graph": None,
                "success": True
            }
        
        return {
            "session_id": session_id,
            "graph": graph,
            "success": True
        }
    except Exception as e:
        logger.error(f"get_graph_endpoint error: {e}")
        return {
            "session_id": session_id,
            "error": str(e),
            "success": False
        }

agents_registry = {
    "chat_agent": get_blender_chat_agent(),
    "material_agent": blender_agent,
    "artist_agent": artist_agent,
    "critic_agent": critic_agent
}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
