#!/usr/bin/env bash
# Deploys / upgrades PulseOps on the k3s node with Helm. Called by GitHub Actions over SSH, or by hand.
#
#   bash scripts/deploy.sh <tag>                     # images from GHCR:  ghcr.io/$GHCR_OWNER/pulseops-{frontend,backend}:<tag>
#   IMAGE_SOURCE=local bash scripts/deploy.sh demo   # images already imported into k3s (podman/docker save | k3s ctr images import)
#
# Env: GHCR_OWNER (GitHub user/org, lowercase)   GHCR_USER + GHCR_TOKEN (only if the GHCR packages are private)
#      EXTRA_VALUES (optional extra values file)  NAMESPACE (default pulseops)  RELEASE (default pulseops)  VALUES (default helm/pulseops/values-micro.yaml)
set -euo pipefail
cd "$(dirname "$0")/.."

TAG="${1:?usage: deploy.sh <image-tag>}"
NAMESPACE="${NAMESPACE:-pulseops}"
RELEASE="${RELEASE:-pulseops}"
VALUES="${VALUES:-helm/pulseops/values-micro.yaml}"
IMAGE_SOURCE="${IMAGE_SOURCE:-ghcr}"
SECRETS_FILE="${SECRETS_FILE:-$HOME/.pulseops-secrets.env}"
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

# --- Secrets: generated once on the server, never committed, reused on every deploy -------------------
if [ ! -f "$SECRETS_FILE" ]; then
  umask 077
  existing() { kubectl -n "$NAMESPACE" get secret pulseops-secrets -o "jsonpath={.data.$1}" 2>/dev/null | base64 -d 2>/dev/null || true; }
  OLD_URL="$(existing DATABASE_URL)"
  if [ -n "$OLD_URL" ]; then
    # A release already exists (e.g. installed by hand with the chart defaults). Postgres only reads its
    # password on the very first start, so keep the old one - a new one would lock the backend out.
    PG_PW="$(echo "$OLD_URL" | sed -E 's#^[^:]+://[^:]+:([^@]*)@.*#\1#')"
    {
      echo "POSTGRES_PASSWORD=$PG_PW"
      echo "JWT_SECRET=$(existing JWT_SECRET)"
      echo "GRAFANA_ADMIN_PASSWORD=$(existing GRAFANA_ADMIN_PASSWORD)"
    } > "$SECRETS_FILE"
    echo "Re-used the secrets of the existing release -> $SECRETS_FILE"
  else
    {
      echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
      echo "JWT_SECRET=$(openssl rand -hex 32)"
      echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '/+=')"
    } > "$SECRETS_FILE"
    echo "Generated new secrets in $SECRETS_FILE"
  fi
fi
# shellcheck disable=SC1090
. "$SECRETS_FILE"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - >/dev/null

# --- Image location ------------------------------------------------------------------------------------
IMAGE_ARGS=()
if [ "$IMAGE_SOURCE" = "local" ]; then
  # Podman names local images "localhost/<name>"; k3s must be told the exact same name, or the pod fails
  # with ErrImageNeverPull ("pulseops-backend:demo" is resolved to docker.io/library/pulseops-backend:demo).
  PREFIX="${LOCAL_PREFIX:-localhost/}"
  IMAGE_ARGS+=(--set "frontend.image.repository=${PREFIX}pulseops-frontend" --set "frontend.image.pullPolicy=Never"
               --set "backend.image.repository=${PREFIX}pulseops-backend"   --set "backend.image.pullPolicy=Never")
else
  OWNER="$(echo "${GHCR_OWNER:?set GHCR_OWNER to your GitHub user/org}" | tr '[:upper:]' '[:lower:]')"
  IMAGE_ARGS+=(--set "frontend.image.repository=ghcr.io/${OWNER}/pulseops-frontend" --set "frontend.image.pullPolicy=IfNotPresent"
               --set "backend.image.repository=ghcr.io/${OWNER}/pulseops-backend"   --set "backend.image.pullPolicy=IfNotPresent")
  if [ -n "${GHCR_TOKEN:-}" ]; then
    kubectl -n "$NAMESPACE" create secret docker-registry ghcr-pull \
      --docker-server=ghcr.io --docker-username="${GHCR_USER:-$OWNER}" --docker-password="$GHCR_TOKEN" \
      --dry-run=client -o yaml | kubectl apply -f - >/dev/null
    IMAGE_ARGS+=(--set "imagePullSecrets[0].name=ghcr-pull")
  fi
fi

# --- Deploy: rolling update; --atomic = automatic rollback to the previous release if it doesn't come up --
echo "==> helm upgrade --install $RELEASE (tag $TAG)"
helm upgrade --install "$RELEASE" helm/pulseops \
  --namespace "$NAMESPACE" \
  -f "$VALUES" \
  ${EXTRA_VALUES:+-f "$EXTRA_VALUES"} \
  "${IMAGE_ARGS[@]}" \
  --set frontend.image.tag="$TAG" \
  --set backend.image.tag="$TAG" \
  --set postgres.password="$POSTGRES_PASSWORD" \
  --set secrets.jwtSecret="$JWT_SECRET" \
  --set secrets.grafanaAdminPassword="$GRAFANA_ADMIN_PASSWORD" \
  --atomic --wait --timeout "${HELM_TIMEOUT:-10m}"

# --- Smoke test through the Ingress (same path a browser takes) -----------------------------------------
echo "==> smoke test"
ok=0
for _ in $(seq 1 30); do
  fe=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/login || true)
  api=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/api/v1/auth/me || true)
  if [ "$fe" = "200" ] && [ "$api" = "401" ]; then ok=1; break; fi
  sleep 5
done
kubectl -n "$NAMESPACE" get pods -o wide
if [ "$ok" != 1 ]; then
  echo "Smoke test FAILED (frontend=$fe api=$api) - rolling back"
  helm rollback "$RELEASE" -n "$NAMESPACE" --wait || true
  exit 1
fi
helm history "$RELEASE" -n "$NAMESPACE" --max 5
echo "Deployed $TAG. Frontend /login=200, API /api/v1/auth/me=401 (auth required) -> healthy."
