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
- `/metrics` exposes low-cardinality Prometheus application metrics.

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
- `/analytics` — explicitly labelled demo metrics

The shared API boundary is [lib/api/client.ts](./lib/api/client.ts). Authentication is connected to the backend; the operational dashboard widgets still contain the Prompt 1 mock flows and should be migrated endpoint-by-endpoint next.

## Docker local environment

Prerequisites: Docker Desktop with Compose v2.

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d db
docker compose ps
docker compose run --rm backend alembic upgrade head
docker compose up -d backend frontend
```

Open `http://localhost:3000`. The browser-facing frontend API URL is `http://localhost:8000`; `backend` is only a Docker-network hostname and is not used by browser JavaScript. The backend listens on port `8000`, the frontend on port `3000`, and PostgreSQL stays private on the Compose network.

Useful commands:

```powershell
docker compose logs -f backend
docker compose logs -f frontend
docker compose ps
docker compose down
docker compose run --rm backend alembic current
docker compose build --no-cache
docker compose down -v # intentionally deletes the local PostgreSQL volume
```

The named `pulseops-db-data` volume preserves PostgreSQL data across normal `docker compose down` and container restarts. Use `down -v` only when intentionally resetting local data. Compose uses one backend process because the monitoring scheduler is single-instance; do not scale it horizontally until distributed scheduling is added.

Build versioned images locally with:

```powershell
docker build -t pulseops-frontend:0.1.0 .
docker build -t pulseops-backend:0.1.0 -f backend/Dockerfile .
```

The frontend `NEXT_PUBLIC_API_BASE_URL` is embedded during the Next.js image build. For a different browser-reachable backend address, set it in `.env` before `docker compose build`. Backend secrets are runtime environment variables and are not copied into either image.

## Monitoring behavior

Monitoring defaults to a 60-second interval, a 5-second timeout, and expected HTTP status `200`. The single-process scheduler reloads enabled services from the database and prevents overlapping checks for the same service. A service is marked degraded after one failed check and down after two consecutive failed checks; an automatic outage incident is created once and resolved on recovery. Check-based uptime is `successful checks / completed checks * 100`, so it is an estimate of sampled availability rather than every second of uptime. History is bounded to recent API windows; retention cleanup should be scheduled as an explicit database maintenance job later.

Only public HTTP/HTTPS endpoints are accepted. URLs with embedded credentials, loopback/private/link-local/reserved/multicast destinations, metadata hostnames, redirects, and unresolved hosts are blocked. DNS rebinding cannot be eliminated completely in a single request process; revalidation and an isolated worker/network policy should be added before exposing monitoring to untrusted users.

The scheduler is intentionally single-instance. Multiple backend replicas would need a distributed lock or dedicated worker to avoid duplicate checks.

## Kubernetes and EC2 deployment

The reusable chart under [helm/pulseops](./helm/pulseops) supports the simple flow in [KUBERNETES.md](./KUBERNETES.md): one Ubuntu EC2 instance, single-node k3s, local Docker images imported into k3s, PostgreSQL inside Kubernetes, one PVC, and one Helm release. No Docker Hub or managed database is required. The chart creates intentionally demo-only credentials by default; use an external Secret and `postgres.enabled: false` for a real deployment.

Keep `backend.replicaCount: 1` because monitoring is process-local. This single-EC2/single-backend architecture is for learning and demonstration, not high availability. Helm and kubectl were not installed in the local Windows workspace, so chart linting, rendering, and real-cluster tests remain to be run on the k3s host.
