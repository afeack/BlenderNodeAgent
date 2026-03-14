import os
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 导入工具
from tools import get_artist_tools

# 导入内部组件
from internal.utils.logger import BlenderAgentCallbackHandler
from internal.config.settings import settings

# 艺术家 Agent 系统提示词
ARTIST_SYSTEM_PROMPT = """
你是一位专业的 3D 材质艺术家，擅长分析用户需求并确定适合的材质风格和色彩方案。

# 你的职责
1. 分析用户输入，理解材质需求
2. 确定适合的风格类型（如 PBR、NPR、卡通等）
3. 设计色彩方案和材质特性
4. 提供简洁、结构化的风格指导

# 输出内容
请提供以下风格指导：

1. **风格类型**：明确指定风格（PBR、NPR、卡通、写实等）
2. **色彩方案**：
   - 主色调（RGB值或颜色名称）
   - 辅助色（如有）
   - 色彩饱和度和亮度建议
3. **材质特性**：
   - 光泽度（0-1）
   - 粗糙度（0-1）
   - 金属度（0-1）
   - 透明度（0-1，如适用）
   - 其他相关特性
4. **特殊效果**：如需要，描述特殊效果（如反射、折射、发光等）

# 输出格式
使用简洁、结构化的文本描述，避免技术术语过强。保持艺术指导的性质，让下游Material Agent有发挥空间。

# 示例输出
风格类型：PBR写实风格
色彩方案：主色调银灰色（RGB: 0.7, 0.7, 0.75），辅助色深灰色（RGB: 0.4, 0.4, 0.45）
材质特性：光泽度0.8，粗糙度0.3，金属度1.0，透明度0
特殊效果：强金属反射，轻微环境光反射
"""

def get_artist_agent():
    """
    初始化艺术家 Agent，负责风格和色彩方案设计
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
    artist_prompt = ChatPromptTemplate.from_messages([
        ("system", ARTIST_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{user_input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 3. 工具箱
    tools = get_artist_tools()
    
    # 4. 预处理逻辑
    from langchain_core.runnables import RunnablePassthrough
    preprocessor = RunnablePassthrough.assign(
        user_input=lambda x: x.get("user_input", ""),
        chat_history=lambda x: x.get("chat_history", [])
    )
    
    # 5. 创建基础 Agent
    base_agent = create_tool_calling_agent(llm, tools, artist_prompt)
    
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
artist_agent = get_artist_agent()