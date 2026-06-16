# Medical Radar

Personal medical news and research radar for tracking topics, saving signals, and separating clinical evidence from hype.

## What It Does

- Stores medical monitoring topics and keywords.
- Stores news/research items with evidence fields.
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
docker compose up -d --build
```

Open:

- HTML dashboard: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs
- Healthcheck: http://127.0.0.1:8000/health

Data is stored in a Docker volume named `news_medical-radar-data`.

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
- `GET /news`
- `POST /news`
- `GET /news/{news_id}`
- `PATCH /news/{news_id}`
- `DELETE /news/{news_id}`
- `POST /news/evaluate`
- `POST /news/{news_id}/evaluate`
- `GET /health`

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
