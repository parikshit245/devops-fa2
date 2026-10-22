# PulseOps

PulseOps is a deployment and reliability monitoring foundation with a Next.js frontend and a FastAPI/PostgreSQL backend.

## Frontend

```bash
pnpm install
pnpm dev
```

Set `NEXT_PUBLIC_API_BASE_URL` in the root `.env.local` when the backend is not running at `http://localhost:8000`.

## Backend

Python 3.12+ is recommended. Python 3.13 was used for local validation.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with a real PostgreSQL DATABASE_URL and a random JWT_SECRET.
$env:PYTHONPATH = "."
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

For the easiest local setup, the checked-out `backend/.env` uses a local SQLite file and requires no database credentials. `DATABASE_URL` also accepts standard PostgreSQL URLs (`postgresql://`, `postgres://`) and normalizes them for `asyncpg`; Neon and other hosted PostgreSQL providers work without provider-specific code. Do not place real credentials in `.env.example`, source files, or frontend `NEXT_PUBLIC_*` variables.

## API

- `GET /` and `GET /health` — safe liveness responses
- `GET /health/database` — authenticated-free database connectivity check
- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`
- Authenticated service CRUD under `/api/v1/services`
- Authenticated deployment list/create/detail under `/api/v1/deployments`
- Authenticated incident list/create/detail/update under `/api/v1/incidents`
- `POST /api/v1/services/{service_id}/check` performs a real bounded check.
- `GET /api/v1/services/{service_id}/checks` returns bounded persisted history.
- `GET /api/v1/services/{service_id}/analytics` returns check-based uptime and latency summaries.
- `/metrics` exposes low-cardinality Prometheus application metrics for API traffic, service checks, and monitored-service status.

Authentication uses a short-lived JWT in an HttpOnly cookie. CORS origins are configured through `ALLOWED_ORIGINS`; credentialed wildcard origins are not enabled.

## Tests

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests -q
pnpm lint
pnpm build
```

Backend tests use an isolated SQLite database. Local development can use SQLite without credentials; production deployments should use PostgreSQL.

## Frontend routes

- `/login` and `/register` — real backend auth forms
- `/dashboard` — authenticated, account-specific overview metrics
- `/services` — authenticated service management backed by the API
- `/deployments` — deployment history demo view
- `/incidents` — incident workflow demo view
- `/analytics` — check-based availability and latency summaries from the backend

The shared API boundary is [lib/api/client.ts](./lib/api/client.ts). Dashboard and analytics views use recorded service checks; the analytics history represents sampled health checks, not application request traffic.

## Podman local environment

Prerequisites: Podman Desktop with a Podman machine running and a Compose provider installed. On Windows, create a machine once with `podman machine init` if needed, then start it from Podman Desktop or run `podman machine start`. Verify `podman info` and `podman compose version` first. Podman's Compose command needs an external provider such as `podman-compose` available on `PATH`; install/configure one if the command reports that no provider is available.

```powershell
podman machine start
Copy-Item .env.example .env
podman compose build
podman compose up -d db
podman compose ps
podman compose run --rm backend alembic upgrade head
podman compose up -d backend frontend
```

Open `http://localhost:3005`. The browser-facing frontend API URL is `http://localhost:8000`; `backend` is only a Podman-network hostname and is not used by browser JavaScript. The backend listens on port `8000`, the frontend is published on host port `3005` (container port `3000`), and PostgreSQL stays private on the Compose network.

Useful commands:

```powershell
podman compose logs -f backend
podman compose logs -f frontend
podman compose ps
podman compose down
podman compose run --rm backend alembic current
podman compose build --no-cache
podman compose down -v # intentionally deletes the local PostgreSQL volume
```

The named `pulseops-db-data` volume preserves PostgreSQL data across normal `podman compose down` and container restarts. Use `down -v` only when intentionally resetting the local data. Compose uses one backend process because the monitoring scheduler is single-instance; do not scale it horizontally until distributed scheduling is added.

Build versioned images locally with:

```powershell
podman build -t pulseops-frontend:0.1.0 .
podman build -t pulseops-backend:0.1.0 -f backend/Dockerfile .
```

The frontend `NEXT_PUBLIC_API_BASE_URL` is embedded during the Next.js image build. For a different browser-reachable backend address, set it in `.env` before `podman compose build`. Backend secrets are runtime environment variables and are not copied into either image. The GitHub Actions workflow still uses Docker-compatible Buildx on GitHub-hosted runners; it does not depend on Podman Desktop installed on your computer.

## Monitoring behavior

Monitoring defaults to a 60-second interval, a 5-second timeout, and expected HTTP status `200`. The single-process scheduler reloads enabled services from the database and prevents overlapping checks for the same service. A service is marked degraded after one failed check and down after two consecutive failed checks; an automatic outage incident is created once and resolved on recovery. Check-based uptime is `successful checks / completed checks * 100`, so it is an estimate of sampled availability rather than every second of uptime. History is bounded to recent API windows; retention cleanup should be scheduled as an explicit database maintenance job later.

Only public HTTP/HTTPS endpoints are accepted. URLs with embedded credentials, loopback/private/link-local/reserved/multicast destinations, metadata hostnames, redirects, and unresolved hosts are blocked. DNS rebinding cannot be eliminated completely in a single request process; revalidation and an isolated worker/network policy should be added before exposing monitoring to untrusted users.

The scheduler is intentionally single-instance. Multiple backend replicas would need a distributed lock or dedicated worker to avoid duplicate checks.

## Kubernetes and EC2 deployment

See **[KUBERNETES.md](./KUBERNETES.md)**: one free-tier EC2 instance running single-node k3s, with the Helm chart in [helm/pulseops](./helm/pulseops) (frontend, backend, PostgreSQL, Prometheus, Grafana, node-exporter). The short version:

```bash
bash scripts/ec2-setup.sh                         # once: swap + k3s + helm
GHCR_OWNER=<github-user> bash scripts/deploy.sh latest   # helm --atomic rolling update + smoke test
```

Keep `backend.replicaCount: 1` (enforced by the chart schema), because the monitoring scheduler is process-local.

## Monitoring, observability and SRE

See **[MONITORING.md](./MONITORING.md)**: Prometheus metrics, SLI/SLO recording rules, multi-window burn-rate alerts (unit-tested with `promtool`), two provisioned Grafana dashboards (SRE overview and cluster/node resources), a traffic generator, an incident drill (`scripts/simulate-incident.sh`) and a blameless [post-mortem template](./docs/POSTMORTEM.md). For a local version: `podman compose --profile monitoring up -d`.

## GitHub Actions CI/CD

`.github/workflows/pulseops.yml` (Build → Test → Scan → Package → Deploy):

| Job | What it does |
|---|---|
| `test` | `pnpm lint` + `pnpm build`, `pytest`, Grafana dashboards up to date, `helm lint`/`template`, **kubeconform** schema validation, **promtool** rule checks + unit tests |
| `security` (DevSecOps) | **Bandit** SAST (fails on HIGH), **Trivy** secret scan (fails if a credential is committed), dependency scan and IaC misconfiguration scan (reports) |
| `publish-images` | Builds both images with Buildx (layer cache), pushes `ghcr.io/<owner>/pulseops-*:<sha>` and `:latest`, then Trivy-scans the images |
| `deploy` (opt-in) | Copies the chart to EC2 over SSH, runs `scripts/deploy.sh <sha>` (`helm --atomic`: rolling update, automatic rollback), then an external smoke test |

To enable deploy, set repository variable `PULSEOPS_DEPLOY=true` and these secrets (on the `production` environment): `EC2_HOST` (public IP), `EC2_USER` (`ubuntu`), `EC2_SSH_KEY` (the .pem contents), and optionally `GHCR_READ_TOKEN` (only if the GHCR packages are private). The frontend image is built with an empty `NEXT_PUBLIC_API_BASE_URL`, so it calls `/api` on whatever host serves it.
