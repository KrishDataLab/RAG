import re
from typing import Tuple

class SafetyGuardrails:
    INJECTION_PATTERNS = [
        r"ignore previous",
        r"reveal your system prompt",
        r"reveal",
        r"system prompt",
        r"you are now dan",
        r"sudo",
        r"rm -rf",
        r"bypass rules",
        r"act as administrator"
    ]

    @classmethod
    def sanitize_user_query(cls, query: str) -> str:
        cleaned = query.strip()
        return cleaned

    @classmethod
    def check_prompt_injection(cls, text: str) -> Tuple[bool, str]:
        lower_text = text.lower()
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, lower_text):
                return True, f"Blocked prompt injection pattern: {pattern}"
        return False, ""
