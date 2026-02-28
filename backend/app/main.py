"""
AI Presentation Generator - Main FastAPI Application
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add backend directory to path for db module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.routes import router
from app.services.session_service import session_manager
from app.services.job_service import job_manager
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    print("🚀 AI Presentation Generator starting up...")
    
    # Initialize database
    await init_db()
    
    # Ensure storage directories exist
    os.makedirs("storage/sessions", exist_ok=True)
    os.makedirs("storage/outputs", exist_ok=True)
    
    # Start background job processor
    job_task = asyncio.create_task(job_manager.process_jobs())
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")
    job_task.cancel()
    try:
        await job_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="AI Presentation Generator",
    description="Generate professional presentations using AI with ChatGPT-like session context",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Serve static files for downloads
os.makedirs("storage/outputs", exist_ok=True)
app.mount("/downloads", StaticFiles(directory="storage/outputs"), name="downloads")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Presentation Generator",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "providers": {
            "groq": "configured",
            "gemini": "configured"
        },
        "sessions_active": len(session_manager.sessions)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
