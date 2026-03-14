# prompts/material_prompts.py模板组装。将系统指令、历史记录占位符、用户输入串联成发送给 LLM 的最终 Prompt。
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from data.prompts.system_prompt import MATERIAL_SYSTEM_PROMPT

# 注意：变量名必须完全匹配 'agent_scratchpad'
material_generation_template = ChatPromptTemplate.from_messages([
    ("system", MATERIAL_SYSTEM_PROMPT + "\n\nCurrent Context: {context}"),
    MessagesPlaceholder(variable_name="chat_history"), 
    ("human", "{user_input}\n\nStyle Guide: {style}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])