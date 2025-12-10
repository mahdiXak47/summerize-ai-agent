import json
import logging
from typing import Any, Dict
import re

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import IncomingTicket, MarkdownResponse
from app.services.summarizer import summarize_ticket


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

app = FastAPI(title="Ticket Summarizer Webhook")


def remove_illegal_json_ctrl_str(s: str) -> str:
    # Remove ASCII control characters except for whitespace (tab, newline, carriage return, and space)
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', s)


@app.get("/healthz")
def healthz(deep: int = Query(default=0)) -> JSONResponse:
    """Readiness probe endpoint."""
    settings = get_settings()
    checks: Dict[str, Any] = {}

    checks["provider"] = "openrouter"
    checks["env_api_key"] = bool(settings.openrouter_api_key)
    checks["model_configured"] = bool(settings.openrouter_model)

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


@app.post("/webhook/ticket", response_model=MarkdownResponse)
async def webhook_ticket(request: Request) -> MarkdownResponse:
    """Receive a ticket payload, log headers/body, summarize, and return JSON."""
    try:
        headers_dict = dict(request.headers)
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8", errors="replace")
        _logger.info("/webhook/ticket headers: %s", headers_dict)
        _logger.info("/webhook/ticket body: %s", body_text)

        # Diagnostic logs
        # _logger.info("RAW BODY BYTES repr: %r", body_bytes)
        # _logger.info("DECODED BODY TEXT repr: %r", body_text)

        clean_body_text = remove_illegal_json_ctrl_str(body_text)
        _logger.info("CLEANED BODY TEXT repr: %r", clean_body_text)
        clean_body_text_no_newlines = clean_body_text.replace('\n', '')
        incoming_ticket = IncomingTicket.model_validate_json(clean_body_text_no_newlines)
        # Map incoming fields to the summarizer ticket format
        mapped_ticket = {
            "ticket_title": incoming_ticket.summary,
            "ticket_priority": "normal",  # Not provided, use default
            "ticket_status": "open",      # Not provided, use default
            "ticket_labels": [],           # Not provided, use default
            "ticket_description": incoming_ticket.description,
            "comments": [
                {
                    "sender": c.author,
                    "type": "text",  # No type field in Jira; default to text
                    "content": c.body
                } for c in incoming_ticket.comments
            ]
        }
        ticket_json_str = json.dumps(mapped_ticket, ensure_ascii=False, indent=2)
        problem, resolution_summary, result_and_key_points = summarize_ticket(ticket_json_str)
    except Exception as exc:
        _logger.exception("Summarization failed: %s", exc)
        # Try manual json parsing to show line/col error diagnostics
        try:
            json.loads(clean_body_text)
        except json.JSONDecodeError as json_exc:
            line = json_exc.lineno
            col = json_exc.colno
            err_msg = json_exc.msg
            lines = clean_body_text.splitlines()
            bad_line = lines[line-1] if 0 < line <= len(lines) else ''
            pointer = ' ' * (col-1) + '^'
            char = ''
            if 0 < col <= len(bad_line):
                suspect = bad_line[col-1]
                # if printable, show as is; else show unicode escape
                char = f"Offending char: {repr(suspect)} / U+{ord(suspect):04X}"
            else:
                char = "Could not locate character."
            _logger.error(f"Invalid JSON: {err_msg} at line {line}, column {col}\n>> {bad_line}\n   {pointer}\n   {char}")
        except Exception as unknown_json:
            _logger.error(f"Unknown error parsing JSON: {unknown_json}")
        raise HTTPException(status_code=400, detail="Invalid JSON body (see server log for pinpointed error)") from exc

    # Combine the outputs into a markdown string as per new requirement
    markdown_response = (
        f"**مسئله:** {problem.strip()}\n\n"
        f"**فرایند رسیدگی:** {resolution_summary.strip()}\n\n"
        f"**نتیجه بررسی:** {result_and_key_points.strip()}"
    )

    return {"content": markdown_response}
