#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 22.04/24.04 EC2 instance as a single-node k3s cluster for PulseOps.
# Safe to re-run.   Usage (on the EC2 host):   bash scripts/ec2-setup.sh
#
# Why each step exists (these were the reasons the first k8s attempt kept failing on a free-tier box):
#   * swap      - 1-2 GiB of RAM is not enough for k3s + 6 pods; without swap the kernel OOM-kills pods at random.
#   * k3s flags - metrics-server is disabled (Prometheus replaces it) to save ~60 MiB.
#   * no builds - never build the images on the EC2 box (the Next.js build alone needs >1.5 GiB RAM);
#                 GitHub Actions builds them and pushes to GHCR, the cluster just pulls.
set -euo pipefail
SWAP_SIZE="${SWAP_SIZE:-2G}"

echo "==> 1/4 swap (${SWAP_SIZE})"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l "$SWAP_SIZE" /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi
# Prefer RAM, use swap only under pressure.
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-pulseops.conf >/dev/null
sudo sysctl -q --system
free -h

echo "==> 2/4 k3s"
if ! command -v k3s >/dev/null; then
  curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
    --disable metrics-server \
    --write-kubeconfig-mode 644 \
    --kubelet-arg=fail-swap-on=false" sh -
fi
mkdir -p "$HOME/.kube"
sudo cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"
chmod 600 "$HOME/.kube/config"
grep -q 'KUBECONFIG=' "$HOME/.bashrc" || echo 'export KUBECONFIG=$HOME/.kube/config' >> "$HOME/.bashrc"
export KUBECONFIG="$HOME/.kube/config"

echo "==> 3/4 helm"
if ! command -v helm >/dev/null; then
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

echo "==> 4/4 waiting for the node and Traefik"
until kubectl get nodes 2>/dev/null | grep -q ' Ready'; do sleep 3; done
kubectl -n kube-system rollout status deploy/traefik --timeout=300s || true
kubectl get nodes -o wide
echo
echo "Done. Next: deploy with   bash scripts/deploy.sh <image-tag>   (or push to main and let GitHub Actions do it)."
