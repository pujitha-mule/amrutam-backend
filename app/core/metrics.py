from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "http_requests_total", "Requests",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds", "Latency",
    ["method", "route"],
    buckets=[0.05, 0.1, 0.2, 0.5, 1, 2, 5],
)
IDEMPOTENT_REPLAYS = Counter(
    "idempotency_replays_total", "Idempotency replays", ["route"],
)
BOOKING_CONFLICTS = Counter(
    "booking_conflicts_total", "Slot booking conflicts", ["reason"],
)
OUTBOX_PENDING = Gauge("outbox_pending_events", "Pending outbox rows")
