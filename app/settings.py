from __future__ import annotations

import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


DATABASE_PATH = os.getenv("MEDICAL_RADAR_DB_PATH", "medical_radar.db")
ENABLE_SCHEDULER = env_bool("MEDICAL_RADAR_ENABLE_SCHEDULER", False)
POLL_MINUTES = max(env_int("MEDICAL_RADAR_POLL_MINUTES", 180), 15)
COLLECT_LIMIT_PER_TOPIC = max(env_int("MEDICAL_RADAR_COLLECT_LIMIT_PER_TOPIC", 5), 1)
MIN_HYPE_RISK_TO_PUBLISH = os.getenv("MEDICAL_RADAR_MIN_PUBLISH_MODE", "all").strip().lower()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_DRY_RUN = env_bool("TELEGRAM_DRY_RUN", True)
