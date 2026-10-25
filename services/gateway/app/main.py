"""API Gateway: ponto único de entrada HTTP da plataforma Pedidos Veloz.

Responsabilidades: roteamento para os serviços internos, padronização de
erros (503 quando um serviço está fora) e propagação do X-Request-ID.
Os serviços internos não são expostos fora do cluster.
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from veloz_common.observability import health_router, setup_observability

SERVICE = "gateway"
PEDIDOS_URL = os.getenv("PEDIDOS_URL", "http://pedidos:8000")
ESTOQUE_URL = os.getenv("ESTOQUE_URL", "http://estoque:8000")

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=float(os.getenv("HTTP_TIMEOUT_SECONDS", "5")),
            transport=httpx.AsyncHTTPTransport(retries=2),
        )
    return _client


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if _client is not None:
        await _client.aclose()


app = FastAPI(
    title="Pedidos Veloz - API Gateway",
    version=os.getenv("APP_VERSION", "dev"),
    lifespan=lifespan,
)
log = setup_observability(app, SERVICE)
app.include_router(health_router())


class PedidoIn(BaseModel):
    """Validação na borda: requisições inválidas nem chegam aos serviços internos."""

    sku: str = Field(min_length=1, max_length=32, examples=["TEN-001"])
    quantidade: int = Field(gt=0, le=100, examples=[1])
    metodo_pagamento: Literal["pix", "cartao", "boleto"] = "pix"


async def _forward(
    client: httpx.AsyncClient, request: Request, method: str, url: str, servico: str
) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    body = await request.body()
    try:
        resp = await client.request(
            method,
            url,
            content=body or None,
            params=dict(request.query_params),
            headers={"content-type": "application/json", "x-request-id": request_id},
        )
    except httpx.HTTPError as exc:
        log.error(
            "serviço indisponível",
            extra={"fields": {"servico": servico, "error": str(exc), "request_id": request_id}},
        )
        return JSONResponse(
            status_code=503,
            content={"detail": f"serviço {servico} indisponível"},
            headers={"x-request-id": request_id},
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
        headers={"x-request-id": request_id},
    )


@app.get("/")
def raiz() -> dict[str, object]:
    return {
        "servico": "Pedidos Veloz API Gateway",
        "versao": os.getenv("APP_VERSION", "dev"),
        "rotas": ["/api/produtos", "/api/produtos/{sku}", "/api/pedidos", "/api/pedidos/{id}"],
        "docs": "/docs",
    }


@app.get("/api/produtos")
async def produtos(request: Request, client: httpx.AsyncClient = Depends(get_client)) -> Response:
    return await _forward(client, request, "GET", f"{ESTOQUE_URL}/produtos", "estoque")


@app.get("/api/produtos/{sku}")
async def produto(
    sku: str, request: Request, client: httpx.AsyncClient = Depends(get_client)
) -> Response:
    return await _forward(client, request, "GET", f"{ESTOQUE_URL}/produtos/{sku}", "estoque")


@app.post("/api/pedidos")
async def criar_pedido(
    pedido: PedidoIn, request: Request, client: httpx.AsyncClient = Depends(get_client)
) -> Response:
    return await _forward(client, request, "POST", f"{PEDIDOS_URL}/pedidos", "pedidos")


@app.get("/api/pedidos")
async def listar_pedidos(
    request: Request, client: httpx.AsyncClient = Depends(get_client)
) -> Response:
    return await _forward(client, request, "GET", f"{PEDIDOS_URL}/pedidos", "pedidos")


@app.get("/api/pedidos/{pedido_id}")
async def obter_pedido(
    pedido_id: str, request: Request, client: httpx.AsyncClient = Depends(get_client)
) -> Response:
    return await _forward(client, request, "GET", f"{PEDIDOS_URL}/pedidos/{pedido_id}", "pedidos")
