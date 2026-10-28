import json
import logging
import sys
from datetime import UTC, datetime

REDACT_KEYS = {
    "password",
    "totp_code",
    "mfa_secret",
    "authorization",
    "cookie",
    "refresh_token",
    "token",
    "email",
    "phone",
    "medication",
    "instructions",
}


def _redact(obj):
    if isinstance(obj, dict):
        return {k: ("***" if k.lower() in REDACT_KEYS else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


class JsonFormatter(logging.Formatter):
    def format(self, record):
        out = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k in (
                "msg",
                "args",
                "levelname",
                "name",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            ):
                continue
            out[k] = _redact(v)
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
