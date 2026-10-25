"""Cliente HTTP para os serviços de Estoque e Pagamentos.

- timeout curto: um serviço lento não deve prender as threads do Pedidos;
- retries=2 no transporte: repete apenas falhas de conexão (seguro);
- criado sob demanda, depois que o tracing foi configurado, para que o
  cabeçalho "traceparent" seja propagado automaticamente.
"""

from __future__ import annotations

import os

import httpx

ESTOQUE_URL = os.getenv("ESTOQUE_URL", "http://estoque:8000")
PAGAMENTOS_URL = os.getenv("PAGAMENTOS_URL", "http://pagamentos:8000")

_client: httpx.Client | None = None


def get_http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=float(os.getenv("HTTP_TIMEOUT_SECONDS", "3")),
            transport=httpx.HTTPTransport(retries=2),
        )
    return _client
