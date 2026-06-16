from __future__ import annotations

import html
import urllib.parse
import urllib.request
from typing import Any

from app import settings
from app.translator import evidence_ru, hype_ru, phase_ru, translate_for_post


def should_publish(item: dict[str, Any]) -> bool:
    mode = settings.MIN_HYPE_RISK_TO_PUBLISH
    if mode == "high_priority":
        return item.get("evidence_level") == "human_trial" or item.get("hype_risk") == "low"
    if mode == "skip_high_hype":
        return item.get("hype_risk") != "high"
    return True


def format_message(item: dict[str, Any]) -> str:
    title = html.escape(translate_for_post(item.get("title") or "Без названия", 250))
    topic = html.escape(item.get("topic") or "unknown")
    source = html.escape(item.get("source") or "unknown")
    date = html.escape(item.get("date") or item.get("created_at") or "дата неизвестна")
    summary = html.escape(shorten(translate_for_post(item.get("summary") or item.get("claims") or "", 700), 700))
    evidence = html.escape(evidence_ru(item.get("evidence_level")))
    phase = html.escape(phase_ru(item.get("trial_phase")))
    hype = html.escape(hype_ru(item.get("hype_risk")))
    relevance = html.escape(shorten(translate_for_post(item.get("practical_relevance") or "", 350), 350))
    url = html.escape(item.get("url") or "")

    parts = [
        f"<b>{title}</b>",
        "",
        f"<b>Тема:</b> {topic}",
        f"<b>Источник:</b> {source} | {date}",
        f"<b>Доказательность:</b> {evidence} / {phase}",
        f"<b>Риск хайпа:</b> {hype}",
    ]
    if summary:
        parts.extend(["", summary])
    if relevance:
        parts.extend(["", f"<b>Почему важно:</b> {relevance}"])
    if url:
        parts.extend(["", url])
    parts.extend(["", "<i>Только мониторинг и аналитика. Не медицинская рекомендация.</i>"])
    return "\n".join(parts)


def publish_to_telegram(item: dict[str, Any]) -> tuple[bool, str]:
    if settings.TELEGRAM_DRY_RUN:
        return True, "dry_run"
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False, "telegram_not_configured"

    payload = urllib.parse.urlencode(
        {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": format_message(item),
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        }
    ).encode("utf-8")
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    request = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status == 200, response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return False, str(exc)


def shorten(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."
