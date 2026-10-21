# PulseOps simple Kubernetes demo

This guide deploys PulseOps on one Ubuntu AWS EC2 instance running single-node k3s. The frontend, backend, and PostgreSQL all run in Kubernetes. This is intentionally a learning/demo setup, not production architecture.

```text
Internet -> EC2 port 80 -> k3s Traefik Ingress
                         -> frontend and backend Services
                         -> PostgreSQL Service -> one PVC
```

## 1. Create the EC2 host

Launch Ubuntu 22.04, 24.04, or 26.04 LTS. Configure the security group with:

- TCP 22 from your current IP only
- TCP 80 from the internet
- Optional TCP 443
- Do not expose 3000, 5432, 6443, or 8000

SSH into the instance, then install Podman, k3s, and Helm:

```bash
sudo apt-get update
sudo apt-get install -y podman
curl -sfL https://get.k3s.io | sh -
sudo snap install helm --classic
podman --version
sudo kubectl get nodes
sudo systemctl status k3s
helm version
sudo chmod 600 /etc/rancher/k3s/k3s.yaml
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

k3s includes Traefik by default. Confirm it with `sudo kubectl get pods -n kube-system`.

## 2. Clone and build locally

Build on EC2 with Podman so you can import the images directly into k3s without publishing them to a registry. Replace the public IP:

```bash
git clone YOUR_REPOSITORY_URL
cd FA-2-Project
podman build --build-arg NEXT_PUBLIC_API_BASE_URL="http://YOUR_EC2_PUBLIC_IP" -t pulseops-frontend:demo .
podman build -t pulseops-backend:demo -f backend/Dockerfile .
podman save --format docker-archive pulseops-frontend:demo | sudo k3s ctr images import -
podman save --format docker-archive pulseops-backend:demo | sudo k3s ctr images import -
```

`NEXT_PUBLIC_API_BASE_URL` is embedded into the frontend image during its build. Rebuild that image if the public URL changes.

## 3. Install with Helm

The chart creates a demo PostgreSQL Deployment, Prometheus, Grafana, persistent volumes, and application Secrets. Prometheus scrapes the backend `/metrics` endpoint, and Grafana provisions a PulseOps dashboard. Default credentials are for local learning only; change them before deployment.

```bash
helm lint helm/pulseops
helm upgrade --install pulseops helm/pulseops \
  --namespace pulseops --create-namespace \
  --set frontend.image.repository=pulseops-frontend \
  --set frontend.image.tag=demo \
  --set frontend.image.pullPolicy=Never \
  --set backend.image.repository=pulseops-backend \
  --set backend.image.tag=demo \
  --set backend.image.pullPolicy=Never \
  --set ingress.host=YOUR_EC2_PUBLIC_IP \
  --set config.allowedOrigins=http://YOUR_EC2_PUBLIC_IP \
  --wait --timeout 10m
```

The migration Job waits for PostgreSQL with `pg_isready` and then runs `alembic upgrade head`. The backend stays at one replica because its monitoring scheduler is process-local.

## 4. Verify and use it

```bash
sudo kubectl -n pulseops get pods,svc,pvc,ingress,jobs
curl -i http://YOUR_EC2_PUBLIC_IP/
```

Open `http://YOUR_EC2_PUBLIC_IP` in a browser, register an account, create a service, and view its monitoring status.

## 5. Open the metrics tools

Prometheus and Grafana use ClusterIP Services and are not exposed through the public Ingress. Open separate terminal sessions and port-forward them:

```bash
sudo kubectl -n pulseops port-forward svc/pulseops-pulseops-prometheus 9090:9090
sudo kubectl -n pulseops port-forward svc/pulseops-pulseops-grafana 3000:3000
```

Visit `http://localhost:9090/targets` to verify the backend scrape, then visit `http://localhost:3000` and sign in as `admin` using the chart's configured Grafana password. Change the demo password in `helm/pulseops/values.yaml` before deploying outside a local exercise.

## 6. Upgrade, rollback, and reset

```bash
helm upgrade pulseops helm/pulseops -n pulseops --reuse-values --wait
helm history pulseops -n pulseops
helm rollback pulseops REVISION -n pulseops --wait
helm uninstall pulseops -n pulseops
```

The PVC is retained after uninstall. Delete it only when intentionally resetting the demo database:

```bash
sudo kubectl delete pvc pulseops-pulseops-postgres -n pulseops
```

For a real deployment, disable the chart PostgreSQL (`postgres.enabled: false`), provide an external Secret with `DATABASE_URL`, `JWT_SECRET`, and `GRAFANA_ADMIN_PASSWORD`, use a real domain/HTTPS, and use a registry rather than `imagePullPolicy: Never`.
