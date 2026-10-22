# Monitoring, Observability and SRE (Unit IV)

## What is deployed

| Component | Runs as | Purpose |
|---|---|---|
| **Prometheus** v2.55 | Deployment + PVC (3-day / 500 MB retention on micro) | Scrapes metrics every 30 s, evaluates SLI recording rules and alert rules |
| **Grafana** v11.4 | Deployment + PVC | Dashboards, auto-provisioned from `helm/pulseops/files/grafana/*.json` |
| **node-exporter** | DaemonSet (host network) | EC2 host metrics: CPU, memory, **swap**, disk, network, pressure |
| **kubelet cAdvisor** | built into k3s, scraped via the API-server proxy (read-only RBAC) | Per-pod CPU / memory / OOM / throttling |
| **PulseOps backend `/metrics`** | `prometheus_client` in FastAPI | Golden signals + synthetic-check results |

Everything is "monitoring as code": scrape config, rules and dashboards live in Git, are unit-tested in CI (`promtool test rules`), and are deployed by Helm.

## The three pillars of observability

| Pillar | In this project |
|---|---|
| **Metrics** | Prometheus + Grafana (below). This is the main part of the assessment. |
| **Logs** | Uvicorn/FastAPI, Postgres, Prometheus and Grafana log to stdout, and the container runtime collects them centrally per pod: `kubectl -n pulseops logs deploy/pulseops-pulseops-backend [-c migrations] [--previous]`. The full ELK stack is **not** deployed, because Elasticsearch alone needs 1–2 GiB of heap, more than the whole free-tier instance. The lightweight "or similar" option is Grafana Loki plus a log agent (about 150 MiB), which makes logs searchable in the same Grafana. It fits on a `t3.small`/`c7i-flex.large`. |
| **Traces** | Not instrumented. The next step would be OpenTelemetry auto-instrumentation for FastAPI (`opentelemetry-instrument uvicorn ...`) sending to Grafana Tempo or Jaeger. |

## Metrics exposed by the backend

| Metric | Type | Golden signal |
|---|---|---|
| `pulseops_http_requests_total{method,route,status}` | Counter | Traffic, Errors |
| `pulseops_http_request_duration_seconds_bucket{method,route,le}` | Histogram | Latency |
| `pulseops_http_requests_in_progress` | Gauge | Saturation |
| `process_resident_memory_bytes` | Gauge | Saturation |
| `pulseops_monitoring_checks_total{outcome}` | Counter | Synthetic monitoring |
| `pulseops_service_up{service_id,service_name}` / `pulseops_service_response_seconds` | Gauge | Per monitored website |
| `pulseops_monitored_services{status}` | Gauge | Services operational / degraded / down |
| `pulseops_build_info{version,commit}` | Info | Which build is running |

Routes are recorded as templates (`/api/v1/services/{service_id}`), not raw URLs, so label cardinality stays low.

## SLI / SLO / SLA

| | Definition |
|---|---|
| **SLI** (indicator: what we measure) | **Availability SLI** = non-5xx requests / all requests. **Latency SLI** = requests served in < 500 ms / all requests. Both are Prometheus recording rules: `pulseops:sli_availability:ratio_rate5m`, `pulseops:sli_latency_good:ratio_rate5m`. |
| **SLO** (objective: our internal target) | **99 %** of requests succeed over 30 days, and **95 %** of requests are faster than 500 ms. |
| **Error budget** | 100 % − 99 % = **1 %** of requests may fail. Grafana shows "Error budget remaining" and the **burn rate** (1 = spending the budget exactly at the sustainable pace). |
| **SLA** (agreement: a promise to users, with a penalty) | Example: "99 % monthly availability, or 10 % service credit". The SLA is deliberately looser than the SLO, so we get warned (SLO breach) before we owe anyone (SLA breach). |

### Alerting (multi-window, multi-burn-rate, from the Google SRE Workbook)

| Alert | Fires when | Severity |
|---|---|---|
| `PulseOpsErrorBudgetFastBurn` | 5xx ratio > 14.4 % over both 1 h and 5 m (2 % of the monthly budget gone in 1 h) | critical (page) |
| `PulseOpsErrorBudgetSlowBurn` | 5xx ratio > 6 % over both 6 h and 30 m | warning (ticket) |
| `PulseOpsHighLatency` | p95 > 500 ms for 10 m | warning |
| `PulseOpsBackendDown` / `PulseOpsBackendMissing` | scrape fails / no backend pod found | critical |
| `PulseOpsDatabaseUnhealthy` | `/health/database` (the readiness probe) returns 5xx | critical |
| `MonitoredServiceDown` | a website registered in PulseOps fails its checks for 2 m | warning |
| `NodeMemoryPressure`, `NodeDiskAlmostFull`, `ContainerNearMemoryLimit`, `ContainerOOMKilled`, `PrometheusTargetDown` | saturation of the EC2 node / pods | warning |

Alerts are visible in Prometheus (`/alerts`) and in the "Firing alerts" panel and table on the SRE dashboard. Sending them to email or Slack would need Alertmanager (not deployed, to save memory).

## Dashboards

1. **PulseOps — SRE Overview** (the home dashboard): SLO stat row (availability SLI, error budget remaining, latency SLI, p95, burn rate, firing alerts), the four golden signals, the burn-rate graph, slowest routes, a state timeline of the monitored websites, and a table of firing alerts.
2. **PulseOps — Cluster & Node Resources**: EC2 CPU / memory / swap / disk / network / PSI pressure, per-pod memory and CPU, memory used vs limit (predicts OOMKills), CPU throttling, and scrape health.

To change a dashboard, edit `monitoring/generate_dashboards.py`, run `python monitoring/generate_dashboards.py`, and commit both. CI fails if the JSON is out of date.

## Demo script (for the evaluation)

```bash
# 1. Traffic, so the graphs move (run from your laptop or the EC2 box)
DURATION=300 ./scripts/generate-traffic.sh http://EC2_PUBLIC_IP
#    → registers a user, adds a healthy site and a broken one (404 → MonitoredServiceDown fires)

# 2. Incident drill: take the database down for 4 minutes
./scripts/simulate-incident.sh
#    → /health/database 5xx → PulseOpsDatabaseUnhealthy (critical) within ~2 min,
#      backend pod goes NotReady (Kubernetes stops sending it traffic) but is still scraped,
#      error ratio and burn rate spike on the SRE dashboard, then everything recovers.

# 3. Write the post-mortem from the timestamps the script printed: docs/POSTMORTEM.md
```

## Incident management process

1. **Detect**: an alert fires (Prometheus rule), or a user reports a problem.
2. **Triage**: check the SRE dashboard. Which SLI is burning, since when, and which route or pod?
3. **Mitigate first, debug later**: roll back (`helm rollback`), scale, or restart. Restoring service matters more than finding the root cause.
4. **Communicate**: one incident owner, status updates at fixed intervals.
5. **Resolve**: SLIs are back within the SLO and alerts have cleared.
6. **Post-mortem**: blameless, within 48 h, using `docs/POSTMORTEM.md`. Each action item gets an owner and a due date.

## Local (Podman Desktop) version, without AWS

```powershell
podman compose --profile monitoring up -d --build
# App http://localhost:3005 · Prometheus http://localhost:9090 · Grafana http://localhost:3300 (admin / pulseops-local-only)
```
Same rules and the same dashboards. The node and pod panels stay empty locally, because there's no node-exporter or kubelet.
