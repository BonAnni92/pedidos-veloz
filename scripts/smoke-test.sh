#!/usr/bin/env bash
# Smoke test ponta a ponta pelo API Gateway.
# Uso: bash scripts/smoke-test.sh [URL]   (padrão: http://localhost:8080)
set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"
ok()   { echo "  ✅ $*"; }
fail() { echo "  ❌ $*"; exit 1; }
campo() { python3 -c "import sys, json; print(json.load(sys.stdin)$1)"; }

echo "▶ Smoke test em $BASE_URL"

for i in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health/ready" >/dev/null 2>&1; then break; fi
  [ "$i" = 30 ] && fail "gateway não ficou pronto"
  sleep 2
done
ok "gateway pronto"

qtd=$(curl -fsS "$BASE_URL/api/produtos" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
[ "$qtd" -ge 3 ] || fail "catálogo vazio"
ok "catálogo com $qtd produtos (gateway -> estoque -> PostgreSQL)"

pedido=$(curl -fsS -X POST "$BASE_URL/api/pedidos" -H 'content-type: application/json' \
  -d '{"sku": "CAM-002", "quantidade": 1, "metodo_pagamento": "pix"}')
id=$(echo "$pedido" | campo "['id']")
status=$(echo "$pedido" | campo "['status']")
[ "$status" = "CONFIRMADO" ] || fail "pedido deveria ser CONFIRMADO, veio $status: $pedido"
ok "pedido $id CONFIRMADO (pedidos -> estoque -> pagamentos)"

status=$(curl -fsS "$BASE_URL/api/pedidos/$id" | campo "['status']")
[ "$status" = "CONFIRMADO" ] || fail "consulta do pedido retornou $status"
ok "consulta do pedido persistido"

status=$(curl -fsS -X POST "$BASE_URL/api/pedidos" -H 'content-type: application/json' \
  -d '{"sku": "MOC-003", "quantidade": 99}' | campo "['status']")
[ "$status" = "RECUSADO" ] || fail "pedido sem estoque deveria ser RECUSADO, veio $status"
ok "pedido sem estoque RECUSADO (compensação)"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/api/pedidos" \
  -H 'content-type: application/json' -d '{"sku": "CAM-002", "quantidade": 0}')
[ "$code" = "422" ] || fail "validação deveria retornar 422, retornou $code"
ok "validação de entrada (422)"

echo "✔ Todos os testes passaram"
