import json
import logging

from app.core.logging import (
    JsonFormatter,
    _redact,
    configure_logging,
)


def test_redact_sensitive_keys():
    result = _redact({
        "password": "secret",
        "email": "user@example.com",
        "name": "Test User",
    })

    assert result["password"] == "***"
    assert result["email"] == "***"
    assert result["name"] == "Test User"


def test_redact_nested_dicts_and_lists():
    result = _redact({
        "profile": {
            "phone": "1234567890",
            "city": "Hyderabad",
        },
        "items": [{"token": "abc"}, {"value": "safe"}],
    })

    assert result["profile"]["phone"] == "***"
    assert result["profile"]["city"] == "Hyderabad"
    assert result["items"][0]["token"] == "***"
    assert result["items"][1]["value"] == "safe"


def test_redact_is_case_insensitive():
    assert _redact({"PASSWORD": "secret"})["PASSWORD"] == "***"


def test_json_formatter_formats_message_and_extra_fields():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="User registered",
        args=(),
        exc_info=None,
    )
    record.email = "user@example.com"
    record.request_id = "req-123"

    result = json.loads(JsonFormatter().format(record))

    assert result["level"] == "INFO"
    assert result["logger"] == "test_logger"
    assert result["msg"] == "User registered"
    assert result["email"] == "user@example.com"
    assert result["request_id"] == "req-123"
    assert "ts" in result


def test_json_formatter_includes_exception():
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=20,
        msg="Operation failed",
        args=(),
        exc_info=exc_info,
    )

    result = json.loads(JsonFormatter().format(record))

    assert "exc" in result
    assert "ValueError: test error" in result["exc"]


def test_configure_logging_sets_json_formatter():
    configure_logging()

    root = logging.getLogger()

    assert root.level == logging.INFO
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)
