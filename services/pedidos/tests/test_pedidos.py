def test_health(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_pedido_confirmado(client, downstream):
    resp = client.post("/pedidos", json={"sku": "TEN-001", "quantidade": 2})
    assert resp.status_code == 201
    pedido = resp.json()
    assert pedido["status"] == "CONFIRMADO"
    assert pedido["valor_total_centavos"] == 59980
    assert f"POST estoque/reservas/{pedido['id']}/confirmar" in downstream.chamadas

    consultado = client.get(f"/pedidos/{pedido['id']}").json()
    assert consultado["status"] == "CONFIRMADO"


def test_estoque_insuficiente(client):
    pedido = client.post("/pedidos", json={"sku": "TEN-001", "quantidade": 50}).json()
    assert pedido["status"] == "RECUSADO"
    assert pedido["motivo"] == "estoque insuficiente"


def test_pagamento_recusado_cancela_reserva(client, downstream):
    downstream.pagamento_status = "RECUSADO"
    pedido = client.post("/pedidos", json={"sku": "TEN-001", "quantidade": 1}).json()
    assert pedido["status"] == "RECUSADO"
    assert f"POST estoque/reservas/{pedido['id']}/cancelar" in downstream.chamadas


def test_pagamentos_fora_do_ar_compensa(client, downstream):
    downstream.pagamentos_fora = True
    pedido = client.post("/pedidos", json={"sku": "TEN-001", "quantidade": 1}).json()
    assert pedido["status"] == "FALHOU"
    assert f"POST estoque/reservas/{pedido['id']}/cancelar" in downstream.chamadas


def test_produto_inexistente(client):
    assert client.post("/pedidos", json={"sku": "XYZ", "quantidade": 1}).status_code == 404


def test_validacao(client):
    assert client.post("/pedidos", json={"sku": "TEN-001", "quantidade": 0}).status_code == 422


def test_listagem_e_404(client):
    client.post("/pedidos", json={"sku": "TEN-001", "quantidade": 1})
    assert len(client.get("/pedidos").json()) == 1
    assert client.get("/pedidos/nao-existe").status_code == 404


def test_metrica_de_negocio(client):
    client.post("/pedidos", json={"sku": "TEN-001", "quantidade": 1})
    assert 'pedidos_criados_total{status="CONFIRMADO"}' in client.get("/metrics").text
