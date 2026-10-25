"""Serviço de Pedidos: cria e consulta pedidos, orquestrando Estoque e Pagamentos.

Fluxo de criação (saga orquestrada simples):
1. consulta o produto no Estoque (preço);
2. grava o pedido como PENDENTE;
3. reserva os itens no Estoque;
4. cobra no Pagamentos;
5. confirma a reserva (CONFIRMADO) ou a cancela (RECUSADO / FALHOU).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from prometheus_client import Counter
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from veloz_common.db import ping, wait_for_db
from veloz_common.observability import health_router, setup_observability

from . import clients
from .db import engine, get_db, init_db
from .models import Pedido

SERVICE = "pedidos"


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db(engine, init_db)
    yield


app = FastAPI(
    title="Pedidos Veloz - Pedidos",
    version=os.getenv("APP_VERSION", "dev"),
    lifespan=lifespan,
)
log = setup_observability(app, SERVICE, engine)
app.include_router(health_router(lambda: ping(engine)))

PEDIDOS = Counter("pedidos_criados_total", "Pedidos criados por status final", ["status"])


class PedidoIn(BaseModel):
    sku: str = Field(min_length=1, max_length=32)
    quantidade: int = Field(gt=0, le=100)
    metodo_pagamento: Literal["pix", "cartao", "boleto"] = "pix"


class PedidoOut(BaseModel):
    id: str
    sku: str
    quantidade: int
    valor_total_centavos: int
    metodo_pagamento: str
    status: str
    motivo: str | None
    criado_em: datetime


def _out(p: Pedido) -> PedidoOut:
    return PedidoOut(
        id=p.id,
        sku=p.sku,
        quantidade=p.quantidade,
        valor_total_centavos=p.valor_total_centavos,
        metodo_pagamento=p.metodo_pagamento,
        status=p.status,
        motivo=p.motivo,
        criado_em=p.criado_em,
    )


def _finalizar(pedido: Pedido, novo_status: str, motivo: str | None, db: Session) -> PedidoOut:
    pedido.status = novo_status
    pedido.motivo = motivo
    db.commit()
    PEDIDOS.labels(status=novo_status).inc()
    log.info(
        "pedido finalizado",
        extra={"fields": {"pedido_id": pedido.id, "status": novo_status, "motivo": motivo}},
    )
    return _out(pedido)


@app.post("/pedidos", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def criar_pedido(
    dados: PedidoIn,
    db: Session = Depends(get_db),
    http: httpx.Client = Depends(clients.get_http),
) -> PedidoOut:
    # 1. Produto e preço
    try:
        resp = http.get(f"{clients.ESTOQUE_URL}/produtos/{dados.sku}")
    except httpx.HTTPError as exc:
        log.error("estoque indisponível", extra={"fields": {"error": str(exc)}})
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "estoque indisponível") from exc
    if resp.status_code == 404:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "produto não encontrado")
    if resp.status_code != 200:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "erro ao consultar estoque")
    produto = resp.json()

    # 2. Pedido pendente
    pedido = Pedido(
        sku=dados.sku,
        quantidade=dados.quantidade,
        valor_total_centavos=produto["preco_centavos"] * dados.quantidade,
        metodo_pagamento=dados.metodo_pagamento,
        status="PENDENTE",
    )
    db.add(pedido)
    db.commit()
    log.info("pedido criado", extra={"fields": {"pedido_id": pedido.id, "sku": dados.sku}})

    # 3. Reserva de estoque
    try:
        resp = http.post(
            f"{clients.ESTOQUE_URL}/reservas",
            json={"pedido_id": pedido.id, "sku": dados.sku, "quantidade": dados.quantidade},
        )
    except httpx.HTTPError:
        return _finalizar(pedido, "FALHOU", "estoque indisponível", db)
    if resp.status_code == 409:
        return _finalizar(pedido, "RECUSADO", "estoque insuficiente", db)
    if resp.status_code not in (200, 201):
        return _finalizar(pedido, "FALHOU", "erro ao reservar estoque", db)

    # 4. Pagamento
    pagamento: dict | None = None
    try:
        resp = http.post(
            f"{clients.PAGAMENTOS_URL}/pagamentos",
            json={
                "pedido_id": pedido.id,
                "valor_centavos": pedido.valor_total_centavos,
                "metodo": dados.metodo_pagamento,
            },
        )
        if resp.status_code == 201:
            pagamento = resp.json()
    except httpx.HTTPError as exc:
        log.error("pagamentos indisponível", extra={"fields": {"error": str(exc)}})

    # 5. Compensação ou confirmação
    if pagamento is None:
        _cancelar_reserva(http, pedido.id)
        return _finalizar(pedido, "FALHOU", "pagamento indisponível", db)
    if pagamento["status"] != "APROVADO":
        _cancelar_reserva(http, pedido.id)
        return _finalizar(pedido, "RECUSADO", pagamento.get("motivo") or "pagamento recusado", db)

    http.post(f"{clients.ESTOQUE_URL}/reservas/{pedido.id}/confirmar")
    return _finalizar(pedido, "CONFIRMADO", None, db)


def _cancelar_reserva(http: httpx.Client, pedido_id: str) -> None:
    try:
        http.post(f"{clients.ESTOQUE_URL}/reservas/{pedido_id}/cancelar")
    except httpx.HTTPError as exc:
        # Em produção iria para uma fila de reprocessamento (outbox / DLQ).
        log.error(
            "falha ao cancelar reserva", extra={"fields": {"pedido_id": pedido_id, "error": str(exc)}}
        )


@app.get("/pedidos", response_model=list[PedidoOut])
def listar_pedidos(limite: int = 20, db: Session = Depends(get_db)) -> list[PedidoOut]:
    limite = max(1, min(limite, 100))
    pedidos = db.scalars(select(Pedido).order_by(Pedido.criado_em.desc()).limit(limite))
    return [_out(p) for p in pedidos]


@app.get("/pedidos/{pedido_id}", response_model=PedidoOut)
def obter_pedido(pedido_id: str, db: Session = Depends(get_db)) -> PedidoOut:
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "pedido não encontrado")
    return _out(pedido)
