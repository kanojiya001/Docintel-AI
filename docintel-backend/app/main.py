from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import (
    auth_router, doc_router, chat_router,
    summary_router, compare_router, question_router,
    analytics_router, export_router,
)
from app.database.db import init_db
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise AI Document Intelligence Platform — RAG-powered analysis, summarization, comparison, and question generation.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(doc_router)
app.include_router(chat_router)
app.include_router(summary_router)
app.include_router(compare_router)
app.include_router(question_router)
app.include_router(analytics_router)
app.include_router(export_router)


@app.on_event("startup")
async def startup():
    try:
        await init_db()
        print("[DocIntel] Database tables verified/created.")
    except Exception as e:
        print(f"[DocIntel] WARNING: Could not connect to database on startup: {e}")
        print("[DocIntel] The app will still start — check your DATABASE_URL in .env")


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/auth/test", tags=["Health"])
async def auth_test():
    """Quick endpoint to verify the backend is reachable from the browser."""
    return {"status": "ok", "message": "Backend is reachable"}
