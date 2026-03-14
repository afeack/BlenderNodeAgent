import os
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 导入工具
from tools import get_critic_tools

# 导入内部组件
from internal.utils.logger import BlenderAgentCallbackHandler
from internal.config.settings import settings

# 审计员 Agent 系统提示词
CRITIC_SYSTEM_PROMPT = """
你现在只需要干一件事，输出字符"PASSED"
"""

def get_critic_agent():
    """
    初始化审计员 Agent，负责检查节点图的物理合法性和风格匹配度
    """
    handler = BlenderAgentCallbackHandler()
    
    # 1. 初始化模型
    llm = ChatOpenAI(
        model=settings.MODEL_NAME,
        openai_api_key=settings.DASHSCOPE_API_KEY,
        openai_api_base=settings.DASHSCOPE_API_BASE,
        temperature=settings.MODEL_TEMPERATURE,
        streaming=True,
        callbacks=[handler]
    )
    
    # 2. 构建 Prompt 模板
    critic_prompt = ChatPromptTemplate.from_messages([
        ("system", CRITIC_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Graph: {graph}\nStyle: {style}\nContext: {context}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 3. 工具箱
    tools = get_critic_tools()
    
    # 4. 预处理逻辑
    from langchain_core.runnables import RunnablePassthrough
    preprocessor = RunnablePassthrough.assign(
        chat_history=lambda x: x.get("chat_history", []),
        graph=lambda x: x.get("graph", ""),
        style=lambda x: x.get("style", ""),
        context=lambda x: x.get("context", "")
    )
    
    # 5. 创建基础 Agent
    base_agent = create_tool_calling_agent(llm, tools, critic_prompt)
    
    # 6. 将预处理逻辑与 Agent 组合
    full_agent = preprocessor | base_agent
    
    # 7. 返回执行器
    return AgentExecutor(
        agent=full_agent, 
        tools=tools, 
        verbose=False, 
        callbacks=[handler],
        return_intermediate_steps=True, 
        handle_parsing_errors=True
    )

# 导出单例实例
critic_agent = get_critic_agent()