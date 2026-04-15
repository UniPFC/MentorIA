from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from config.logger import logger
from config.settings import settings
from shared.database.migration import run_migrations
from src.api.routes import chat_types, chats, upload, jobs, auth
from src.services.seeder import seed_default_knowledge
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting API...")
    run_migrations()
    
    try:
        if not settings.DEV_MODE:
            logger.info("Running background seeder...")
            await asyncio.to_thread(seed_default_knowledge)
    except Exception as e:
        logger.error(f"Seeder failed: {e}")
        
    yield
    logger.info("Shutting down API...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-tenant RAG chat system with custom knowledge bases",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Retorna mensagens de erro de validação mais claras"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"][1:])
        msg = error["msg"]
        
        # Remover prefixo "Value error, " que o Pydantic adiciona
        if msg.startswith("Value error, "):
            msg = msg.replace("Value error, ", "", 1)
        
        # Melhorar mensagens de validação de senha
        if field == "password" or field == "new_password":
            if "at least 8 characters" in msg or "Senha deve ter no mínimo 8 caracteres" in msg:
                msg = "Senha deve ter no mínimo 8 caracteres."
            elif "String should have at least" in msg:
                msg = "Senha deve ter no mínimo 8 caracteres."
        
        errors.append({
            "field": field,
            "message": msg
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Erro de validação",
            "errors": errors
        }
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
