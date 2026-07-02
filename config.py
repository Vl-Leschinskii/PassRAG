from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""

    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_api_key: str = "lm-studio"
    lm_studio_model: str = "local-model"
    lm_studio_timeout: float = 120.0

    embedding_model: str = "intfloat/multilingual-e5-small"
    top_k: int = 3
    confidence_threshold: float = 0.4
    hotline: str = "309-10-10"

    @property
    def docx_path(self) -> Path:
        matches = list(ROOT_DIR.glob("*.docx"))
        if not matches:
            raise FileNotFoundError("DOCX с шаблонами не найден в корне проекта")
        return matches[0]

    @property
    def xlsx_path(self) -> Path:
        matches = list(ROOT_DIR.glob("*.xlsx"))
        if not matches:
            raise FileNotFoundError("XLSX с разметкой не найден в корне проекта")
        return matches[0]


settings = Settings()
