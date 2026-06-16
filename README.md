# Medical Radar

Personal medical news and research radar for tracking topics, saving signals, and separating clinical evidence from hype.

## What It Does

- Stores medical monitoring topics and keywords.
- Stores news/research items with evidence fields.
- Collects candidates from PubMed and Google News RSS searches.
- Deduplicates news by URL.
- Keeps a watchlist of exact people, companies, drugs, targets, and trial IDs.
- Publishes to Telegram only when an item matches the watchlist by default.
- Runs an optional background scheduler in Docker.
- Publishes pending items to Telegram, with dry-run mode enabled by default.
- Provides CRUD endpoints for topics and news.
- Evaluates a news item into:
  - `evidence_level`
  - `trial_phase`
  - `patient_count`
  - `result_strength`
  - `safety_notes`
  - `hype_risk`
  - `practical_relevance`
  - `needs_verification`
- Includes a simple HTML dashboard at `/`.

This MVP does not give medical advice. It is for analytics and monitoring only.

## Run

### Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Open:

- HTML dashboard: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs
- Healthcheck: http://127.0.0.1:8000/health

Data is stored in a Docker volume named `news_medical-radar-data`.

By default, Telegram is in dry-run mode. Edit `.env` when you are ready to send real posts:

```env
TELEGRAM_DRY_RUN=false
TELEGRAM_BOT_TOKEN=123456:your_bot_token
TELEGRAM_CHAT_ID=@your_channel_username
```

Add the bot as an administrator in the Telegram channel before disabling dry-run.

Useful commands:

```bash
docker compose ps
docker compose logs -f
docker compose stop
```

### Local Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- HTML dashboard: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs

## Example: Add News

```bash
curl -X POST http://127.0.0.1:8000/news ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"Phase 2 trial reports retinal therapy signal\",\"source\":\"Example Journal\",\"date\":\"2026-06-16\",\"topic\":\"Восстановление зрения\",\"summary\":\"A phase 2 study in humans reported visual acuity improvement in 72 patients.\",\"claims\":\"Human phase 2 trial with measurable clinical improvement and safety monitoring.\",\"url\":\"https://example.com\"}"
```

## Main Endpoints

- `GET /topics`
- `POST /topics`
- `PATCH /topics/{topic_id}`
- `DELETE /topics/{topic_id}`
- `GET /watchlist`
- `POST /watchlist`
- `PATCH /watchlist/{item_id}`
- `DELETE /watchlist/{item_id}`
- `GET /news`
- `POST /news`
- `GET /news/{news_id}`
- `PATCH /news/{news_id}`
- `DELETE /news/{news_id}`
- `POST /news/evaluate`
- `POST /news/{news_id}/evaluate`
- `POST /collect/run`
- `POST /telegram/publish-pending`
- `GET /scheduler`
- `GET /health`

## Manual Collection

Run one collection pass:

```bash
curl -X POST "http://127.0.0.1:8000/collect/run?limit_per_topic=3"
```

Publish pending items. In dry-run mode this marks them as published without sending to Telegram:

```bash
curl -X POST "http://127.0.0.1:8000/telegram/publish-pending?limit=10"
```

Check scheduler status:

```bash
curl http://127.0.0.1:8000/scheduler
```

## Watchlist

The channel is designed to stay quiet unless a story matches a watchlist item.

Initial watchlist:

- David Sinclair: aging, epigenetics, partial reprogramming, Life Biosciences.
- Professor Harrington: oncology, immunotherapy, oncolytic viruses.

Add a new interest:

```bash
curl -X POST http://127.0.0.1:8000/watchlist \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Toregem Biopharma",
    "topic": "Регенерация зубов",
    "keywords": ["Toregem Biopharma", "USAG-1 antibody", "tooth regrowth Japan"],
    "notes": "Tooth regeneration watch item"
  }'
```

List active interests:

```bash
curl "http://127.0.0.1:8000/watchlist?active=true"
```

## Scheduler

The Docker setup enables the background scheduler by default:

```env
MEDICAL_RADAR_ENABLE_SCHEDULER=true
MEDICAL_RADAR_POLL_MINUTES=180
MEDICAL_RADAR_COLLECT_LIMIT_PER_TOPIC=5
MEDICAL_RADAR_COLLECT_BROAD_TOPICS=false
MEDICAL_RADAR_MIN_PUBLISH_MODE=skip_high_hype
MEDICAL_RADAR_PUBLISH_REQUIRE_WATCHLIST=true
```

Publish modes:

- `all`: publish everything.
- `skip_high_hype`: skip high hype-risk items.
- `high_priority`: publish human trials and low hype-risk items only.

## Initial Topics

The app seeds the database with:

- Longevity / омоложение
- Восстановление зрения
- Регенерация зубов
- Витилиго
- Рак / онкология
- Ozempic / ожирение / мышцы
- HIV / иммунитет
- AI в медицине

The SQLite database is created automatically at `medical_radar.db` locally, or `/data/medical_radar.db` inside Docker.
