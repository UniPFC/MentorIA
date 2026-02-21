from contextlib import asynccontextmanager
from fastapi import FastAPI
from config.logger import logger
from shared.database.migration import run_migrations

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting api...")
    run_migrations()
    yield
    logger.info("Shutting down api...")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Chat & RAG API"}
