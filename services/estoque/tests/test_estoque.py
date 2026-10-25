def test_health(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200


def test_metrics_exposto(client):
    client.get("/produtos")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text


def test_lista_catalogo_inicial(client):
    produtos = client.get("/produtos").json()
    assert [p["sku"] for p in produtos] == ["CAM-002", "MOC-003", "TEN-001"]
    assert all(p["livre"] == p["disponivel"] for p in produtos)


def test_produto_inexistente(client):
    assert client.get("/produtos/NAO-EXISTE").status_code == 404


def test_reserva_e_confirmacao_baixam_estoque(client):
    resp = client.post("/reservas", json={"pedido_id": "p1", "sku": "MOC-003", "quantidade": 2})
    assert resp.status_code == 201
    assert resp.json()["status"] == "RESERVADA"

    produto = client.get("/produtos/MOC-003").json()
    assert produto["reservado"] == 2 and produto["livre"] == 3

    assert client.post("/reservas/p1/confirmar").json()["status"] == "CONFIRMADA"
    produto = client.get("/produtos/MOC-003").json()
    assert produto["disponivel"] == 3 and produto["reservado"] == 0


def test_cancelamento_libera_estoque(client):
    client.post("/reservas", json={"pedido_id": "p2", "sku": "MOC-003", "quantidade": 5})
    assert client.get("/produtos/MOC-003").json()["livre"] == 0
    assert client.post("/reservas/p2/cancelar").json()["status"] == "CANCELADA"
    assert client.get("/produtos/MOC-003").json()["livre"] == 5


def test_estoque_insuficiente(client):
    resp = client.post("/reservas", json={"pedido_id": "p3", "sku": "MOC-003", "quantidade": 6})
    assert resp.status_code == 409


def test_reserva_idempotente(client):
    body = {"pedido_id": "p4", "sku": "TEN-001", "quantidade": 1}
    client.post("/reservas", json=body)
    client.post("/reservas", json=body)
    assert client.get("/produtos/TEN-001").json()["reservado"] == 1


def test_validacao_quantidade(client):
    resp = client.post("/reservas", json={"pedido_id": "p5", "sku": "TEN-001", "quantidade": 0})
    assert resp.status_code == 422


def test_nao_confirma_reserva_cancelada(client):
    client.post("/reservas", json={"pedido_id": "p6", "sku": "TEN-001", "quantidade": 1})
    client.post("/reservas/p6/cancelar")
    assert client.post("/reservas/p6/confirmar").status_code == 409
