import os
import yaml
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_yaml_config(filename: str) -> dict:
    filepath = BASE_DIR / "configs" / filename
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "AUTOSAR HLD Intelligence & Traceability Assistant (AHITA)"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    DATABASE_URL: str = f"sqlite:///{(BASE_DIR / 'data' / 'ahita.db').as_posix()}"
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploaded_pdfs")
    PROCESSED_DIR: str = str(BASE_DIR / "data" / "processed")
    
    # LLM Settings
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: str = "auto"
    
    # Config mappings
    app_config: dict = Field(default_factory=lambda: load_yaml_config("app.yaml"))
    model_config_data: dict = Field(default_factory=lambda: load_yaml_config("model.yaml"))
    retrieval_config: dict = Field(default_factory=lambda: load_yaml_config("retrieval.yaml"))

settings = Settings()

# Ensure data directories exist
for path_str in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, str(BASE_DIR / "data")]:
    os.makedirs(path_str, exist_ok=True)
