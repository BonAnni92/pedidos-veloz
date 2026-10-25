"""Serviço de Pagamentos: simula a integração com um gateway de pagamento externo.

Parâmetros de simulação (variáveis de ambiente / ConfigMap):
- PAGAMENTO_LIMITE_CENTAVOS: valores acima disso são recusados.
- PAGAMENTO_LATENCIA_MAX_MS: latência aleatória do "provedor externo".
- PAGAMENTO_TAXA_FALHA: probabilidade (0..1) de o provedor responder 503,
  útil para demonstrar tracing de erros e resiliência.
"""

from __future__ import annotations

import os
import random
import time
import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from prometheus_client import Counter
from pydantic import BaseModel, Field

from veloz_common.observability import health_router, setup_observability

SERVICE = "pagamentos"

app = FastAPI(title="Pedidos Veloz - Pagamentos", version=os.getenv("APP_VERSION", "dev"))
log = setup_observability(app, SERVICE)
app.include_router(health_router())

PAGAMENTOS = Counter("pagamentos_total", "Pagamentos processados por resultado", ["resultado"])


class PagamentoIn(BaseModel):
    pedido_id: str = Field(min_length=1, max_length=36)
    valor_centavos: int = Field(gt=0)
    metodo: Literal["pix", "cartao", "boleto"] = "pix"


class PagamentoOut(BaseModel):
    pagamento_id: str
    pedido_id: str
    status: Literal["APROVADO", "RECUSADO"]
    motivo: str | None = None


def _cfg(nome: str, padrao: str) -> float:
    return float(os.getenv(nome, padrao))


@app.post("/pagamentos", response_model=PagamentoOut, status_code=status.HTTP_201_CREATED)
def processar(dados: PagamentoIn) -> PagamentoOut:
    latencia_ms = random.uniform(0, _cfg("PAGAMENTO_LATENCIA_MAX_MS", "300"))
    time.sleep(latencia_ms / 1000)

    if random.random() < _cfg("PAGAMENTO_TAXA_FALHA", "0"):
        PAGAMENTOS.labels(resultado="erro_provedor").inc()
        log.error("provedor de pagamento indisponível", extra={"fields": {"pedido_id": dados.pedido_id}})
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "provedor de pagamento indisponível")

    limite = _cfg("PAGAMENTO_LIMITE_CENTAVOS", "500000")
    if dados.valor_centavos > limite:
        resultado = PagamentoOut(
            pagamento_id=str(uuid.uuid4()),
            pedido_id=dados.pedido_id,
            status="RECUSADO",
            motivo="valor acima do limite aprovado",
        )
    else:
        resultado = PagamentoOut(
            pagamento_id=str(uuid.uuid4()), pedido_id=dados.pedido_id, status="APROVADO"
        )

    PAGAMENTOS.labels(resultado=resultado.status.lower()).inc()
    log.info(
        "pagamento processado",
        extra={
            "fields": {
                "pedido_id": dados.pedido_id,
                "status": resultado.status,
                "metodo": dados.metodo,
                "latencia_ms": round(latencia_ms, 1),
            }
        },
    )
    return resultado
