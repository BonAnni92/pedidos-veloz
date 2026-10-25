#!/usr/bin/env bash
# Constrói as imagens e implanta tudo no cluster Kubernetes local
# (Rancher Desktop, kind ou Docker Desktop).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ Contexto atual do kubectl: $(kubectl config current-context)"

echo "▶ Build das imagens (tag :local)"
docker compose build estoque pagamentos pedidos gateway

# No kind as imagens precisam ser copiadas para dentro do cluster.
# No Rancher Desktop (motor dockerd/moby) o Kubernetes já enxerga as imagens locais.
if kubectl config current-context | grep -q '^kind-'; then
  cluster=$(kubectl config current-context | sed 's/^kind-//')
  for s in estoque pagamentos pedidos gateway; do
    kind load docker-image "ghcr.io/bonanni92/pedidos-veloz-$s:local" --name "$cluster"
  done
fi

echo "▶ Observabilidade (OTel Collector, Jaeger, Prometheus)"
kubectl apply -k k8s/observability

echo "▶ Aplicação (overlay local)"
kubectl apply -k k8s/overlays/local

kubectl -n loja-veloz rollout status statefulset/postgres --timeout=300s
for d in estoque pagamentos pedidos gateway; do
  kubectl -n loja-veloz rollout status deployment/$d --timeout=300s
done

kubectl -n loja-veloz get pods,svc,hpa
cat <<'MSG'

✔ Aplicação no ar. Para acessar:
   kubectl -n loja-veloz port-forward svc/gateway 8080:8000
   kubectl -n observability port-forward svc/jaeger 16686:16686
   kubectl -n observability port-forward svc/prometheus 9090:9090
MSG
