"""Environment configuration; no credentials are needed for local catalogue use."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def settings():
    return {
        "DATA_PATH": os.getenv("TRIPGENIE_DATA_PATH", str(ROOT / "data/processed/india_tourism_processed.json")),
        "LOG_LEVEL": os.getenv("TRIPGENIE_LOG_LEVEL", "INFO"),
        "ALLOWED_ORIGINS": [origin.strip() for origin in os.getenv(
            "TRIPGENIE_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
        "MAX_CONTENT_LENGTH": 16 * 1024,
        "JSON_SORT_KEYS": False,
    }
