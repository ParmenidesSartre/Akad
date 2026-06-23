from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from registry.database import create_tables
from registry.routers import contracts, health, results


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="Akad Contract Registry",
    description="Contract storage, versioning, and breach history for the Akad data contract framework",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(contracts.router, prefix="/contracts",          tags=["Contracts"])
app.include_router(results.router,   prefix="/validation-results", tags=["Validation Results"])
app.include_router(health.router,    prefix="/health",             tags=["Health"])
