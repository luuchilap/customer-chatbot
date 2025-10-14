from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool
from langchain.memory import ConversationBufferWindowMemory
from .prompt import get_system_instructions


def build_agent(
    llm: ChatOpenAI,
    tools: List[BaseTool],
    memory: Optional[ConversationBufferWindowMemory] = None,
) -> AgentExecutor:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", get_system_instructions()),
            MessagesPlaceholder(variable_name="chat_history"),
            # Required by create_openai_tools_agent to accumulate intermediate tool calls
            MessagesPlaceholder(variable_name="agent_scratchpad"),
            ("human", "{input}"),
        ]
    )
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        return_intermediate_steps=True,
        memory=memory,
    )


