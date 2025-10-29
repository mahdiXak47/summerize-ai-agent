import logging
from typing import Tuple

from openai import OpenAI

from app.config import get_settings


_logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """
the form of this gpt behavior is it will get an input of json with flags that enable a part of this json or disable it and some rules are mentiond in it 

consider that the form of json is like this

{
  "ticket_title": "string",
  "ticket_priority": "normal | high | critical",
  "ticket_status":"resolved | closed | open | samurai workflow | camedus workflow | lamallus workflow | gow workflow | gherghi workflow | marketplace workflow | financial workflow",
  "ticket_labels": [
    "string"
  ],
  "ticket_description": "Text reported by customer",
  "comments": [
    {
      "sender": "customer",
      "type": "text | attachment",
      "content": "string or file reference"
    },
    {
      "sender": "technical_support",
      "type": "text | attachment",
      "visibility": "internal | public",
      "content": "string or file reference"
    }
  ]
}


based on that i will send a content of a ticket and ask from the agent some questions

also consider all the answers most be based on persian language 

do not send the ticket number , title , priority , status and labes just know them it might be usable for analysing the ticket but no need to send it in output 

the output structure is good to be like this : 

ticket problem : 
process of troubleshooting the ticket : 
final result :

consider that when you are mention some crew of the company that says something or do something just say the name of the crew not its position 
just say مهدی اکبری do this or says that instead of telling مهدی اکبری کارشناس پشتیبانی does this or says that 

and here is a detail of the company users with theri teams : 

مهدی اکبری, مهرشاد دهقانی , محسن کربلائی امینی, فاطمه حمدی, پارسا حاجی قاسمی are technical support 
محمد امین بخشی is technical financial support 
هادی زمانی , سهند اسماعیل‌زاده, محمدمهدی واحدی are dbass service support 

also consider that there is not need to tell the exact details just the important things and explaining a bit the process of ticket troubleshoot will be ok

"""

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

    if not settings.openrouter_api_key:
        _logger.error("OPENROUTER_API_KEY is missing.")
        raise RuntimeError("OpenRouter API key not configured.")

    user_content = "تیکت:\n<JSON>\n" + ticket_json_str + "\n</JSON>"

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
        client = client.with_options(timeout=settings.request_timeout_seconds)

        extra_headers = {}
        if settings.openrouter_site_url:
            extra_headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_site_name:
            extra_headers["X-Title"] = settings.openrouter_site_name

        completion = client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=600,
            extra_headers=extra_headers or None,
        )

        try:
            text = completion.choices[0].message.content or ""
        except Exception:  # noqa: BLE001
            text = ""
    except Exception as exc:  # noqa: BLE001
        _logger.exception("LLM request failed: %s", exc)
        raise

    if not text:
        _logger.warning("Empty response from model.")
        return "", "", ""

    return _parse_three_sections(text)
