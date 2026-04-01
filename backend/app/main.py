"""
GHL Sales Assistant - FastAPI Application Entry Point

Main application setup with CORS, routers, and startup configuration.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.api.webhooks.ghl import router as webhook_router

# Configure Python root logger so app-level INFO logs appear in docker logs.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: [%(name)s] %(message)s",
)

app = FastAPI(
    title="GHL Sales Assistant API",
    description="Backend API for the GHL Sales Assistant Chrome Extension. "
    "Captures business leads and integrates with GoHighLevel CRM.",
    version="1.0.0",
)

# Configure CORS - allow all origins in development mode
# In production, set ALLOWED_ORIGINS to specific chrome-extension:// ID
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Include webhook routes (separate concern from REST API — no /api/v1 prefix)
app.include_router(webhook_router, prefix="/webhooks")


@app.get("/")
async def root():
    """Root endpoint - basic API info."""
    return {
        "app": "GHL Sales Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}
