# PulseOps simple Kubernetes demo

This guide deploys PulseOps on one Ubuntu AWS EC2 instance running single-node k3s. The frontend, backend, and PostgreSQL all run in Kubernetes. This is intentionally a learning/demo setup, not production architecture.

```text
Internet -> EC2 port 80 -> k3s Traefik Ingress
                         -> frontend and backend Services
                         -> PostgreSQL Service -> one PVC
```

## 1. Create the EC2 host

Launch Ubuntu 22.04 or 24.04 LTS. Configure the security group with:

- TCP 22 from your current IP only
- TCP 80 from the internet
- Optional TCP 443
- Do not expose 3000, 5432, 6443, or 8000

SSH into the instance, then install Docker, k3s, and Helm using their current official instructions:

```bash
curl -sfL https://get.docker.com | sh
curl -sfL https://get.k3s.io | sh -
sudo kubectl get nodes
sudo systemctl status k3s
helm version
sudo chmod 600 /etc/rancher/k3s/k3s.yaml
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

k3s includes Traefik by default. Confirm it with `sudo kubectl get pods -n kube-system`.

## 2. Clone and build locally

Build on EC2 so no Docker Hub account is needed. Replace the public IP:

```bash
git clone YOUR_REPOSITORY_URL
cd FA-2-Project
docker build --build-arg NEXT_PUBLIC_API_BASE_URL="http://YOUR_EC2_PUBLIC_IP" -t pulseops-frontend:demo .
docker build -t pulseops-backend:demo -f backend/Dockerfile .
docker save pulseops-frontend:demo | sudo k3s ctr images import -
docker save pulseops-backend:demo | sudo k3s ctr images import -
```

`NEXT_PUBLIC_API_BASE_URL` is embedded into the frontend image during its build. Rebuild that image if the public URL changes.

## 3. Install with Helm

The chart creates a demo PostgreSQL Deployment, ClusterIP Service, 5 GiB PVC, and application Secret. The demo credentials are `pulseops`/`pulseops` and must not be reused for a real deployment.

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
sudo kubectl -n pulseops rollout status deployment/pulseops-pulseops-postgres
sudo kubectl -n pulseops rollout status deployment/pulseops-pulseops-backend
sudo kubectl -n pulseops rollout status deployment/pulseops-pulseops-frontend
sudo kubectl -n pulseops logs job/pulseops-pulseops-migrations
curl -i http://YOUR_EC2_PUBLIC_IP/
```

Open `http://YOUR_EC2_PUBLIC_IP` in a browser, register an account, create a service, and view its monitoring status.

## 5. Upgrade, rollback, and reset

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

For a real deployment, disable the chart PostgreSQL (`postgres.enabled: false`), provide an external Secret with `DATABASE_URL` and `JWT_SECRET`, use a real domain/HTTPS, and use a registry rather than `imagePullPolicy: Never`.
