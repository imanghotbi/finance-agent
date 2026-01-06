from langchain_core.prompts import ChatPromptTemplate

def create_prompt(system_prompt:str , user_message:str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([("system", system_prompt),("human", user_message)])