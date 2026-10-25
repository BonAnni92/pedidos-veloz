from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku: Mapped[str] = mapped_column(String(32))
    quantidade: Mapped[int] = mapped_column(Integer)
    valor_total_centavos: Mapped[int] = mapped_column(Integer)
    metodo_pagamento: Mapped[str] = mapped_column(String(16))
    # PENDENTE -> CONFIRMADO | RECUSADO | FALHOU
    status: Mapped[str] = mapped_column(String(16), default="PENDENTE")
    motivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
