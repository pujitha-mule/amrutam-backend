# Amrutam — Telemedicine Backend

A modular REST API backend for a telemedicine platform, built with **Python, FastAPI, PostgreSQL, SQLAlchemy, and Docker**. The system supports authentication, doctor availability, consultation booking, consultation lifecycle management, prescriptions, audit logging, and observability.

## Features

- **Authentication and authorization:** User login and role-based access control.
- **Doctor discovery:** Doctor profiles and availability management.
- **Consultation booking:** Booking workflows with idempotency support.
- **Consultation lifecycle:** Controlled consultation state transitions.
- **Prescriptions:** Doctor-issued prescriptions and patient prescription history.
- **Database management:** PostgreSQL with asynchronous SQLAlchemy and Alembic migrations.
- **Audit logging:** Records important application actions.
- **Observability:** Health checks, application logging, and metrics endpoint.
- **Containerization:** Dockerfile and Docker Compose configuration.
- **Automated testing:** Pytest-based unit and integration tests.
- **Continuous integration:** GitHub Actions workflow.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python |
| API framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy (async) |
| Migrations | Alembic |
| Validation | Pydantic |
| Cache / supporting services | Redis (configured where applicable) |
| Testing | Pytest |
| Containerization | Docker, Docker Compose |
| CI/CD | GitHub Actions |

## Architecture

The application follows a modular architecture that separates API routes, business logic, database models, schemas, and infrastructure concerns.

```text
amrutam-backend/
├── .github/
│   └── workflows/
│       └── ci.yml
├── app/
│   ├── api/
│   │   └── v1/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── workers/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   └── OPERATIONS.md
├── migrations/
├── tests/
├── Dockerfile
├── compose.yaml
├── alembic.ini
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11
- PostgreSQL 16 or a compatible version
- Redis, if required by the configured services
- Git
- Docker Desktop (optional)

### 1. Clone the repository

```bash
git clone https://github.com/pujitha-mule/amrutam-backend.git
cd amrutam-backend
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your local database credentials and strong, unique development secrets.

Example configuration:

```env
DATABASE_URL=postgresql+asyncpg://amrutam:amrutam@localhost:5432/amrutam
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=replace-with-a-random-secret
JWT_REFRESH_SECRET=replace-with-a-different-random-secret
MFA_ENCRYPTION_KEY=replace-with-a-valid-encryption-key
PAYMENT_WEBHOOK_SECRET=replace-with-a-random-webhook-secret
ENV=dev
```

These values are examples for local development only. Never use them as production credentials or commit your `.env` file.

### 5. Run database migrations

Ensure PostgreSQL is running and the configured database exists.

```powershell
alembic upgrade head
```

### 6. Start the API server

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## API Documentation

Once the server is running, access the automatically generated API documentation.

| Resource | URL |
|---|---|
| Swagger UI | http://127.0.0.1:8000/docs |
| OpenAPI schema | http://127.0.0.1:8000/openapi.json |
| Health check | http://127.0.0.1:8000/health |
| Readiness check | http://127.0.0.1:8000/health/ready |
| Metrics | http://127.0.0.1:8000/metrics |

Confirm the health-check paths against the routes registered in the running application.

## Running with Docker

Review `compose.yaml` and configure the required environment variables before starting the services.

```powershell
docker compose up --build
```

To stop the services:

```powershell
docker compose down
```

## Running Tests

Run the automated test suite:

```powershell
python -m pytest -q
```

To generate a coverage report:

```powershell
python -m pytest --cov=app --cov-report=term-missing
```

**Latest recorded local test result:** 34 passed, 6 warnings. Run the suite again after code changes to verify the current state.

## Core Workflow

The backend supports the following tested development workflow:

1. Authenticate as a doctor and a patient.
2. Create or identify a doctor's availability slot.
3. Book a consultation using an idempotency key.
4. Verify that a repeated request with the same key returns the existing booking.
5. Advance the consultation through permitted lifecycle states.
6. Issue a prescription after consultation completion.
7. Retrieve the prescription using its ID.
8. Retrieve the patient's prescription list.

Use synthetic test data when demonstrating these workflows.

## Observability

The project includes health-check and metrics functionality, along with application logging.

For a production deployment, centralize logs and metrics, configure dashboards and alerts, and add distributed tracing where needed. Monitor request latency, error rates, database connection usage, booking conflicts, and dependency health.

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

## Security

Security considerations include:

- Authentication and role-based authorization.
- Input validation and controlled state transitions.
- Idempotency for critical write operations.
- Environment-based secret configuration.
- Audit logging for important actions.
- Protection of patient and prescription records.
- Dependency and container security scanning.

Before production deployment, verify object-level authorization, MFA coverage, rate limiting, TLS, encryption at rest, secret rotation, and backup recovery.

See [`docs/SECURITY.md`](docs/SECURITY.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Scalability and Reliability

The design targets the assignment's requirements of 100,000 daily consultations, read p95 latency below 200 ms, write p95 below 500 ms, and 99.95% availability.

Potential production measures include horizontal API scaling, indexed database queries, carefully selected caching, concurrency-safe booking transactions, bounded retries with backoff, asynchronous background jobs, database backups, and multi-zone deployment.

These are target requirements, not measured performance guarantees. Load testing and production infrastructure validation are required before claiming the targets have been achieved.

## Continuous Integration

GitHub Actions configuration is located in `.github/workflows/ci.yml`.

The workflow runs automated checks when triggered by configured repository events. Review the GitHub Actions results after each push and resolve any failed checks before submitting the project.

## Documentation

- [Architecture and system design](docs/ARCHITECTURE.md)
- [Security checklist and threat model](docs/SECURITY.md)
- [Operations, observability, and disaster recovery](docs/OPERATIONS.md)

## Future Improvements

- Production-grade distributed tracing and alerting.
- Load testing and performance benchmarking.
- Managed secrets and automated key rotation.
- Hardened MFA and session lifecycle controls.
- Durable asynchronous processing and transactional outbox integration.
- Automated backup restoration and disaster recovery testing.
- Dependency and container image scanning in CI/CD.

## Disclaimer

This repository is a telemedicine backend development project. Successful local tests do not by themselves establish production readiness, regulatory compliance, or achievement of the stated scale and availability targets.

