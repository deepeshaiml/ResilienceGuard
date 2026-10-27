from functools import lru_cache
from pathlib import Path
import os


ROOT = Path(__file__).resolve().parents[2]


class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'artifacts' / 'resilienceguard.db'}")
    data_root: Path = Path(os.getenv("DATA_ROOT", ROOT / "data")).resolve()
    restore_root: Path = Path(os.getenv("RESTORE_ROOT", ROOT / "artifacts" / "restores")).resolve()
    ollama_url: str = os.getenv("OLLAMA_URL", "")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")


@lru_cache
def get_settings() -> Settings:
    return Settings()
