from prometheus_client import Counter, Gauge, Histogram

http_requests_total = Counter("pulseops_http_requests_total", "HTTP requests", ["method", "route", "status"])
http_request_duration_seconds = Histogram("pulseops_http_request_duration_seconds", "HTTP request duration", ["method", "route"])
monitoring_checks_total = Counter("pulseops_monitoring_checks_total", "Monitoring checks", ["outcome"])
monitoring_check_duration_seconds = Histogram("pulseops_monitoring_check_duration_seconds", "Monitoring check duration")
monitored_services = Gauge("pulseops_monitored_services", "Monitored services", ["status"])
