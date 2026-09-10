"""PII redaction for stored text (skills.md section 36).

Applied to text that gets persisted in the report (account names, OCR
text) - never to the text used for keyword matching, so redaction can
never hide a legitimate match. Disabled by default per field; the
operator opts in via config/config.yaml `privacy.redact_email` /
`redact_phone`.
"""

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\w)(\+?[\d][\d\-\s]{7,14}\d)(?!\w)")

EMAIL_PLACEHOLDER = "[REDACTED_EMAIL]"
PHONE_PLACEHOLDER = "[REDACTED_PHONE]"


def redact_emails(text: str) -> str:
    if not text:
        return text
    return EMAIL_RE.sub(EMAIL_PLACEHOLDER, text)


def redact_phones(text: str) -> str:
    if not text:
        return text

    def _replace(match: "re.Match") -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) < 8:
            return match.group(0)
        return PHONE_PLACEHOLDER

    return PHONE_RE.sub(_replace, text)


def redact_text(text: str, config: dict = None) -> str:
    """Applies configured redaction rules to a single string."""
    if not text or not config:
        return text
    if not config.get("redact_sensitive_data", True):
        return text
    if config.get("redact_email"):
        text = redact_emails(text)
    if config.get("redact_phone"):
        text = redact_phones(text)
    return text


def redact_list(items: list, config: dict = None) -> list:
    """Applies configured redaction rules to every string in a list."""
    return [redact_text(item, config) for item in items]
