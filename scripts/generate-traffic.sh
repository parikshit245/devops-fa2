#!/usr/bin/env bash
# Generates realistic API traffic so the Grafana dashboards have something to show.
#   ./scripts/generate-traffic.sh http://EC2_PUBLIC_IP          (Kubernetes / Ingress)
#   ./scripts/generate-traffic.sh http://localhost:8000          (local compose)
#   DURATION=300 ./scripts/generate-traffic.sh http://...        (seconds, default 120)
set -euo pipefail
BASE="${1:-http://localhost:8000}"
DURATION="${DURATION:-120}"
JAR="$(mktemp)"; trap 'rm -f "$JAR"' EXIT
EMAIL="loadtest-$(date +%s)@example.com"

echo "Registering $EMAIL against $BASE ..."
curl -fsS -c "$JAR" -H 'Content-Type: application/json' \
  -d "{\"name\":\"Load Test\",\"email\":\"$EMAIL\",\"password\":\"correct horse battery\"}" \
  "$BASE/api/v1/auth/register" > /dev/null

# Two real public sites to monitor (one healthy, one that returns 404 -> shows up as DOWN on the dashboard).
for site in "Example|https://example.com" "Broken page|https://example.com/this-page-does-not-exist"; do
  curl -fsS -b "$JAR" -H 'Content-Type: application/json' \
    -d "{\"name\":\"${site%%|*}\",\"endpoint_url\":\"${site##*|}\",\"environment\":\"production\"}" \
    "$BASE/api/v1/services" > /dev/null || true
done

echo "Sending traffic for ${DURATION}s (Ctrl+C to stop) ..."
END=$(( $(date +%s) + DURATION )); n=0
while [ "$(date +%s)" -lt "$END" ]; do
  curl -s -o /dev/null -b "$JAR" "$BASE/api/v1/services"
  curl -s -o /dev/null -b "$JAR" "$BASE/api/v1/incidents"
  curl -s -o /dev/null -b "$JAR" "$BASE/api/v1/auth/me"
  curl -s -o /dev/null "$BASE/api/v1/services"            # 401 (no cookie)
  curl -s -o /dev/null "$BASE/api/v1/does-not-exist"      # 404
  n=$((n + 5)); [ $((n % 100)) -eq 0 ] && echo "  $n requests sent"
  sleep 0.2
done
echo "Done: $n requests."
