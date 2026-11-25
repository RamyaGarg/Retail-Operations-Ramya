"""
Multi-Store Retail Operations Platform - FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database.db import get_db, init_db
from app.connectors import router as connectors_router
from app.dashboard import router as dashboard_router
from app.reconciliation import router as reconciliation_router
from app.pricing import router as pricing_router
from app.ai import router as ai_router
from app.hub_simulator import router as hub_simulator_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Retail Operations Platform",
    description="Multi-store retail operations management system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(connectors_router, prefix="/api/connectors", tags=["connectors"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(reconciliation_router, prefix="/api/reconciliation", tags=["reconciliation"])
app.include_router(pricing_router, prefix="/api/pricing", tags=["pricing"])
app.include_router(ai_router, prefix="/api/ai", tags=["ai"])
app.include_router(hub_simulator_router, prefix="/api/hub", tags=["hub"])


@app.get("/")
async def root():
    return {"message": "Retail Operations Platform API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}