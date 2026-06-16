from __future__ import annotations

import email.utils
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


USER_AGENT = "MedicalRadar/0.1 (+https://github.com/asetsyrymov21-dotcom/MedicalRadar)"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"


@dataclass(frozen=True)
class TopicQuery:
    topic: str
    terms: list[str]


TOPIC_QUERIES = [
    TopicQuery("Longevity / омоложение", ["partial reprogramming", "epigenetic rejuvenation", "Life Biosciences", "cellular reprogramming"]),
    TopicQuery("Восстановление зрения", ["retina regeneration", "photoreceptor transplantation", "retinal organoids", "optogenetic vision restoration"]),
    TopicQuery("Регенерация зубов", ["tooth regrowth Japan", "USAG-1 antibody", "Toregem Biopharma", "tooth regeneration clinical trials"]),
    TopicQuery("Витилиго", ["JAK inhibitors vitiligo", "ruxolitinib vitiligo", "melanocyte transplantation vitiligo"]),
    TopicQuery("Рак / онкология", ["personalized cancer vaccines", "CAR-T solid tumors", "glioblastoma immunotherapy", "oncolytic viruses"]),
    TopicQuery("Ozempic / ожирение / мышцы", ["semaglutide muscle loss", "tirzepatide safety", "retatrutide", "myostatin inhibitors weight loss"]),
    TopicQuery("HIV / иммунитет", ["HIV cure latent reservoir", "broadly neutralizing antibodies HIV", "CRISPR HIV cure"]),
    TopicQuery("AI в медицине", ["AI drug discovery clinical trial", "AI-designed drugs", "generative biology biomarkers"]),
]


def collect_candidates(limit_per_topic: int = 5) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for topic in TOPIC_QUERIES:
        candidates.extend(collect_pubmed(topic, limit_per_topic))
        candidates.extend(collect_google_news(topic, limit_per_topic))
    return dedupe_candidates(candidates)


def collect_pubmed(topic: TopicQuery, limit: int) -> list[dict[str, Any]]:
    query = " OR ".join(f'"{term}"' for term in topic.terms)
    ids = pubmed_search(query, limit)
    if not ids:
        return []
    summaries = pubmed_summary(ids)
    items: list[dict[str, Any]] = []
    for summary in summaries:
        pubmed_id = summary.get("uid") or summary.get("pubmed_id")
        title = clean_text(summary.get("title", ""))
        pubdate = summary.get("pubdate") or summary.get("sortpubdate")
        source = summary.get("source") or "PubMed"
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/" if pubmed_id else None
        if not title or not url:
            continue
        items.append(
            {
                "title": title,
                "source": f"PubMed / {source}",
                "date": normalize_date(pubdate),
                "topic": topic.topic,
                "summary": clean_text(summary.get("fulljournalname", "")),
                "claims": f"PubMed indexed publication. PMID: {pubmed_id}",
                "url": url,
            }
        )
    return items


def pubmed_search(query: str, limit: int) -> list[str]:
    params = urllib.parse.urlencode(
        {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": str(limit),
            "sort": "pub+date",
        }
    )
    data = fetch_json(f"{PUBMED_SEARCH_URL}?{params}")
    return data.get("esearchresult", {}).get("idlist", [])


def pubmed_summary(ids: list[str]) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
    data = fetch_json(f"{PUBMED_SUMMARY_URL}?{params}")
    result = data.get("result", {})
    return [result[item_id] for item_id in result.get("uids", []) if item_id in result]


def collect_google_news(topic: TopicQuery, limit: int) -> list[dict[str, Any]]:
    query = " OR ".join(f'"{term}"' for term in topic.terms[:4])
    params = urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    xml_text = fetch_text(f"{GOOGLE_NEWS_RSS_URL}?{params}")
    if not xml_text:
        return []
    root = ET.fromstring(xml_text)
    items: list[dict[str, Any]] = []
    for item in root.findall(".//item")[:limit]:
        title = clean_text(find_text(item, "title"))
        link = clean_text(find_text(item, "link"))
        pub_date = normalize_date(find_text(item, "pubDate"))
        description = clean_text(strip_tags(find_text(item, "description")))
        source = clean_text(find_text(item, "source")) or "Google News"
        if not title or not link:
            continue
        items.append(
            {
                "title": title,
                "source": source,
                "date": pub_date,
                "topic": topic.topic,
                "summary": description,
                "claims": "News/RSS item; verify primary paper, trial registry, or company release.",
                "url": link,
            }
        )
    return items


def fetch_json(url: str) -> dict[str, Any]:
    text = fetch_text(url)
    if not text:
        return {}
    return json.loads(text)


def fetch_text(url: str, timeout: int = 15) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def dedupe_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = (item.get("url") or item.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def find_text(item: ET.Element, tag: str) -> str:
    found = item.find(tag)
    return found.text if found is not None and found.text else ""


def clean_text(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", value or "")).strip()


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "")


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.date().isoformat()
    except Exception:
        pass
    match = re.search(r"\b(19|20)\d{2}(?:[-/]\d{1,2})?(?:[-/]\d{1,2})?\b", value)
    if match:
        raw = match.group(0).replace("/", "-")
        parts = raw.split("-")
        if len(parts) == 1:
            return f"{parts[0]}-01-01"
        if len(parts) == 2:
            return f"{parts[0]}-{int(parts[1]):02d}-01"
        return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except Exception:
        return None
