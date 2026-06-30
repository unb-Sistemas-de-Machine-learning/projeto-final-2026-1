"""API HTTP e entrega da interface web do RetentionAI."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.agent import RetentionAgent
from app.config import BASE_DIR, settings
from app.model_service import ModelService
from app.monitoring import Monitor
from app.schemas import CustomerProfile, HealthResponse, PredictionResponse

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    model = ModelService(settings.model_path)
    monitor = Monitor(settings.log_path)
    application.state.model = model
    application.state.monitor = monitor
    application.state.agent = RetentionAgent(model, monitor)
    yield


app = FastAPI(
    title="RetentionAI API",
    summary="Predição auditável de churn e recomendações de retenção.",
    version=__version__,
    lifespan=lifespan,
)


@app.middleware("http")
async def security_and_size_guardrail(request: Request, call_next):
    content_length = int(request.headers.get("content-length", "0") or 0)
    if content_length > 50_000:
        return JSONResponse(
            status_code=413,
            content={"error": "payload_too_large", "message": "A entrada excede 50 KB."},
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {
            "field": ".".join(str(part) for part in error["loc"][1:]) or "body",
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "invalid_input",
            "message": "Revise os dados informados.",
            "details": fields,
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro não tratado: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Não foi possível concluir a análise. Tente novamente.",
        },
    )


@app.get("/health", response_model=HealthResponse, tags=["Operação"])
def health(request: Request) -> HealthResponse:
    model_loaded = request.app.state.model.available
    return HealthResponse(
        status="ok" if model_loaded else "degraded",
        model_loaded=model_loaded,
        version=__version__,
    )


@app.get("/api/v1/metrics", tags=["Operação"])
def operational_metrics(request: Request) -> dict[str, Any]:
    return request.app.state.monitor.snapshot()


@app.get("/api/v1/model-card", tags=["Modelo"])
def model_card() -> dict[str, Any]:
    if not settings.metrics_path.exists():
        return {"status": "unavailable", "message": "Métricas de treino não encontradas."}
    return json.loads(settings.metrics_path.read_text(encoding="utf-8"))


@app.post(
    "/api/v1/predict",
    response_model=PredictionResponse,
    tags=["Agente"],
    responses={422: {"description": "Entrada rejeitada por guardrail"}},
)
def predict(profile: CustomerProfile, request: Request) -> PredictionResponse:
    return request.app.state.agent.analyze(profile)


app.mount(
    "/",
    StaticFiles(directory=BASE_DIR / "app" / "static", html=True),
    name="interface",
)
