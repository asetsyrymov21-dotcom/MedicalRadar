from __future__ import annotations

import re
import sqlite3
import asyncio
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field, HttpUrl

from app import settings
from app.collector import TOPIC_QUERIES, TopicQuery


DATABASE_PATH = Path(settings.DATABASE_PATH)

EvidenceLevel = Literal[
    "human_trial",
    "animal_study",
    "cell_study",
    "press_release",
    "unknown",
]
TrialPhase = Literal[
    "phase_1",
    "phase_2",
    "phase_3",
    "approved",
    "not_applicable",
    "unknown",
]
HypeRisk = Literal["low", "medium", "high"]


INITIAL_TOPICS = [
    {
        "name": "Longevity / омоложение",
        "keywords": [
            "Life Biosciences",
            "ER-100",
            "ER-300",
            "partial reprogramming",
            "epigenetic rejuvenation",
            "cellular reprogramming",
            "age-related diseases",
        ],
    },
    {
        "name": "Восстановление зрения",
        "keywords": [
            "retina regeneration",
            "photoreceptor transplantation",
            "retinal organoids",
            "stem cell therapy blindness",
            "gene therapy inherited retinal disease",
            "optogenetic vision restoration",
            "South Korea vision restoration research",
        ],
    },
    {
        "name": "Регенерация зубов",
        "keywords": [
            "tooth regrowth Japan",
            "USAG-1 antibody",
            "third dentition drug",
            "Toregem Biopharma",
            "tooth regeneration clinical trials",
        ],
    },
    {
        "name": "Витилиго",
        "keywords": [
            "JAK inhibitors",
            "ruxolitinib",
            "topical JAK vitiligo",
            "melanocyte transplantation",
            "autoimmune vitiligo",
            "stress and vitiligo",
        ],
    },
    {
        "name": "Рак / онкология",
        "keywords": [
            "cancer immunotherapy",
            "oncolytic viruses",
            "pancreatic cancer metastatic treatment",
            "glioblastoma immunotherapy",
            "personalized cancer vaccines",
            "CAR-T solid tumors",
            "TCR therapy",
            "AI cancer drug discovery",
            "Kevin Harrington cancer research",
        ],
    },
    {
        "name": "Ozempic / ожирение / мышцы",
        "keywords": [
            "semaglutide",
            "Ozempic safety",
            "tirzepatide",
            "retatrutide",
            "orforglipron",
            "Scholar Rock",
            "apitegromab",
            "myostatin inhibitors",
            "muscle preservation during weight loss",
        ],
    },
    {
        "name": "HIV / иммунитет",
        "keywords": [
            "HIV cure research",
            "latent reservoir",
            "broadly neutralizing antibodies",
            "CRISPR HIV cure",
            "therapeutic HIV vaccine",
            "universal immune recognition",
        ],
    },
    {
        "name": "AI в медицине",
        "keywords": [
            "AI drug discovery",
            "AI-designed drugs in clinical trials",
            "biomarkers",
            "cancer drug discovery",
            "generative biology",
            "clinical trial analysis",
        ],
    },
]

INITIAL_WATCHLIST = [
    {
        "name": "David Sinclair",
        "topic": "Longevity / омоложение",
        "keywords": [
            "David Sinclair",
            "David A. Sinclair",
            "Sinclair Lab",
            "Sinclair longevity",
            "Sinclair aging",
            "Sinclair epigenetic reprogramming",
            "Life Biosciences",
            "ER-100",
            "ER-300",
        ],
        "notes": "Aging, epigenetics, partial reprogramming, Life Biosciences.",
    },
    {
        "name": "Professor Harrington",
        "topic": "Рак / онкология",
        "keywords": [
            "Kevin Harrington",
            "Kevin J. Harrington",
            "Professor Harrington cancer",
            "Harrington oncology",
            "Harrington immunotherapy",
            "Harrington oncolytic virus",
        ],
        "notes": "Likely Kevin Harrington in oncology; verify exact person if needed.",
    },
]


class TopicCreate(BaseModel):
    name: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)


class TopicUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    keywords: list[str] | None = None


class TopicOut(TopicCreate):
    id: int
    created_at: str


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1)
    topic: str = Field(default="unknown")
    keywords: list[str] = Field(default_factory=list)
    notes: str = Field(default="")
    active: bool = True


class WatchlistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    topic: str | None = None
    keywords: list[str] | None = None
    notes: str | None = None
    active: bool | None = None


class WatchlistOut(WatchlistCreate):
    id: int
    created_at: str


class NewsBase(BaseModel):
    title: str = Field(min_length=1)
    source: str = Field(default="unknown")
    date: str | None = None
    topic: str = Field(default="unknown")
    summary: str = Field(default="")
    claims: str = Field(default="")
    evidence_level: EvidenceLevel = "unknown"
    trial_phase: TrialPhase = "unknown"
    patient_count: int | None = Field(default=None, ge=0)
    result_strength: str = Field(default="unknown")
    safety_notes: str = Field(default="")
    hype_risk: HypeRisk = "medium"
    practical_relevance: str = Field(default="")
    url: HttpUrl | str | None = None
    needs_verification: bool = False
    watchlist_matches: str = ""


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    source: str | None = None
    date: str | None = None
    topic: str | None = None
    summary: str | None = None
    claims: str | None = None
    evidence_level: EvidenceLevel | None = None
    trial_phase: TrialPhase | None = None
    patient_count: int | None = Field(default=None, ge=0)
    result_strength: str | None = None
    safety_notes: str | None = None
    hype_risk: HypeRisk | None = None
    practical_relevance: str | None = None
    url: HttpUrl | str | None = None
    needs_verification: bool | None = None
    watchlist_matches: str | None = None


class NewsOut(NewsBase):
    id: int
    created_at: str


class EvaluationInput(BaseModel):
    title: str = ""
    source: str = ""
    summary: str = ""
    claims: str = ""
    url: str | None = None


class EvaluationOut(BaseModel):
    evidence_level: EvidenceLevel
    trial_phase: TrialPhase
    patient_count: int | None
    result_strength: str
    safety_notes: str
    hype_risk: HypeRisk
    practical_relevance: str
    needs_verification: bool
    rationale: list[str]


class CollectRunOut(BaseModel):
    fetched: int
    inserted: int
    duplicates: int


class PublishRunOut(BaseModel):
    scanned: int
    published: int
    skipped: int
    failed: int
    dry_run: bool


app = FastAPI(
    title="Medical Radar",
    description="Personal medical topic monitor with evidence and hype-risk labeling.",
    version="0.1.0",
)

worker_task: asyncio.Task | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    if "keywords" in item:
        item["keywords"] = [k for k in item["keywords"].split("\n") if k]
    return item


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                keywords TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                date TEXT,
                topic TEXT NOT NULL,
                summary TEXT NOT NULL,
                claims TEXT NOT NULL,
                evidence_level TEXT NOT NULL,
                trial_phase TEXT NOT NULL,
                patient_count INTEGER,
                result_strength TEXT NOT NULL,
                safety_notes TEXT NOT NULL,
                hype_risk TEXT NOT NULL,
                practical_relevance TEXT NOT NULL,
                url TEXT,
                needs_verification INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        ensure_news_column(db, "published_to_telegram", "INTEGER NOT NULL DEFAULT 0")
        ensure_news_column(db, "published_at", "TEXT")
        ensure_news_column(db, "telegram_error", "TEXT")
        ensure_news_column(db, "watchlist_matches", "TEXT NOT NULL DEFAULT ''")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_news_url_unique ON news(url) WHERE url IS NOT NULL")
        db.execute("CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_to_telegram, created_at)")
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                topic TEXT NOT NULL,
                keywords TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_active ON watchlist(active)")
        for topic in INITIAL_TOPICS:
            db.execute(
                """
                INSERT OR IGNORE INTO topics (name, keywords, created_at)
                VALUES (?, ?, ?)
                """,
                (topic["name"], "\n".join(topic["keywords"]), now_iso()),
            )
        for item in INITIAL_WATCHLIST:
            db.execute(
                """
                INSERT OR IGNORE INTO watchlist (name, topic, keywords, notes, active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (item["name"], item["topic"], "\n".join(item["keywords"]), item["notes"], now_iso()),
            )
        db.commit()


@app.on_event("startup")
async def startup() -> None:
    init_db()
    start_background_worker()


@app.on_event("shutdown")
def shutdown() -> None:
    global worker_task
    if worker_task:
        worker_task.cancel()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Medical Radar</title>
        <style>
          body { margin: 0; font-family: Arial, sans-serif; background: #f7f7f4; color: #1f2933; }
          header { padding: 28px 32px; background: #16324f; color: white; }
          main { max-width: 1120px; margin: 0 auto; padding: 24px; }
          h1 { margin: 0 0 8px; font-size: 30px; }
          h2 { margin: 28px 0 12px; font-size: 20px; }
          .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
          .card { background: white; border: 1px solid #d9e0e7; border-radius: 8px; padding: 14px; }
          .muted { color: #64748b; }
          .tag { display: inline-block; margin: 4px 4px 0 0; padding: 3px 7px; border-radius: 999px; background: #e8eef4; font-size: 12px; }
          code { background: #eef2f6; padding: 2px 4px; border-radius: 4px; }
          a { color: #0b5cad; }
        </style>
      </head>
      <body>
        <header>
          <h1>Medical Radar</h1>
          <div>Personal medical news monitor with evidence and hype-risk labeling.</div>
        </header>
        <main>
          <section>
            <h2>API</h2>
            <div class="grid">
              <div class="card"><strong>Topics</strong><p class="muted"><code>GET /topics</code><br><code>POST /topics</code></p></div>
              <div class="card"><strong>Watchlist</strong><p class="muted"><code>GET /watchlist</code><br><code>POST /watchlist</code></p></div>
              <div class="card"><strong>News</strong><p class="muted"><code>GET /news</code><br><code>POST /news</code></p></div>
              <div class="card"><strong>Evaluation</strong><p class="muted"><code>POST /news/evaluate</code><br><code>POST /news/{id}/evaluate</code></p></div>
              <div class="card"><strong>Collector</strong><p class="muted"><code>POST /collect/run</code><br><code>POST /telegram/publish-pending</code></p></div>
              <div class="card"><strong>Docs</strong><p class="muted"><a href="/docs">Open Swagger UI</a></p></div>
            </div>
          </section>
          <section>
            <h2>Evidence Labels</h2>
            <span class="tag">human_trial</span>
            <span class="tag">animal_study</span>
            <span class="tag">cell_study</span>
            <span class="tag">press_release</span>
            <span class="tag">unknown</span>
          </section>
        </main>
      </body>
    </html>
    """


@app.get("/topics", response_model=list[TopicOut])
def list_topics() -> list[dict[str, Any]]:
    with closing(connect()) as db:
        rows = db.execute("SELECT * FROM topics ORDER BY name").fetchall()
        return [row_to_dict(row) for row in rows]


@app.post("/topics", response_model=TopicOut, status_code=201)
def create_topic(topic: TopicCreate) -> dict[str, Any]:
    try:
        with closing(connect()) as db:
            cursor = db.execute(
                "INSERT INTO topics (name, keywords, created_at) VALUES (?, ?, ?)",
                (topic.name, "\n".join(topic.keywords), now_iso()),
            )
            db.commit()
            row = db.execute("SELECT * FROM topics WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Topic already exists") from exc


@app.patch("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: int, topic: TopicUpdate) -> dict[str, Any]:
    existing = get_topic_row(topic_id)
    values = {
        "name": topic.name if topic.name is not None else existing["name"],
        "keywords": "\n".join(topic.keywords) if topic.keywords is not None else existing["keywords"],
    }
    with closing(connect()) as db:
        db.execute(
            "UPDATE topics SET name = ?, keywords = ? WHERE id = ?",
            (values["name"], values["keywords"], topic_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        return row_to_dict(row)


@app.delete("/topics/{topic_id}", status_code=204, response_class=Response, response_model=None)
def delete_topic(topic_id: int):
    get_topic_row(topic_id)
    with closing(connect()) as db:
        db.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        db.commit()


@app.get("/watchlist", response_model=list[WatchlistOut])
def list_watchlist(active: bool | None = Query(default=None)) -> list[dict[str, Any]]:
    with closing(connect()) as db:
        if active is None:
            rows = db.execute("SELECT * FROM watchlist ORDER BY name").fetchall()
        else:
            rows = db.execute("SELECT * FROM watchlist WHERE active = ? ORDER BY name", (1 if active else 0,)).fetchall()
        return [row_to_watchlist(row) for row in rows]


@app.post("/watchlist", response_model=WatchlistOut, status_code=201)
def create_watchlist(item: WatchlistCreate) -> dict[str, Any]:
    keywords = item.keywords or [item.name]
    try:
        with closing(connect()) as db:
            cursor = db.execute(
                """
                INSERT INTO watchlist (name, topic, keywords, notes, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item.name, item.topic, "\n".join(keywords), item.notes, 1 if item.active else 0, now_iso()),
            )
            db.commit()
            row = db.execute("SELECT * FROM watchlist WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_watchlist(row)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Watchlist item already exists") from exc


@app.patch("/watchlist/{item_id}", response_model=WatchlistOut)
def update_watchlist(item_id: int, item: WatchlistUpdate) -> dict[str, Any]:
    existing = get_watchlist_row(item_id)
    with closing(connect()) as db:
        db.execute(
            """
            UPDATE watchlist
            SET name = ?, topic = ?, keywords = ?, notes = ?, active = ?
            WHERE id = ?
            """,
            (
                item.name if item.name is not None else existing["name"],
                item.topic if item.topic is not None else existing["topic"],
                "\n".join(item.keywords) if item.keywords is not None else existing["keywords"],
                item.notes if item.notes is not None else existing["notes"],
                1 if (item.active if item.active is not None else bool(existing["active"])) else 0,
                item_id,
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM watchlist WHERE id = ?", (item_id,)).fetchone()
        return row_to_watchlist(row)


@app.delete("/watchlist/{item_id}", status_code=204, response_class=Response, response_model=None)
def delete_watchlist(item_id: int):
    get_watchlist_row(item_id)
    with closing(connect()) as db:
        db.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))
        db.commit()


@app.get("/news", response_model=list[NewsOut])
def list_news(
    topic: str | None = Query(default=None),
    evidence_level: EvidenceLevel | None = Query(default=None),
    hype_risk: HypeRisk | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    where = []
    params: list[Any] = []
    if topic:
        where.append("topic = ?")
        params.append(topic)
    if evidence_level:
        where.append("evidence_level = ?")
        params.append(evidence_level)
    if hype_risk:
        where.append("hype_risk = ?")
        params.append(hype_risk)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with closing(connect()) as db:
        rows = db.execute(
            f"SELECT * FROM news {clause} ORDER BY COALESCE(date, created_at) DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [row_to_news(row) for row in rows]


@app.post("/news", response_model=NewsOut, status_code=201)
def create_news(news: NewsCreate) -> dict[str, Any]:
    data = news.model_dump()
    if data["evidence_level"] == "unknown" and data["trial_phase"] == "unknown":
        evaluated = evaluate_text(
            EvaluationInput(
                title=data["title"],
                source=data["source"],
                summary=data["summary"],
                claims=data["claims"],
                url=str(data["url"]) if data["url"] else None,
            )
        )
        data.update(evaluated.model_dump(exclude={"rationale"}))

    inserted, item = insert_news_data(data)
    if not inserted:
        raise HTTPException(status_code=409, detail="News item already exists")
    return item


@app.get("/news/{news_id}", response_model=NewsOut)
def get_news(news_id: int) -> dict[str, Any]:
    return row_to_news(get_news_row(news_id))


@app.patch("/news/{news_id}", response_model=NewsOut)
def update_news(news_id: int, news: NewsUpdate) -> dict[str, Any]:
    existing = row_to_news(get_news_row(news_id))
    update = news.model_dump(exclude_unset=True)
    merged = {**existing, **update}
    with closing(connect()) as db:
        db.execute(
            """
            UPDATE news SET
                title = ?, source = ?, date = ?, topic = ?, summary = ?, claims = ?,
                evidence_level = ?, trial_phase = ?, patient_count = ?,
                result_strength = ?, safety_notes = ?, hype_risk = ?,
                practical_relevance = ?, url = ?, needs_verification = ?,
                watchlist_matches = ?
            WHERE id = ?
            """,
            (*news_values(merged)[:-1], news_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
        return row_to_news(row)


@app.delete("/news/{news_id}", status_code=204, response_class=Response, response_model=None)
def delete_news(news_id: int):
    get_news_row(news_id)
    with closing(connect()) as db:
        db.execute("DELETE FROM news WHERE id = ?", (news_id,))
        db.commit()


@app.post("/news/evaluate", response_model=EvaluationOut)
def evaluate_news(payload: EvaluationInput) -> EvaluationOut:
    return evaluate_text(payload)


@app.post("/news/{news_id}/evaluate", response_model=NewsOut)
def evaluate_existing_news(news_id: int) -> dict[str, Any]:
    row = row_to_news(get_news_row(news_id))
    evaluated = evaluate_text(
        EvaluationInput(
            title=row["title"],
            source=row["source"],
            summary=row["summary"],
            claims=row["claims"],
            url=row["url"],
        )
    )
    update = NewsUpdate(**evaluated.model_dump(exclude={"rationale"}))
    return update_news(news_id, update)


@app.post("/collect/run", response_model=CollectRunOut)
def run_collection(limit_per_topic: int = Query(default=settings.COLLECT_LIMIT_PER_TOPIC, ge=1, le=20)) -> CollectRunOut:
    from app.collector import collect_candidates

    candidates = collect_candidates(limit_per_topic=limit_per_topic, topic_queries=collector_queries())
    inserted = 0
    duplicates = 0
    for candidate in candidates:
        evaluated = evaluate_text(
            EvaluationInput(
                title=candidate.get("title", ""),
                source=candidate.get("source", ""),
                summary=candidate.get("summary", ""),
                claims=candidate.get("claims", ""),
                url=candidate.get("url"),
            )
        )
        candidate.update(evaluated.model_dump(exclude={"rationale"}))
        matches = [candidate.get("watchlist_matches", ""), match_watchlist(candidate)]
        candidate["watchlist_matches"] = ", ".join(dict.fromkeys(m for m in matches if m))
        was_inserted, _ = insert_news_data(candidate)
        if was_inserted:
            inserted += 1
        else:
            duplicates += 1
    return CollectRunOut(fetched=len(candidates), inserted=inserted, duplicates=duplicates)


@app.post("/telegram/publish-pending", response_model=PublishRunOut)
def publish_pending(limit: int = Query(default=10, ge=1, le=50)) -> PublishRunOut:
    from app.telegram import publish_to_telegram, should_publish

    with closing(connect()) as db:
        rows = db.execute(
            """
            SELECT * FROM news
            WHERE published_to_telegram = 0
            ORDER BY COALESCE(date, created_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    published = 0
    skipped = 0
    failed = 0
    for row in rows:
        item = row_to_news(row)
        if not should_publish(item):
            mark_telegram_result(item["id"], False, "skipped_by_publish_mode", mark_done=True)
            skipped += 1
            continue
        ok, detail = publish_to_telegram(item)
        mark_telegram_result(item["id"], ok, detail, mark_done=ok)
        if ok:
            published += 1
        else:
            failed += 1
    return PublishRunOut(
        scanned=len(rows),
        published=published,
        skipped=skipped,
        failed=failed,
        dry_run=settings.TELEGRAM_DRY_RUN,
    )


@app.get("/scheduler")
def scheduler_status() -> dict[str, Any]:
    return {
        "enabled": settings.ENABLE_SCHEDULER,
        "poll_minutes": settings.POLL_MINUTES,
        "running": worker_task is not None and not worker_task.done(),
        "telegram_dry_run": settings.TELEGRAM_DRY_RUN,
        "publish_require_watchlist": settings.PUBLISH_REQUIRE_WATCHLIST,
        "collect_broad_topics": settings.COLLECT_BROAD_TOPICS,
    }


def get_topic_row(topic_id: int) -> sqlite3.Row:
    with closing(connect()) as db:
        row = db.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Topic not found")
        return row


def get_news_row(news_id: int) -> sqlite3.Row:
    with closing(connect()) as db:
        row = db.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="News item not found")
        return row


def get_watchlist_row(item_id: int) -> sqlite3.Row:
    with closing(connect()) as db:
        row = db.execute("SELECT * FROM watchlist WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Watchlist item not found")
        return row


def ensure_news_column(db: sqlite3.Connection, name: str, definition: str) -> None:
    columns = {row["name"] for row in db.execute("PRAGMA table_info(news)").fetchall()}
    if name not in columns:
        db.execute(f"ALTER TABLE news ADD COLUMN {name} {definition}")


def row_to_news(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["needs_verification"] = bool(item["needs_verification"])
    if "published_to_telegram" in item:
        item["published_to_telegram"] = bool(item["published_to_telegram"])
    return item


def row_to_watchlist(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["keywords"] = [k for k in item["keywords"].split("\n") if k]
    item["active"] = bool(item["active"])
    return item


def active_watchlist() -> list[dict[str, Any]]:
    with closing(connect()) as db:
        rows = db.execute("SELECT * FROM watchlist WHERE active = 1 ORDER BY name").fetchall()
        return [row_to_watchlist(row) for row in rows]


def collector_queries() -> list[TopicQuery]:
    queries: list[TopicQuery] = []
    for item in active_watchlist():
        terms = item["keywords"] or [item["name"]]
        queries.append(TopicQuery(item["topic"], terms, item["name"]))
    if settings.COLLECT_BROAD_TOPICS:
        queries.extend(TOPIC_QUERIES)
    return queries or TOPIC_QUERIES


def match_watchlist(data: dict[str, Any]) -> str:
    text = " ".join(
        str(data.get(field) or "")
        for field in ["title", "source", "summary", "claims", "url", "topic"]
    ).lower()
    matches: list[str] = []
    for item in active_watchlist():
        for keyword in item["keywords"] or [item["name"]]:
            if keyword.lower() in text:
                matches.append(item["name"])
                break
    return ", ".join(dict.fromkeys(matches))


def insert_news_data(data: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    with closing(connect()) as db:
        try:
            cursor = db.execute(
                """
                INSERT INTO news (
                    title, source, date, topic, summary, claims, evidence_level,
                    trial_phase, patient_count, result_strength, safety_notes,
                    hype_risk, practical_relevance, url, needs_verification,
                    watchlist_matches, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                news_values(data),
            )
            db.commit()
            row = db.execute("SELECT * FROM news WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return True, row_to_news(row)
        except sqlite3.IntegrityError:
            row = None
            if data.get("url"):
                row = db.execute("SELECT * FROM news WHERE url = ?", (str(data["url"]),)).fetchone()
            if row is None:
                raise
            return False, row_to_news(row)


def mark_telegram_result(news_id: int, ok: bool, detail: str, mark_done: bool) -> None:
    with closing(connect()) as db:
        db.execute(
            """
            UPDATE news
            SET published_to_telegram = ?,
                published_at = ?,
                telegram_error = ?
            WHERE id = ?
            """,
            (1 if mark_done else 0, now_iso() if ok or mark_done else None, None if ok else detail[:1000], news_id),
        )
        db.commit()


def start_background_worker() -> None:
    global worker_task
    if not settings.ENABLE_SCHEDULER or worker_task is not None:
        return
    worker_task = asyncio.create_task(background_worker())


async def background_worker() -> None:
    while True:
        try:
            await asyncio.to_thread(run_collection, settings.COLLECT_LIMIT_PER_TOPIC)
            await asyncio.to_thread(publish_pending, 20)
        except Exception:
            pass
        await asyncio.sleep(settings.POLL_MINUTES * 60)


def news_values(data: dict[str, Any]) -> tuple[Any, ...]:
    return (
        data["title"],
        data.get("source") or "unknown",
        data.get("date"),
        data.get("topic") or "unknown",
        data.get("summary") or "",
        data.get("claims") or "",
        data.get("evidence_level") or "unknown",
        data.get("trial_phase") or "unknown",
        data.get("patient_count"),
        data.get("result_strength") or "unknown",
        data.get("safety_notes") or "",
        data.get("hype_risk") or "medium",
        data.get("practical_relevance") or "",
        str(data["url"]) if data.get("url") else None,
        1 if data.get("needs_verification") else 0,
        data.get("watchlist_matches") or "",
        data.get("created_at") or now_iso(),
    )


def evaluate_text(payload: EvaluationInput) -> EvaluationOut:
    text = " ".join([payload.title, payload.source, payload.summary, payload.claims, payload.url or ""])
    normalized = text.lower()
    rationale: list[str] = []

    evidence_level: EvidenceLevel = "unknown"
    if has_any(normalized, ["press release", "announces", "company announced", "pipeline update"]):
        evidence_level = "press_release"
        rationale.append("Looks like a company announcement or press release.")
    if has_any(normalized, ["cell", "in vitro", "organoid", "cell culture"]):
        evidence_level = "cell_study"
        rationale.append("Mentions cells, organoids, or in vitro work.")
    if has_any(normalized, ["mouse", "mice", "rat", "animal model", "preclinical"]):
        evidence_level = "animal_study"
        rationale.append("Mentions animal or preclinical data.")
    if has_any(normalized, ["human", "patients", "volunteers", "clinical trial", "randomized", "placebo"]):
        evidence_level = "human_trial"
        rationale.append("Mentions human participants or clinical trial language.")

    trial_phase = detect_trial_phase(normalized)
    if trial_phase != "unknown":
        rationale.append(f"Detected {trial_phase.replace('_', ' ')} language.")

    patient_count = detect_patient_count(normalized)
    if patient_count is not None:
        rationale.append(f"Detected patient/participant count around {patient_count}.")

    has_trial_id = bool(re.search(r"\b(nct\d{8}|jprn|eudract|isrctn)\b", normalized))
    has_article_signal = has_any(normalized, ["doi", "journal", "published", "pubmed", "nejm", "nature", "science", "cell"])
    has_effect_signal = has_any(normalized, ["improved", "reduced", "increased", "survival", "response rate", "remission", "clinical effect"])
    has_safety_signal = has_any(normalized, ["adverse event", "side effect", "safety", "tolerated", "toxicity"])

    if evidence_level == "human_trial" and has_effect_signal:
        result_strength = "clinical signal reported"
        practical_relevance = "Potentially relevant, but verify endpoints, comparator, and durability."
    elif evidence_level in {"animal_study", "cell_study"}:
        result_strength = "early-stage biological signal"
        practical_relevance = "Research-stage only; not directly actionable for patients."
    elif evidence_level == "press_release":
        result_strength = "company-reported claim"
        practical_relevance = "Track for paper, registry entry, or independent validation."
    else:
        result_strength = "unclear"
        practical_relevance = "Needs more source detail before prioritizing."

    if has_safety_signal:
        safety_notes = "Safety is mentioned; inspect adverse events and discontinuations."
    elif evidence_level == "human_trial":
        safety_notes = "Human data found, but safety details are not clear in the provided text."
    else:
        safety_notes = "No clear safety data in the provided text."

    needs_verification = not (has_trial_id or has_article_signal)
    if needs_verification:
        rationale.append("No obvious trial id, DOI, PubMed, or journal signal found.")

    if evidence_level == "human_trial" and has_effect_signal and not needs_verification:
        hype_risk: HypeRisk = "low"
    elif evidence_level in {"animal_study", "cell_study"}:
        hype_risk = "medium"
    elif evidence_level == "press_release" or needs_verification:
        hype_risk = "high"
    else:
        hype_risk = "medium"

    return EvaluationOut(
        evidence_level=evidence_level,
        trial_phase=trial_phase,
        patient_count=patient_count,
        result_strength=result_strength,
        safety_notes=safety_notes,
        hype_risk=hype_risk,
        practical_relevance=practical_relevance,
        needs_verification=needs_verification,
        rationale=rationale or ["Insufficient detail for a confident automated evaluation."],
    )


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def detect_trial_phase(text: str) -> TrialPhase:
    if has_any(text, ["approved", "fda approval", "ema approval", "approved therapy"]):
        return "approved"
    if re.search(r"\bphase\s*3\b|\bphase iii\b", text):
        return "phase_3"
    if re.search(r"\bphase\s*2\b|\bphase ii\b", text):
        return "phase_2"
    if re.search(r"\bphase\s*1\b|\bphase i\b", text):
        return "phase_1"
    if has_any(text, ["preclinical", "animal", "mouse", "mice", "in vitro", "cell culture"]):
        return "not_applicable"
    return "unknown"


def detect_patient_count(text: str) -> int | None:
    patterns = [
        r"\b(\d{1,6})\s+(?:patients|participants|volunteers|subjects)\b",
        r"\bn\s*=\s*(\d{1,6})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None
