from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openai import ChatOpenAI
from src.core.config import settings
from typing import Optional

class LLMFactory:
    @staticmethod
    def get_model(temperature: float = 0.0, thinking:bool = True,
                top_p:Optional[float] = None, max_output_tokens:Optional[int] = None,
                structured_output=None,tools:list=[]):


        llm = ChatNVIDIA(
            model=settings.model_name,
            api_key=settings.model_api_key.get_secret_value(),
            temperature=temperature,
            max_output_tokens=max_output_tokens or settings.max_tokens,
            top_p= top_p or settings.top_p,
            extra_body = {'chat_template_kwargs':{'thinking':thinking}},
            proxies = settings.proxy_url
        )
        if structured_output:
            return llm.with_structured_output(structured_output)
        if tools:
            return llm.bind_tools(tools)
        return llm