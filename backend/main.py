from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from backend.api import (
    routes_agent,
    routes_briefing,
    routes_inventory,
    routes_predictions,
    routes_shipments,
)


app = FastAPI(
    title=(
        "Supply-Chain Disruption Agent API"
    ),
    description=(
        "Risk prediction, operational evidence retrieval, "
        "and AI investigation orchestration layer"
    ),
    version="1.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=[
        "*",
    ],
    allow_headers=[
        "*",
    ],
)


app.include_router(
    routes_shipments.router
)

app.include_router(
    routes_predictions.router
)

app.include_router(
    routes_agent.router
)

app.include_router(
    routes_briefing.router
)

app.include_router(
    routes_inventory.router
)


@app.get(
    "/health",
    tags=["Health"],
)
def health_check():
    """
    Report backend-service availability.
    """
    return {
        "status": "healthy",
        "service": (
            "Backend Orchestration"
        ),
    }