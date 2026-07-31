from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.logger import logger
from config.settings import settings
from shared.database.migration import run_migrations
from src.api.routes import (
    admin,
    audio,
    auth,
    chat_types,
    chats,
    jobs,
    payments,
    upload,
    websocket,
)
from src.middleware.https_security import (
    SecureCookieMiddleware,
    SecurityHeadersMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting API...")
    run_migrations()

    yield
    logger.info("Shutting down API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-tenant RAG chat system with custom knowledge bases",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_API_DOCS else None,
)

# Adicionar middlewares de segurança (ordem importa!)
# 1. Forçar HTTPS em produção
# app.add_middleware(HTTPSRedirectMiddleware)

# 2. Adicionar headers de segurança
app.add_middleware(SecurityHeadersMiddleware)

# 3. Garantir cookies seguros
app.add_middleware(SecureCookieMiddleware)

# Configure CORS (depois dos middlewares de segurança)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-STT-Enabled"],
)


# Middleware to add STT availability header
@app.middleware("http")
async def add_stt_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-STT-Enabled"] = str(settings.STT_ENABLED).lower()
    return response


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
            if (
                "at least 8 characters" in msg
                or "Senha deve ter no mínimo 8 caracteres" in msg
            ):
                msg = "Senha deve ter no mínimo 8 caracteres."
            elif "String should have at least" in msg:
                msg = "Senha deve ter no mínimo 8 caracteres."

        errors.append({"field": field, "message": msg})

    return JSONResponse(
        status_code=422, content={"detail": "Erro de validação", "errors": errors}
    )


# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(chat_types.router, prefix="/api/v1")
app.include_router(chats.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(audio.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
app.include_router(payments.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])


@app.get("/")
def root():
    return {"message": "RAG Chat API", "version": app.version, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
