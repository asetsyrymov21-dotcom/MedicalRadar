from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from app import settings


GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


def translate_for_post(text: str, limit: int = 900) -> str:
    text = " ".join((text or "").split())
    if not text or not settings.TRANSLATE_TO_RUSSIAN:
        return text
    if looks_russian(text):
        return text
    translated = translate_with_google(text[:limit])
    return translated or text


def translate_with_google(text: str) -> str:
    params = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "auto",
            "tl": "ru",
            "dt": "t",
            "q": text,
        }
    )
    request = urllib.request.Request(
        f"{GOOGLE_TRANSLATE_URL}?{params}",
        headers={"User-Agent": "MedicalRadar/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
        return "".join(part[0] for part in data[0] if part and part[0]).strip()
    except Exception:
        return ""


def looks_russian(text: str) -> bool:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    if not letters:
        return True
    cyrillic = re.findall(r"[А-Яа-яЁё]", text)
    return len(cyrillic) / len(letters) > 0.45


def evidence_ru(value: str | None) -> str:
    return {
        "human_trial": "исследование на людях",
        "animal_study": "исследование на животных",
        "cell_study": "клеточное исследование",
        "press_release": "пресс-релиз",
        "unknown": "неясно",
    }.get(value or "unknown", value or "неясно")


def phase_ru(value: str | None) -> str:
    return {
        "phase_1": "фаза 1",
        "phase_2": "фаза 2",
        "phase_3": "фаза 3",
        "approved": "одобрено",
        "not_applicable": "не применимо",
        "unknown": "неясно",
    }.get(value or "unknown", value or "неясно")


def hype_ru(value: str | None) -> str:
    return {
        "low": "низкий",
        "medium": "средний",
        "high": "высокий",
    }.get(value or "medium", value or "средний")
