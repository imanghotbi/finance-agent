from langchain_openai import ChatOpenAI
from src.core.config import settings
from typing import Optional, Dict, Any

class LLMFactory:
    @staticmethod
    def resolve_model_name(node_name: Optional[str] = None, model_name: Optional[str] = None) -> str:
        if model_name:
            return model_name
        if node_name:
            return settings.model_name_overrides.get(node_name, settings.model_name)
        return settings.model_name

    @staticmethod
    def get_model(temperature: float = 0.0, thinking:bool = True,
                top_p:Optional[float] = None, max_output_tokens:Optional[int] = None,
                structured_output=None, tools: Optional[list] = None,
                node_name: Optional[str] = None, model_name: Optional[str] = None):

        tools = tools or []
        resolved_model_name = LLMFactory.resolve_model_name(node_name=node_name, model_name=model_name)

        llm = ChatOpenAI(
            model=resolved_model_name,
            api_key=settings.model_api_key.get_secret_value(),
            base_url=settings.model_base_url,
            temperature=temperature,
            max_tokens=max_output_tokens or settings.max_tokens,
            top_p=top_p if top_p is not None else settings.top_p,
            reasoning_effort=settings.model_reasoning_effort if thinking else None
        )
        if structured_output:
            return llm.with_structured_output(structured_output)
        if tools:
            return llm.bind_tools(tools)
        return llm
