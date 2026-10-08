from pathlib import Path
from app.core.config import BASE_DIR

class PromptManager:
    def __init__(self):
        self.prompts_dir = BASE_DIR / "prompts"

    def get_prompt(self, prompt_name: str) -> str:
        filepath = self.prompts_dir / prompt_name
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        raise FileNotFoundError(f"Prompt file {prompt_name} not found in {self.prompts_dir}")

    def render(self, prompt_name: str, **kwargs) -> str:
        template = self.get_prompt(prompt_name)
        return template.format(**kwargs)

prompt_manager = PromptManager()
