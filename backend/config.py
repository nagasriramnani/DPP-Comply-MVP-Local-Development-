import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    ENV: str = os.getenv("ENV", "development")
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
    AI_BACKEND: str = os.getenv("AI_BACKEND", "mock")  # 'mock' or 'openai'
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    ALLOW_ORIGINS: List[str] = field(default_factory=lambda: os.getenv("ALLOW_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(","))

settings = Settings()
