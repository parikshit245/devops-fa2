# PulseOps on Kubernetes (k3s on one free-tier EC2 instance)

```text
GitHub push ──► GitHub Actions: test ─► security scan ─► build images ─► push to GHCR ─► SSH deploy
                                                                                          │
Browser ──► EC2 :80 ──► Traefik Ingress ──┬─ /      ─► frontend (Next.js)                 ▼
                                          └─ /api/* ─► backend (FastAPI) ─► PostgreSQL (PVC)   helm upgrade --atomic
                                                          ▲ /metrics
            EC2 :30090 (your IP only) ─► Prometheus ──────┤◄─ node-exporter (EC2 host), kubelet cAdvisor (pods)
            EC2 :30300 (your IP only) ─► Grafana ◄── PromQL
```

Everything (app, database, Prometheus, Grafana) runs in **one single-node k3s cluster**. This is a learning/demo setup, not high availability.

## Why the first attempt didn't work

| Symptom you probably saw | Cause | Fix in this version |
|---|---|---|
| Pods stuck in `ErrImageNeverPull` | `podman build -t pulseops-backend:demo` really stores **`localhost/pulseops-backend:demo`**. The chart asked k3s for `pulseops-backend:demo`, which Kubernetes expands to `docker.io/library/pulseops-backend:demo`, so no such local image exists. | Images are built by GitHub Actions and pulled from GHCR. For local images, `deploy.sh` uses the `localhost/` prefix. |
| The EC2 box freezes / SSH hangs while building | `pnpm build` (Next.js) needs well over 1 GiB of RAM. | Never build on EC2. CI builds the images. |
| Pods `OOMKilled`, `CrashLoopBackOff` at random | No swap on a 1 GiB box. Postgres's default `shared_buffers=128MB` didn't fit its 128 Mi limit. The Grafana "micro" limits were accidentally nested under `ingress:` in `values-micro.yaml`, so they never applied. | `ec2-setup.sh` adds 2 GiB swap. Postgres is tuned (`shared_buffers=32MB`). `values-micro.yaml` is fixed. |
| `helm --wait` times out and the app returns 500 on register | Migrations ran as a **post-install hook**, which only runs *after* `--wait` succeeds. On a slow box the wait timed out first, so tables were never created. The Postgres liveness probe could also kill the very first `initdb`. | Migrations now run as an **init container** before the API starts. Postgres and the backend have **startup probes**. |
| Browser calls fail with CORS / cookie problems | The API URL was baked into the frontend image as an absolute URL. | The image is built with an empty API base, so the browser calls `/api/...` on the same host, and Traefik routes it to FastAPI. One image works for any IP. |

## 1. Create the EC2 instance

- **AMI:** Ubuntu 24.04 LTS (free tier eligible)
- **Instance type** (cheapest that works, in order of preference):
  - Accounts created **after 15 July 2025** (credit-based free plan): `t3.small` (2 GiB) is the sweet spot. `c7i-flex.large` (4 GiB) is very comfortable for the demo day. Both are free-tier eligible and consume credits, so **stop the instance when you're not using it**.
  - Older accounts: `t3.micro` / `t2.micro` (1 GiB). It works with swap, but it's slow; give the first deploy ~10 minutes.
- **Storage:** 20 GiB gp3 (the free tier includes 30 GiB).
- **Security group, inbound:**

| Port | Source | Why |
|---|---|---|
| 22 | your IP (plus `0.0.0.0/0` **only** if you enable the GitHub Actions deploy; key-only SSH) | SSH |
| 80 | `0.0.0.0/0` | the app |
| 30300 | **your IP only** | Grafana |
| 30090 | **your IP only** | Prometheus |

Never open 6443 (Kubernetes API), 5432, 8000 or 9100.

## 2. Install k3s, Helm and swap (once)

```bash
ssh -i your-key.pem ubuntu@EC2_PUBLIC_IP
git clone https://github.com/parikshit245/devops-fa2.git && cd devops-fa2
bash scripts/ec2-setup.sh          # swap + k3s (metrics-server disabled) + helm; re-runnable
```

## 3. Deploy

### Option A (recommended): images built by GitHub Actions
1. Push to `main`. The workflow publishes `ghcr.io/<owner>/pulseops-frontend:<sha>` and `pulseops-backend:<sha>`.
2. In GitHub → your profile → **Packages**, set both packages to **Public**. (Or keep them private and pass a `read:packages` token as `GHCR_TOKEN`.)
3. On EC2:
```bash
GHCR_OWNER=parikshit245 bash scripts/deploy.sh latest     # or a commit SHA
```

### Option B: build on your laptop with Podman (no registry)
```powershell
podman build --build-arg NEXT_PUBLIC_API_BASE_URL= -t pulseops-frontend:demo .
podman build -t pulseops-backend:demo -f backend/Dockerfile .
podman save -m -o pulseops-images.tar localhost/pulseops-frontend:demo localhost/pulseops-backend:demo
scp -i your-key.pem pulseops-images.tar ubuntu@EC2_PUBLIC_IP:~
```
```bash
sudo k3s ctr images import ~/pulseops-images.tar
sudo k3s ctr images ls | grep pulseops        # must show localhost/pulseops-...:demo
IMAGE_SOURCE=local bash scripts/deploy.sh demo
```

`deploy.sh` generates random DB/JWT/Grafana secrets once (`~/.pulseops-secrets.env`, never committed). It then runs `helm upgrade --install --atomic` (a rolling update with automatic rollback), smoke-tests `/login` (expects 200) and `/api/v1/auth/me` (expects 401), and rolls back if they fail.

> Installed the chart earlier with the defaults? `deploy.sh` re-uses the existing release's secrets automatically. To start completely fresh instead: `helm uninstall pulseops -n pulseops && kubectl -n pulseops delete pvc --all`.

## 4. Verify

```bash
kubectl -n pulseops get pods,svc,pvc,ingress
curl -i http://EC2_PUBLIC_IP/login
```
- App: `http://EC2_PUBLIC_IP/`. Register, add a service, and watch it get checked.
- Prometheus: `http://EC2_PUBLIC_IP:30090/targets` (all targets should show **UP**) and `/alerts`.
- Grafana: `http://EC2_PUBLIC_IP:30300` → user `admin`, password:
  `kubectl -n pulseops get secret pulseops-secrets -o jsonpath='{.data.GRAFANA_ADMIN_PASSWORD}' | base64 -d`

If you'd rather not open 30090/30300, use an SSH tunnel: `ssh -L 3000:localhost:30300 -L 9090:localhost:30090 ubuntu@EC2_PUBLIC_IP`.

## 5. Deployment strategy, upgrade, rollback

- **Rolling update** (`maxUnavailable: 0`, `maxSurge: 1`): the new pod must pass its readiness probe before the old one is removed, so there's zero downtime.
- **`--atomic`:** if the new release doesn't become healthy within the timeout, Helm rolls back by itself. This was tested by deploying a non-existent image tag: Helm marked revision 7 failed, rolled back to 6, and the app kept serving the whole time.
- Postgres, Prometheus and Grafana use **Recreate**, because each holds a ReadWriteOnce volume.

```bash
helm history pulseops -n pulseops
helm rollback pulseops <REVISION> -n pulseops --wait
```

## 6. Troubleshooting

```bash
kubectl -n pulseops get pods                         # look for Pending / CrashLoopBackOff / OOMKilled
kubectl -n pulseops describe pod <pod>               # Events section explains most problems
kubectl -n pulseops logs deploy/pulseops-pulseops-backend -c migrations   # schema migration output
kubectl -n pulseops logs deploy/pulseops-pulseops-backend
free -h; kubectl top 2>/dev/null || echo "(metrics-server disabled - use the Grafana infra dashboard)"
```
- `Pending` with `Insufficient memory`: the instance is too small. Add swap or use t3.small.
- `ErrImageNeverPull`: the image name in k3s doesn't match. Run `sudo k3s ctr images ls | grep pulseops`.
- `ImagePullBackOff` from GHCR: the package is private. Make it public or set `GHCR_TOKEN`.

## 7. Save your credits

```bash
aws ec2 stop-instances --instance-ids i-xxxx     # or Stop in the console; EBS data (DB, metrics) is kept
```
Note that the public IP changes after a stop/start unless you attach an Elastic IP. The app works with any IP; only the `EC2_HOST` GitHub secret needs updating.
