"""Observabilidade padronizada: logs JSON, métricas Prometheus e tracing OpenTelemetry.

12-Factor (fator XI): logs são escritos no stdout como fluxo de eventos; quem
coleta e armazena é a plataforma (Docker / Kubernetes), não a aplicação.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Callable

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from prometheus_fastapi_instrumentator import Instrumentator

QUIET_PATHS = {"/health/live", "/health/ready", "/metrics"}


class JsonFormatter(logging.Formatter):
    """Formata cada log como uma linha JSON, incluindo trace_id/span_id."""

    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "message": record.getMessage(),
        }
        span_ctx = trace.get_current_span().get_span_context()
        if span_ctx.is_valid:
            payload["trace_id"] = format(span_ctx.trace_id, "032x")
            payload["span_id"] = format(span_ctx.span_id, "016x")
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(service: str) -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    # O access log padrão do uvicorn é texto puro; usamos o nosso (JSON) no lugar.
    logging.getLogger("uvicorn.access").disabled = True
    # Cada chamada HTTP já aparece no trace; evitamos duplicar no log.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logging.getLogger(service)


def _setup_tracing(app: FastAPI, service: str, engine: object | None) -> bool:
    """Ativa o tracing apenas se houver um coletor configurado (OTLP/HTTP)."""
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return False

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": service,
            "service.version": os.getenv("APP_VERSION", "dev"),
            "deployment.environment": os.getenv("APP_ENV", "local"),
        }
    )
    provider = TracerProvider(resource=resource)
    # O exporter lê OTEL_EXPORTER_OTLP_ENDPOINT e acrescenta /v1/traces.
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health/live,health/ready,metrics")
    # Injeta o cabeçalho W3C "traceparent" nas chamadas entre serviços.
    HTTPXClientInstrumentor().instrument()
    if engine is not None:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=engine)
    return True


def setup_observability(app: FastAPI, service: str, engine: object | None = None) -> logging.Logger:
    """Configura logs, métricas (/metrics) e tracing para um serviço."""
    logger = configure_logging(service)
    tracing = _setup_tracing(app, service, engine)

    Instrumentator(excluded_handlers=list(QUIET_PATHS)).instrument(app).expose(
        app, include_in_schema=False
    )

    @app.middleware("http")
    async def access_log(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        response = await call_next(request)
        if request.url.path not in QUIET_PATHS:
            logger.info(
                "request",
                extra={
                    "fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    }
                },
            )
        return response

    logger.info("observabilidade configurada", extra={"fields": {"tracing": tracing}})
    return logger


def health_router(check_ready: Callable[[], None] | None = None) -> APIRouter:
    """/health/live (liveness) e /health/ready (readiness).

    - liveness: o processo está vivo? Não verifica dependências, para evitar
      reinícios em cascata quando o banco oscila.
    - readiness: o Pod pode receber tráfego? Verifica as dependências próprias.
    """
    router = APIRouter(tags=["health"])

    @router.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/health/ready")
    def ready() -> JSONResponse:
        if check_ready is not None:
            try:
                check_ready()
            except Exception as exc:  # noqa: BLE001
                return JSONResponse(
                    status_code=503, content={"status": "not-ready", "reason": str(exc)}
                )
        return JSONResponse(content={"status": "ready"})

    return router
