import json
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import SummaryResponse, Ticket
from app.services.summarizer import summarize_ticket


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

app = FastAPI(title="Ticket Summarizer Webhook")


@app.get("/healthz")
def healthz(deep: int = Query(default=0)) -> JSONResponse:
    """Readiness probe endpoint."""
    settings = get_settings()
    checks: Dict[str, Any] = {}

    checks["env_openai_api_key"] = bool(settings.openai_api_key)
    checks["model_configured"] = bool(settings.openai_model)

    status = "ok" if all(checks.values()) else "unhealthy"
    ready = status == "ok"

    # Optional deep check.
    if deep:
        # Best-effort: try very cheap call shape to validate auth/connectivity.
        try:
            # We avoid real model calls to keep it light; we just verify key presence here.
            # If a real deep check is needed, we can add a tiny call in the future.
            checks["deep_check"] = "skipped"
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Deep check failed: %s", exc)
            checks["deep_check"] = "failed"
            status = "degraded"
            ready = False

    body = {"status": status, "ready": ready, "checks": checks}
    http_code = 200 if ready else 503
    return JSONResponse(content=body, status_code=http_code)


@app.post("/webhook/ticket", response_model=SummaryResponse)
def webhook_ticket(ticket: Ticket) -> SummaryResponse:
    """Receive a ticket payload, summarize via OpenAI, print and return JSON."""
    try:
        ticket_json_str = json.dumps(ticket.model_dump(), ensure_ascii=False, indent=2)
        problem, resolution_summary, result_and_key_points = summarize_ticket(ticket_json_str)
    except Exception as exc:  # noqa: BLE001
        _logger.exception("Summarization failed: %s", exc)
        raise HTTPException(status_code=503, detail="Summarization service unavailable.") from exc

    combined_for_print = (
        "مسئله:\n" + problem.strip() + "\n\n"
        "روند حل به‌صورت خلاصه:\n" + resolution_summary.strip() + "\n\n"
        "نتیجه و نکات کلیدی:\n" + result_and_key_points.strip()
    )
    print(combined_for_print)

    return SummaryResponse(
        problem=problem.strip(),
        resolution_summary=resolution_summary.strip(),
        result_and_key_points=result_and_key_points.strip(),
    )
