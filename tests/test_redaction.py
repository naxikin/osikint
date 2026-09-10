"""Unit tests: PII redaction (skills.md section 36)."""

from utils.redaction import redact_emails, redact_list, redact_phones, redact_text


def test_redact_emails_replaces_match():
    text = "contact me at jane.doe@example.com please"
    assert redact_emails(text) == "contact me at [REDACTED_EMAIL] please"


def test_redact_emails_no_match():
    assert redact_emails("no email here") == "no email here"


def test_redact_emails_empty():
    assert redact_emails("") == ""
    assert redact_emails(None) is None


def test_redact_phones_replaces_long_digit_run():
    text = "call +62 812-3456-7890 now"
    assert redact_phones(text) == "call [REDACTED_PHONE] now"


def test_redact_phones_ignores_short_numbers():
    assert redact_phones("room 42 floor 3") == "room 42 floor 3"


def test_redact_text_master_switch_off():
    config = {
        "redact_sensitive_data": False,
        "redact_email": True,
        "redact_phone": True,
    }
    text = "a@b.com and 081234567890"
    assert redact_text(text, config) == text


def test_redact_text_email_flag_only():
    config = {
        "redact_sensitive_data": True,
        "redact_email": True,
        "redact_phone": False,
    }
    text = "a@b.com and 081234567890"
    result = redact_text(text, config)
    assert "[REDACTED_EMAIL]" in result
    assert "081234567890" in result


def test_redact_text_both_flags():
    config = {
        "redact_sensitive_data": True,
        "redact_email": True,
        "redact_phone": True,
    }
    text = "a@b.com and 081234567890"
    result = redact_text(text, config)
    assert "[REDACTED_EMAIL]" in result
    assert "[REDACTED_PHONE]" in result


def test_redact_text_no_config_is_noop():
    assert redact_text("a@b.com", None) == "a@b.com"
    assert redact_text("a@b.com", {}) == "a@b.com"


def test_redact_list_applies_to_each_item():
    config = {"redact_sensitive_data": True, "redact_email": True}
    result = redact_list(["a@b.com", "no email"], config)
    assert result == ["[REDACTED_EMAIL]", "no email"]
