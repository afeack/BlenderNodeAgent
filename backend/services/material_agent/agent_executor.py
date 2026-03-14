# chains/agent_executor.py 定义 AgentExecutor 实例，集成工具调用 Agent。
import os
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# 导入内部组件
from models.material import MaterialGraph
from data.prompts.material_prompts import material_generation_template
from internal.utils.logger import BlenderAgentCallbackHandler
from internal.config.settings import settings
from tools import get_Material_tools
from langchain_openai import ChatOpenAI

def get_blender_agent():
    
    handler = BlenderAgentCallbackHandler()
    
    # 1. 初始化模型
    llm = ChatOpenAI(
        model=settings.MODEL_NAME,
        openai_api_key=settings.DASHSCOPE_API_KEY,
        openai_api_base=settings.DASHSCOPE_API_BASE,
        temperature=settings.MODEL_TEMPERATURE,
        streaming=True,  # 此时可以安全开启流式了
        callbacks=[handler]
    )
    
    # 2. 工具箱
    tools = get_Material_tools()
    
    # 3. 预处理逻辑
    preprocessor = RunnablePassthrough.assign(
        user_input=lambda x: x.get("user_input", ""),
        chat_history=lambda x: x.get("chat_history", []),
        context=lambda x: x.get("context", ""),
        style=lambda x: x.get("style", "")
    )
    
    # 4. 创建基础 Agent
    base_agent = create_tool_calling_agent(llm, tools, material_generation_template)
    
    # 5. 将预处理逻辑与 Agent 组合
    full_agent = preprocessor | base_agent
    
    # 6. 返回执行器
    return AgentExecutor(
        agent=full_agent, 
        tools=tools, 
        verbose=False, 
        callbacks=[handler],
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        max_iterations=10  # 限制最大迭代次数，防止无限循环
    )

# 导出实例
blender_agent = get_blender_agent()