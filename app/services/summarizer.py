import logging
from typing import Tuple

from openai import OpenAI

from app.config import get_settings


_logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "شما یک دستیار فنی هستید که باید یک تیکت فنی را خلاصه کنید. خروجی فقط فارسی باشد، "
    "اصطلاحات کاملاً فنی انگلیسی را به همان صورت نگه دارید. خروجی دقیقاً سه بخش کوتاه داشته باشد و چیزی اضافه نشود:\n"
    "1) «مسئله»\n2) «روند حل به‌صورت خلاصه»\n3) «نتیجه و نکات کلیدی»\n"
    "از حدس‌زدن خودداری کنید و فقط بر اساس محتوای تیکت نتیجه بگیرید."
)


def _build_input(ticket_json_str: str) -> str:
    """Build the single input string concatenating system rules and dynamic content."""
    return (
        _SYSTEM_PROMPT
        + "\n\n"
        + "تیکت:\n<JSON>\n"
        + ticket_json_str
        + "\n</JSON>"
    )


def _parse_three_sections(text: str) -> Tuple[str, str, str]:
    """Parse the model output into three sections using simple heuristics."""
    normalized = text.replace("\r", "").strip()

    # Try split by numbered lines.
    parts = []
    current = []
    for line in normalized.split("\n"):
        if line.strip().startswith("1") and ("مسئله" in line or ")" in line or "." in line):
            if current:
                parts.append("\n".join(current).strip())
                current = []
            current.append(line)
        elif line.strip().startswith("2") and ("روند" in line or ")" in line or "." in line):
            if current:
                parts.append("\n".join(current).strip())
                current = []
            current.append(line)
        elif line.strip().startswith("3") and ("نتیجه" in line or ")" in line or "." in line):
            if current:
                parts.append("\n".join(current).strip())
                current = []
            current.append(line)
        else:
            current.append(line)
    if current:
        parts.append("\n".join(current).strip())

    if len(parts) >= 3:
        section1 = parts[0].strip()
        section2 = parts[1].strip()
        section3 = parts[2].strip()
        return section1, section2, section3

    # Fallback: split by headings keywords.
    keywords = ["مسئله", "روند", "نتیجه"]
    found = []
    last_index = 0
    for kw in keywords:
        idx = normalized.find(kw, last_index)
        if idx != -1:
            found.append(idx)
            last_index = idx + len(kw)
    if found:
        segments = []
        for i, start in enumerate(found):
            end = found[i + 1] if i + 1 < len(found) else len(normalized)
            segments.append(normalized[start:end].strip())
        while len(segments) < 3:
            segments.append("")
        return segments[0], segments[1], segments[2]

    # Last resort: put all text in the first section.
    return normalized, "", ""


def summarize_ticket(ticket_json_str: str) -> Tuple[str, str, str]:
    """Summarize the ticket content and return three Persian sections."""
    settings = get_settings()
    if not settings.openai_api_key:
        _logger.error("OPENAI_API_KEY is missing.")
        raise RuntimeError("OpenAI API key not configured.")

    client = OpenAI(api_key=settings.openai_api_key)
    client = client.with_options(timeout=settings.request_timeout_seconds)

    user_input = _build_input(ticket_json_str)

    try:
        resp = client.responses.create(
            model=settings.openai_model,
            input=user_input,
            temperature=0.2,
            max_output_tokens=600,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.exception("OpenAI request failed: %s", exc)
        raise

    try:
        text = resp.output_text  # SDK v1 convenience accessor.
    except Exception:  # noqa: BLE001
        # Structured fallback.
        try:
            first = resp.output[0]
            text = getattr(first, "content", "") or ""
        except Exception:  # noqa: BLE001
            text = ""

    if not text:
        _logger.warning("Empty response from model.")
        return "", "", ""

    return _parse_three_sections(text)
