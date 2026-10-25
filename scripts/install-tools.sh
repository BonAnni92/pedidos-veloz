#!/usr/bin/env bash
# Instala kind e kubeconform (usado pelo devcontainer do Codespaces).
set -euo pipefail
ARCH=$(uname -m | sed 's/x86_64/amd64/; s/aarch64/arm64/')
curl -fsSLo /tmp/kind "https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-${ARCH}"
sudo install /tmp/kind /usr/local/bin/kind
curl -fsSL "https://github.com/yannh/kubeconform/releases/download/v0.6.7/kubeconform-linux-${ARCH}.tar.gz" \
  | sudo tar xz -C /usr/local/bin kubeconform
echo "✔ kind e kubeconform instalados"
