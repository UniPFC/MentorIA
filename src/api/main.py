from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.logger import logger
from shared.database.migration import run_migrations
from src.api.routes import chat_types, chats, upload, jobs, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting API...")
    run_migrations()
    yield
    logger.info("Shutting down API...")

app = FastAPI(
    title="RAG Chat API",
    description="Multi-tenant RAG chat system with custom knowledge bases",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(chat_types.router, prefix="/api/v1")
app.include_router(chats.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "message": "RAG Chat API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
