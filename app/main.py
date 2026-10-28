from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.db import engine, SessionLocal
from app.api.v1 import admin, auth, consultations, doctors, payments, prescriptions, users
from app.models import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Amrutam Telemedicine Backend",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health/live", tags=["health"])
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness():
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready"},
        )



@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


for module in (auth, users, doctors, consultations, prescriptions, payments, admin):
    app.include_router(module.router, prefix="/api/v1")

