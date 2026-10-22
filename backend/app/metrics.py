import os
from prometheus_client import Counter, Gauge, Histogram, Info

# --- Golden signals for the PulseOps API itself (traffic, errors, latency) ---
http_requests_total = Counter("pulseops_http_requests_total", "HTTP requests", ["method", "route", "status"])
http_request_duration_seconds = Histogram(
    "pulseops_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
http_requests_in_progress = Gauge("pulseops_http_requests_in_progress", "HTTP requests currently being served")

# --- Synthetic monitoring of the user's registered services ---
monitoring_checks_total = Counter("pulseops_monitoring_checks_total", "Monitoring checks", ["outcome"])
monitoring_check_duration_seconds = Histogram("pulseops_monitoring_check_duration_seconds", "Monitoring check duration")
monitored_services = Gauge("pulseops_monitored_services", "Monitored services", ["status"])
# One series per monitored service (bounded by the number of services users register).
service_up = Gauge("pulseops_service_up", "1 if the last check of a monitored service succeeded, else 0", ["service_id", "service_name"])
service_response_seconds = Gauge("pulseops_service_response_seconds", "Response time of the last successful check", ["service_id", "service_name"])

build_info = Info("pulseops_build", "PulseOps build information")
build_info.info({"version": os.getenv("APP_VERSION", "dev"), "commit": os.getenv("GIT_SHA", "unknown")})


def forget_service(service_id: str, service_name: str) -> None:
    """Drop per-service series when a service is deleted so Grafana does not show ghosts."""
    for gauge in (service_up, service_response_seconds):
        try:
            gauge.remove(service_id, service_name)
        except KeyError:
            pass
