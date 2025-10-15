## Ticket Summarizer Webhook (Python + FastAPI)

A tiny HTTP service that receives a technical ticket (JSON), builds a static+dynamic prompt, calls OpenAI to generate a concise Persian summary, prints it to stdout, and returns it in the HTTP response.

## What it does
- Accepts a ticket JSON at `POST /webhook/ticket`.
- Sends the ticket to OpenAI with a static instruction (role/format) + your ticket as dynamic content.
- Returns a 3-part Persian summary:
  - مسئله
  - روند حل به‌صورت خلاصه
  - نتیجه و نکات کلیدی
- Readiness probe at `GET /healthz` for container orchestrators.

## Agent (model) information
- Uses OpenAI model `gpt-4.1` by default.
- Configurable via env var `OPENAI_MODEL`.
- OpenAI Python SDK v1 (`openai` package) is used.

## Run locally
```bash
# From project root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY='YOUR_OPENAI_KEY'
export OPENAI_MODEL='gpt-4.1'  # optional, defaults to gpt-4.1

uvicorn app.main:app --reload --port 8000
```

## Docker
```bash
# Build
docker build -t summerize-ai-agent:latest .

# Run
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY='YOUR_OPENAI_KEY' \
  -e OPENAI_MODEL='gpt-4.1' \
  summerize-ai-agent:latest
```

## Endpoints

### Readiness
- `GET /healthz`
- Returns JSON: `{ "status": "ok|unhealthy|degraded", "ready": bool, "checks": { ... } }`.
- HTTP 200 if ready, 503 otherwise.
- Optional: `GET /healthz?deep=1` reserved for future deeper checks.

### Summarize ticket
- `POST /webhook/ticket`
- Content-Type: `application/json`
- Response JSON:
```json
{
  "problem": "...",
  "resolution_summary": "...",
  "result_and_key_points": "..."
}
```

## Input JSON schema (example)
```json
{
  "ticket_number": 21054,
  "ticket_title": "عنوان تیکت",
  "ticket_priority": "normal",
  "ticket_labels": ["label1", "label2"],
  "ticket_status": "open",
  "ticket_description": "توضیحات تیکت...",
  "comments": [
    {
      "sender": "technical_support",
      "name": "اختیاری",
      "type": "text",
      "visibility": "public",
      "content": "..."
    }
  ]
}
```

## Example request
```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/ticket \
  -H 'Content-Type: application/json' \
  --data @ticket.json | jq
```

## Prompt rules (roles/conditions)
- خروجی فقط فارسی باشد و اصطلاحات کاملاً فنی انگلیسی حفظ شوند.
- دقیقاً سه بخش کوتاه تولید شود: مسئله، روند حل به‌صورت خلاصه، نتیجه و نکات کلیدی.
- از حدس‌زدن خودداری شود و فقط بر اساس محتوای تیکت نتیجه گرفته شود.

## Port
- Service listens on port `8000`.

## Notes
- You must set `OPENAI_API_KEY` at runtime.
- Handle billing/quota on your OpenAI account; 429 insufficient_quota will return HTTP 503 from the webhook.
- Do not commit secrets.
