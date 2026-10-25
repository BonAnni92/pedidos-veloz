from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Produto(Base):
    __tablename__ = "produtos"

    sku: Mapped[str] = mapped_column(String(32), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    preco_centavos: Mapped[int] = mapped_column(Integer)
    disponivel: Mapped[int] = mapped_column(Integer)  # estoque físico
    reservado: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def livre(self) -> int:
        return self.disponivel - self.reservado


class Reserva(Base):
    __tablename__ = "reservas"

    pedido_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sku: Mapped[str] = mapped_column(ForeignKey("produtos.sku"))
    quantidade: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))  # RESERVADA | CONFIRMADA | CANCELADA
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
