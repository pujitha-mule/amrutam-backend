# Operations, Observability, CI, and Demo Runbook

## 1. Health checks

When the application is running, check the actual configured endpoints (commonly `/health`, `/health/ready`, and `/metrics`). A liveness check should answer whether the process is alive. A readiness check should indicate whether the instance can safely serve requests, including required dependency checks.

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:8000/health/ready
Invoke-WebRequest http://127.0.0.1:8000/metrics
```

If your local server is on another port, change the URL. Do not expose internal health details publicly.

## 2. Metrics, logs, and traces

### Metrics to collect
- Request count, status code, and latency histogram by route template/method (avoid raw IDs as labels).
- Error rate and 4xx/5xx breakdown.
- DB pool utilization, wait time, query latency, and connection errors.
- Booking conflicts, idempotency hits/replays, and state-transition failures.
- Redis availability/cache hit rate if used.
- Worker queue depth/age and retry/dead-letter counts if async workers are deployed.

### Logs
Use structured JSON logs with timestamp, severity, service/version, request ID, route template, status, and duration. Redact authorization headers, passwords, tokens, payment secrets, and clinical payloads. Restrict log access and retention.

### Distributed tracing
Use OpenTelemetry-compatible instrumentation at ingress, database calls, and outbound integrations in a production deployment if tracing is not already wired into this repository. Propagate trace context, sample appropriately, and never attach clinical payloads or secrets to spans.

### Alerting and SLOs
Recommended initial alerts:
- sustained elevated 5xx/error rate;
- p95 latency above the target for a defined window;
- readiness failures or repeated DB connection failures;
- booking conflict spike or idempotency anomalies;
- queue lag/retry/dead-letter growth;
- backup failure and failed restore drill.

The assignment target is 99.95% availability. Define the measurement window, exclusions, and error-budget policy before reporting SLO compliance.

## 3. CI and release workflow

1. Open a pull request.
2. CI installs dependencies and runs automated checks from `.github/workflows/ci.yml`.
3. Review test results and dependency scan findings.
4. Build the container image and scan it before release.
5. Deploy to staging using environment-managed secrets.
6. Apply reviewed migrations; run smoke tests and health checks.
7. Promote to production with a rollback/roll-forward plan and observe error rate and latency.

The existing GitHub Actions workflow is the CI baseline. A production pipeline should add dependency scanning, container scanning, artifact provenance, deployment approvals, and staging smoke tests if not already present.

## 4. Backup and disaster recovery runbook

- Configure encrypted automated PostgreSQL backups and point-in-time recovery.
- Restrict backup access separately from application credentials.
- Define RPO/RTO with stakeholders; example initial proposal: RPO <= 5 minutes, RTO <= 60 minutes.
- Perform scheduled restore drills into an isolated environment.
- Validate row counts, constraints, migrations, and application smoke tests after restore.
- Document primary failover, regional recovery, DNS cutover, and reconciliation of external payment/notification events.
- Do not claim recoverability until a restore has been successfully tested.

## 5. Five-minute demo outline

Use synthetic accounts/data only and avoid showing secrets in terminal history.

- **0:00–0:30 — Overview:** repository, architecture diagram, stack (FastAPI, PostgreSQL, SQLAlchemy, Alembic, Docker, CI).
- **0:30–1:00 — Docs and health:** show `/docs`, `/openapi.json`, health/readiness and metrics endpoints.
- **1:00–2:00 — Auth and discovery:** authenticate patient/doctor; show doctor/availability discovery if available.
- **2:00–3:00 — Booking reliability:** book a slot; repeat the same request with the same idempotency key and show the stable result; explain concurrency protection.
- **3:00–4:00 — Consultation and prescription:** demonstrate permitted state transitions, issue a prescription after completion, fetch by ID, and show the patient's prescription list.
- **4:00–4:30 — Tests and CI:** run `python -m pytest -q`; show GitHub Actions result.
- **4:30–5:00 — Observability/security/limitations:** show metrics and docs, explain audit trail and security controls, and be transparent about production gates (load testing, HA deployment, tracing/alerts, backup restore evidence).

## 6. Troubleshooting

- **Database connection fails:** verify PostgreSQL is running, database/role exist, `.env` URL is correct, and credentials are URL-encoded where needed.
- **Migration fails:** inspect the migration and current schema; run `alembic current`; do not delete the database as a first response.
- **Port is busy:** identify the process listening on the port or choose a different port; do not start multiple servers on the same port.
- **401/403:** obtain a fresh token, confirm the role and resource ownership, and inspect server logs without exposing the token.
- **500 error:** capture the fresh traceback from the active server process; stale log files may not represent the latest request.
- **CI failure:** reproduce the failing command locally in the same Python version and inspect the full workflow output.
