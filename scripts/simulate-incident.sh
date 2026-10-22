#!/usr/bin/env bash
# Chaos drill for the SRE part of the demo: takes PostgreSQL down, lets alerts fire, then restores it.
#   ./scripts/simulate-incident.sh            (namespace/release default to pulseops)
# Watch:  Grafana "SRE Overview" (error ratio, burn rate, firing alerts)  and  Prometheus /alerts
set -euo pipefail
NS="${NS:-pulseops}"; RELEASE="${RELEASE:-pulseops}"; OUTAGE="${OUTAGE:-240}"
DB="deploy/${RELEASE}-pulseops-postgres"
KUBECTL="${KUBECTL:-kubectl}"

echo "[$(date +%T)] INCIDENT START: scaling $DB to 0 for ${OUTAGE}s"
$KUBECTL -n "$NS" scale "$DB" --replicas=0
echo "Expect within ~1-3 min: /health/database 5xx -> PulseOpsDatabaseUnhealthy, error ratio spike,"
echo "backend pod NotReady (still scraped directly via Kubernetes SD) and PulseOpsErrorBudgetFastBurn."
sleep "$OUTAGE"
echo "[$(date +%T)] MITIGATION: scaling $DB back to 1"
$KUBECTL -n "$NS" scale "$DB" --replicas=1
$KUBECTL -n "$NS" rollout status "$DB" --timeout=180s
echo "[$(date +%T)] RECOVERED. Fill in docs/POSTMORTEM.md using the timestamps above and the Grafana graphs."
