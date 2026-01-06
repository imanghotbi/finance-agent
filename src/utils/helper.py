from typing import Any, Dict, Optional, Tuple, Type

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError


def create_prompt(system_prompt: str, user_message: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([("system", system_prompt), ("human", user_message)])


def _prompt_to_text(prompt_value: Any) -> str:
    if hasattr(prompt_value, "to_string"):
        return prompt_value.to_string()
    return str(prompt_value)


async def _invoke_structured_with_recovery(
    llm: Any,
    prompt_value: Any,
    schema_model: Type[BaseModel],
    fallback_prompt: Optional[str] = None,
) -> Tuple[BaseModel, Optional[Dict[str, str]]]:
    try:
        out = await llm.with_structured_output(schema_model).ainvoke(prompt_value)
        return out, None
    except Exception:
        prompt_text = _prompt_to_text(prompt_value)
        fix_prompt = f"""
        Return ONLY valid JSON matching this schema:
        {schema_model.model_json_schema()}
        No extra text. Use null when unknown.

        Original prompt:
        {prompt_text}
        """
        raw_msg = await llm.ainvoke(fix_prompt)
        raw = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        try:
            out = schema_model.model_validate_json(raw)
            return out, {"recovered": "fix_prompt"}
        except ValidationError:
            if fallback_prompt is None:
                fallback_prompt = f"""
Return ONLY valid JSON matching this schema:
{schema_model.model_json_schema()}
No extra text. Use null when unknown.
"""
            raw2_msg = await llm.ainvoke(fallback_prompt + "\n\n" + prompt_text)
            raw2 = raw2_msg.content if hasattr(raw2_msg, "content") else str(raw2_msg)
            out = schema_model.model_validate_json(raw2)
            return out, {"recovered": "json_only_fallback"}
