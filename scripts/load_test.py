#!/usr/bin/env python3
"""Gerador de carga simples (somente biblioteca padrão) para demonstrar o HPA
e alimentar os painéis do Grafana.

Uso:
    python3 scripts/load_test.py --url http://localhost:8080 --duracao 120 --concorrencia 20
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

SKUS = ["TEN-001", "CAM-002", "MOC-003"]


def requisicao(base: str) -> tuple[int, float]:
    inicio = time.perf_counter()
    if random.random() < 0.7:  # 70% leituras de catálogo, 30% criação de pedidos
        req = urllib.request.Request(f"{base}/api/produtos")
    else:
        corpo = json.dumps({"sku": random.choice(SKUS), "quantidade": 1}).encode()
        req = urllib.request.Request(
            f"{base}/api/pedidos", data=corpo, headers={"content-type": "application/json"}
        )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            codigo = resp.status
    except urllib.error.HTTPError as exc:
        codigo = exc.code
    except Exception:  # noqa: BLE001
        codigo = 0  # erro de conexão / timeout
    return codigo, (time.perf_counter() - inicio) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--duracao", type=int, default=60, help="segundos")
    parser.add_argument("--concorrencia", type=int, default=10)
    args = parser.parse_args()

    fim = time.time() + args.duracao
    codigos: Counter[int] = Counter()
    latencias: list[float] = []
    trava = threading.Lock()

    def trabalhador() -> None:
        while time.time() < fim:
            codigo, ms = requisicao(args.url)
            with trava:
                codigos[codigo] += 1
                latencias.append(ms)

    print(f"▶ Carga em {args.url} por {args.duracao}s com {args.concorrencia} clientes...")
    with ThreadPoolExecutor(max_workers=args.concorrencia) as pool:
        for _ in range(args.concorrencia):
            pool.submit(trabalhador)

    total = sum(codigos.values())
    erros = sum(v for k, v in codigos.items() if k == 0 or k >= 500)
    latencias.sort()
    p95 = latencias[int(len(latencias) * 0.95) - 1] if latencias else 0
    print(f"Requisições: {total}  ({total / args.duracao:.1f} req/s)")
    print(f"Status:      {dict(codigos)}")
    print(f"Erros (5xx/conexão): {erros} ({100 * erros / max(total, 1):.2f}%)")
    print(f"Latência:    p50={statistics.median(latencias):.0f} ms  p95={p95:.0f} ms")


if __name__ == "__main__":
    main()
