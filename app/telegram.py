from __future__ import annotations

import html
import urllib.parse
import urllib.request
from typing import Any

from app import settings


def should_publish(item: dict[str, Any]) -> bool:
    mode = settings.MIN_HYPE_RISK_TO_PUBLISH
    if mode == "high_priority":
        return item.get("evidence_level") == "human_trial" or item.get("hype_risk") == "low"
    if mode == "skip_high_hype":
        return item.get("hype_risk") != "high"
    return True


def format_message(item: dict[str, Any]) -> str:
    title = html.escape(item.get("title") or "Untitled")
    topic = html.escape(item.get("topic") or "unknown")
    source = html.escape(item.get("source") or "unknown")
    date = html.escape(item.get("date") or item.get("created_at") or "unknown date")
    summary = html.escape(shorten(item.get("summary") or item.get("claims") or "", 700))
    evidence = html.escape(item.get("evidence_level") or "unknown")
    phase = html.escape(item.get("trial_phase") or "unknown")
    hype = html.escape(item.get("hype_risk") or "medium")
    relevance = html.escape(shorten(item.get("practical_relevance") or "", 350))
    url = html.escape(item.get("url") or "")

    parts = [
        f"<b>{title}</b>",
        "",
        f"<b>Topic:</b> {topic}",
        f"<b>Source:</b> {source} | {date}",
        f"<b>Evidence:</b> {evidence} / {phase}",
        f"<b>Hype risk:</b> {hype}",
    ]
    if summary:
        parts.extend(["", summary])
    if relevance:
        parts.extend(["", f"<b>Why it matters:</b> {relevance}"])
    if url:
        parts.extend(["", url])
    parts.extend(["", "<i>Monitoring only. Not medical advice.</i>"])
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
