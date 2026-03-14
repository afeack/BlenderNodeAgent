# chains/chat_agent.py
import os
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import PromptTemplate

# 导入内部组件
from data.prompts.system_prompt import CHAT_SYSTEM_PROMPT
from internal.utils.logger import BlenderAgentCallbackHandler
from internal.config.settings import settings
from tools import get_chat_tools

def get_blender_chat_agent():
    """
    初始化 Blender 技术咨询 Agent，使用 React Agent 支持思考过程
    """
    handler = BlenderAgentCallbackHandler()
    
    # 1. 初始化模型 (复用 settings 中的通义千问配置)
    llm = ChatOpenAI(
        model=settings.MODEL_NAME,
        openai_api_key=settings.DASHSCOPE_API_KEY,
        openai_api_base=settings.DASHSCOPE_API_BASE,
        temperature=settings.MODEL_TEMPERATURE,
        streaming=True,
        callbacks=[handler]
    )
    
    # 2. 构建 React Agent 专用的 Prompt 模板
    react_prompt = PromptTemplate.from_template(
        """
        {system_prompt}
        
        Answer the following questions as best you can. You have access to the following tools:
        
        {tools}
        
        Use the following format:
        
        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question
        
        Question: {input}
        {agent_scratchpad}
        """
    )

    # 3. 工具箱 (包含Agent调用工具)
    tools = get_chat_tools()
    
    # 4. 预处理逻辑 (简单透传，保持 LCEL 链条结构一致)
    preprocessor = RunnablePassthrough.assign(
        system_prompt=lambda x: CHAT_SYSTEM_PROMPT,
        tools=lambda x: "\n".join([f"{tool.name}: {tool.description}" for tool in tools]),
        tool_names=lambda x: ", ".join([tool.name for tool in tools]),
        input=lambda x: x.get("user_input", ""),
        agent_scratchpad=lambda x: x.get("agent_scratchpad", "")
    )
    
    # 5. 创建基础 Agent (使用 React Agent)
    base_agent = create_react_agent(llm, tools, react_prompt)
    
    # 6. 将预处理逻辑与 Agent 组合
    full_agent = preprocessor | base_agent
    
    # 7. 返回执行器
    return AgentExecutor(
        agent=full_agent, 
        tools=tools, 
        verbose=True,  # 启用详细输出以查看思考过程s
        callbacks=[handler],
        return_intermediate_steps=True, 
        handle_parsing_errors=True,
        max_iterations=15,  # 减少最大迭代次数，避免无限循环
        early_stopping_method="force"  # 强制在Final Answer后停止
    )

# 导出单例实例
blender_chat_agent = get_blender_chat_agent()