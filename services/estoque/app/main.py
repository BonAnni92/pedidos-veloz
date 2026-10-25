"""Serviço de Estoque: catálogo, reserva e baixa de itens."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from veloz_common.db import ping, wait_for_db
from veloz_common.observability import health_router, setup_observability

from .db import engine, get_db, init_db
from .models import Produto, Reserva

SERVICE = "estoque"


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db(engine, init_db)
    yield


app = FastAPI(
    title="Pedidos Veloz - Estoque",
    version=os.getenv("APP_VERSION", "dev"),
    lifespan=lifespan,
)
log = setup_observability(app, SERVICE, engine)
app.include_router(health_router(lambda: ping(engine)))


class ProdutoOut(BaseModel):
    sku: str
    nome: str
    preco_centavos: int
    disponivel: int
    reservado: int
    livre: int


class ReservaIn(BaseModel):
    pedido_id: str = Field(min_length=1, max_length=36)
    sku: str
    quantidade: int = Field(gt=0, le=100)


class ReservaOut(BaseModel):
    pedido_id: str
    sku: str
    quantidade: int
    status: str


def _produto_out(p: Produto) -> ProdutoOut:
    return ProdutoOut(
        sku=p.sku,
        nome=p.nome,
        preco_centavos=p.preco_centavos,
        disponivel=p.disponivel,
        reservado=p.reservado,
        livre=p.livre,
    )


def _reserva_out(r: Reserva) -> ReservaOut:
    return ReservaOut(pedido_id=r.pedido_id, sku=r.sku, quantidade=r.quantidade, status=r.status)


@app.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(db: Session = Depends(get_db)) -> list[ProdutoOut]:
    return [_produto_out(p) for p in db.scalars(select(Produto).order_by(Produto.sku))]


@app.get("/produtos/{sku}", response_model=ProdutoOut)
def obter_produto(sku: str, db: Session = Depends(get_db)) -> ProdutoOut:
    produto = db.get(Produto, sku)
    if produto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "produto não encontrado")
    return _produto_out(produto)


@app.post("/reservas", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def reservar(dados: ReservaIn, db: Session = Depends(get_db)) -> ReservaOut:
    existente = db.get(Reserva, dados.pedido_id)
    if existente is not None:  # idempotência: o Pedidos pode repetir a chamada
        return _reserva_out(existente)

    # SELECT ... FOR UPDATE: evita vender o mesmo item duas vezes sob concorrência.
    produto = db.scalars(
        select(Produto).where(Produto.sku == dados.sku).with_for_update()
    ).first()
    if produto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "produto não encontrado")
    if produto.livre < dados.quantidade:
        log.info(
            "estoque insuficiente",
            extra={"fields": {"sku": dados.sku, "livre": produto.livre, "pedido_id": dados.pedido_id}},
        )
        raise HTTPException(status.HTTP_409_CONFLICT, "estoque insuficiente")

    produto.reservado += dados.quantidade
    reserva = Reserva(
        pedido_id=dados.pedido_id, sku=dados.sku, quantidade=dados.quantidade, status="RESERVADA"
    )
    db.add(reserva)
    db.commit()
    log.info("itens reservados", extra={"fields": {"pedido_id": dados.pedido_id, "sku": dados.sku}})
    return _reserva_out(reserva)


def _finalizar(pedido_id: str, novo_status: str, db: Session) -> ReservaOut:
    reserva = db.get(Reserva, pedido_id)
    if reserva is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "reserva não encontrada")
    if reserva.status == novo_status:
        return _reserva_out(reserva)
    if reserva.status != "RESERVADA":
        raise HTTPException(status.HTTP_409_CONFLICT, f"reserva já está {reserva.status}")

    produto = db.scalars(
        select(Produto).where(Produto.sku == reserva.sku).with_for_update()
    ).one()
    produto.reservado -= reserva.quantidade
    if novo_status == "CONFIRMADA":
        produto.disponivel -= reserva.quantidade  # baixa definitiva
    reserva.status = novo_status
    db.commit()
    log.info("reserva finalizada", extra={"fields": {"pedido_id": pedido_id, "status": novo_status}})
    return _reserva_out(reserva)


@app.post("/reservas/{pedido_id}/confirmar", response_model=ReservaOut)
def confirmar(pedido_id: str, db: Session = Depends(get_db)) -> ReservaOut:
    return _finalizar(pedido_id, "CONFIRMADA", db)


@app.post("/reservas/{pedido_id}/cancelar", response_model=ReservaOut)
def cancelar(pedido_id: str, db: Session = Depends(get_db)) -> ReservaOut:
    return _finalizar(pedido_id, "CANCELADA", db)
