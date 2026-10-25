import json
import os
import pathlib
import sys

SERVICE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SERVICE_DIR), str(SERVICE_DIR.parents[1] / "libs")]
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ESTOQUE_URL"] = "http://estoque"
os.environ["PAGAMENTOS_URL"] = "http://pagamentos"
os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class FakeDownstream:
    """Simula Estoque e Pagamentos para testar o Pedidos isoladamente."""

    def __init__(self) -> None:
        self.livre = {"TEN-001": 10}
        self.preco = {"TEN-001": 29990}
        self.pagamento_status = "APROVADO"
        self.pagamentos_fora = False
        self.chamadas: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.chamadas.append(f"{request.method} {request.url.host}{path}")

        if request.url.host == "estoque":
            if request.method == "GET" and path.startswith("/produtos/"):
                sku = path.rsplit("/", 1)[-1]
                if sku not in self.preco:
                    return httpx.Response(404, json={"detail": "produto não encontrado"})
                return httpx.Response(200, json={"sku": sku, "preco_centavos": self.preco[sku]})
            if path == "/reservas":
                body = json.loads(request.content)
                if body["quantidade"] > self.livre[body["sku"]]:
                    return httpx.Response(409, json={"detail": "estoque insuficiente"})
                return httpx.Response(201, json={**body, "status": "RESERVADA"})
            if path.endswith("/confirmar") or path.endswith("/cancelar"):
                return httpx.Response(200, json={"status": "ok"})

        if request.url.host == "pagamentos":
            if self.pagamentos_fora:
                return httpx.Response(503, json={"detail": "indisponível"})
            body = json.loads(request.content)
            return httpx.Response(
                201,
                json={
                    "pagamento_id": "x",
                    "pedido_id": body["pedido_id"],
                    "status": self.pagamento_status,
                    "motivo": None if self.pagamento_status == "APROVADO" else "limite",
                },
            )
        return httpx.Response(500)


@pytest.fixture()
def downstream() -> FakeDownstream:
    return FakeDownstream()


@pytest.fixture()
def client(downstream):
    from app import clients
    from app.db import engine, init_db
    from app.main import app
    from app.models import Base

    Base.metadata.drop_all(engine)
    init_db()
    fake_http = httpx.Client(transport=httpx.MockTransport(downstream))
    app.dependency_overrides[clients.get_http] = lambda: fake_http
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
