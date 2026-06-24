import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()  # read a local .env if present; real env vars still win
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for live agent runs")
        return cls(api_key=api_key, model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))

