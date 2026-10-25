#!/usr/bin/env bash
# Cria um cluster Kubernetes local com kind (usado no GitHub Codespaces).
# No Rancher Desktop NÃO é necessário: basta ativar o Kubernetes nas preferências.
set -euo pipefail
CLUSTER=pedidos-veloz

if ! kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER" --wait 120s
fi

# metrics-server: necessário para o HPA ler o uso de CPU dos Pods
if ! kubectl -n kube-system get deployment metrics-server >/dev/null 2>&1; then
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml
  # no kind os certificados do kubelet são autoassinados
  kubectl -n kube-system patch deployment metrics-server --type=json \
    -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
fi
echo "✔ Cluster kind '$CLUSTER' pronto. Próximo passo: bash scripts/k8s-deploy.sh"
