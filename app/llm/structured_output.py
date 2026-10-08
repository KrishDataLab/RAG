import json
import re
from typing import Type, TypeVar, Any
from pydantic import BaseModel
from app.core.exceptions import LLMProviderError

T = TypeVar("T", bound=BaseModel)

class StructuredOutputParser:
    @staticmethod
    def parse_json(raw_response: str, schema: Type[T]) -> T:
        cleaned = raw_response.strip()
        # Strip markdown ```json codeblocks if present
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(cleaned)
            return schema.model_validate(data)
        except Exception as e:
            # Fallback regex JSON extraction
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    return schema.model_validate(data)
                except Exception as inner_e:
                    pass
            raise LLMProviderError(f"Failed to parse LLM response into schema {schema.__name__}: {str(e)}")
