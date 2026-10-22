"""Generates the Grafana dashboards in helm/pulseops/files/grafana/.

Run:  python monitoring/generate_dashboards.py
The JSON files are provisioned into Grafana by the Helm chart (Kubernetes) and by compose.yaml (local Podman).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "helm" / "pulseops" / "files" / "grafana"
DS = {"type": "prometheus", "uid": "prometheus"}
GREEN, YELLOW, RED, BLUE = "green", "#EAB839", "red", "blue"


class Board:
    def __init__(self):
        self.panels, self.y, self.next_id = [], 0, 1

    def _id(self):
        self.next_id += 1
        return self.next_id - 1

    def row(self, title):
        self.panels.append({"type": "row", "title": title, "collapsed": False, "id": self._id(),
                            "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.y}, "panels": []})
        self.y += 1

    def add(self, panels, h):
        x = 0
        for p, w in panels:
            p["id"] = self._id()
            p["gridPos"] = {"h": h, "w": w, "x": x, "y": self.y}
            p.setdefault("datasource", DS)
            self.panels.append(p)
            x += w
        self.y += h


def target(expr, legend="", instant=False, fmt=None):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": "A", "range": not instant, "instant": instant}
    if fmt:
        t["format"] = fmt
    return t


def refs(targets):
    for i, t in enumerate(targets):
        t["refId"] = chr(ord("A") + i)
    return targets


def thresholds(*steps):
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for c, v in steps]}


def stat(title, expr, unit="short", steps=((GREEN, None),), desc="", decimals=None, mappings=None, color_mode="background"):
    d = {"unit": unit, "thresholds": thresholds(*steps), "color": {"mode": "thresholds"}}
    if decimals is not None:
        d["decimals"] = decimals
    if mappings:
        d["mappings"] = mappings
    return {"type": "stat", "title": title, "description": desc, "targets": [target(expr, instant=True)],
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"colorMode": color_mode, "graphMode": "none", "justifyMode": "center", "textMode": "value",
                        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}}}


def ts(title, targets, unit="short", desc="", stack=False, steps=None, minv=None, maxv=None, fill=10, show_thr=False):
    d = {"unit": unit, "custom": {"drawStyle": "line", "lineWidth": 2, "fillOpacity": fill, "showPoints": "never",
                                  "spanNulls": True, "stacking": {"mode": "normal" if stack else "none"},
                                  "thresholdsStyle": {"mode": "line+area" if show_thr else "off"}},
         "color": {"mode": "palette-classic"}}
    if steps:
        d["thresholds"] = thresholds(*steps)
    if minv is not None:
        d["min"] = minv
    if maxv is not None:
        d["max"] = maxv
    return {"type": "timeseries", "title": title, "description": desc, "targets": refs(targets),
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull", "max"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}}}


def dashboard(uid, title, board, tags, templating=None, links=None):
    return {"uid": uid, "title": title, "tags": tags, "timezone": "browser", "schemaVersion": 39, "version": 1,
            "editable": True, "graphTooltip": 1, "refresh": "30s", "time": {"from": "now-1h", "to": "now"},
            "timepicker": {"refresh_intervals": ["10s", "30s", "1m", "5m"]}, "fiscalYearStartMonth": 0,
            "annotations": {"list": [{"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                                      "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)",
                                      "name": "Annotations & Alerts", "type": "dashboard"}]},
            "links": links or [], "templating": {"list": templating or []}, "panels": board.panels}


UP_MAP = [{"type": "value", "options": {"0": {"text": "DOWN", "color": RED}, "1": {"text": "UP", "color": GREEN}}},
          {"type": "special", "options": {"match": "null", "result": {"text": "NO DATA", "color": "gray"}}}]
ERR = 'pulseops_http_requests_total{status=~"5.."}'
ALL = "pulseops_http_requests_total"


def sre_overview():
    b = Board()
    b.row("Service Level Objectives  (SLO: 99% of requests succeed, 95% faster than 500 ms)")
    b.add([
        (stat("Backend", 'max(up{job="pulseops-backend"})', mappings=UP_MAP,
              steps=((RED, None), (GREEN, 1)), desc="Is Prometheus able to scrape the FastAPI backend?"), 3),
        (stat("Availability SLI (time range)",
              f"1 - ((sum(increase({ERR}[$__range])) or vector(0)) / sum(increase({ALL}[$__range])))",
              unit="percentunit", decimals=3, steps=((RED, None), (YELLOW, 0.99), (GREEN, 0.995)),
              desc="Share of API requests that did NOT return 5xx over the selected time range. SLO = 99%."), 4),
        (stat("Error budget remaining",
              f"1 - (((sum(increase({ERR}[$__range])) or vector(0)) / sum(increase({ALL}[$__range]))) / 0.01)",
              unit="percentunit", decimals=1, steps=((RED, None), (YELLOW, 0.25), (GREEN, 0.5)),
              desc="Budget = 1% of requests may fail. 100% = nothing used, 0% or below = SLO violated."), 4),
        (stat("Latency SLI (< 500 ms)",
              'sum(increase(pulseops_http_request_duration_seconds_bucket{le="0.5"}[$__range])) / sum(increase(pulseops_http_request_duration_seconds_count[$__range]))',
              unit="percentunit", decimals=2, steps=((RED, None), (YELLOW, 0.95), (GREEN, 0.99)),
              desc="Share of requests served under 500 ms. SLO = 95%."), 4),
        (stat("p95 latency (5m)", "pulseops:http_latency_seconds:p95_5m", unit="s", decimals=3,
              steps=((GREEN, None), (YELLOW, 0.25), (RED, 0.5))), 3),
        (stat("Burn rate (1h)", "pulseops:error_budget_burn_rate:1h", decimals=2,
              steps=((GREEN, None), (YELLOW, 1), (RED, 14.4)),
              desc="1 = consuming budget exactly at the sustainable pace. >14.4 pages the on-call (fast burn)."), 3),
        (stat("Firing alerts", 'count(ALERTS{alertstate="firing"}) or vector(0)',
              steps=((GREEN, None), (RED, 1))), 3),
    ], h=5)

    b.row("Golden signals — PulseOps API (traffic · errors · latency · saturation)")
    b.add([
        (ts("Traffic: requests per second by route",
            [target(f"sum by (route) (rate({ALL}[$__rate_interval]))", "{{route}}")], unit="reqps"), 12),
        (ts("Errors: 5xx ratio vs SLO threshold",
            [target("pulseops:sli_errors:ratio_rate5m", "5xx ratio (5m)"),
             target("pulseops:sli_errors:ratio_rate1h", "5xx ratio (1h)")],
            unit="percentunit", minv=0, steps=((GREEN, None), (RED, 0.01)), show_thr=True,
            desc="Red area = above the 1% error budget."), 12),
    ], h=8)
    b.add([
        (ts("Latency percentiles",
            [target(f"histogram_quantile({q}, sum by (le) (rate(pulseops_http_request_duration_seconds_bucket[$__rate_interval])))", f"p{int(q*100)}")
             for q in (0.5, 0.95, 0.99)], unit="s", steps=((GREEN, None), (RED, 0.5)), show_thr=True), 8),
        (ts("Responses by status code",
            [target(f"sum by (status) (rate({ALL}[$__rate_interval]))", "{{status}}")], unit="reqps", stack=True), 8),
        (ts("Saturation: in-flight requests & backend memory",
            [target("sum(pulseops_http_requests_in_progress)", "in-flight requests"),
             target('process_resident_memory_bytes{job="pulseops-backend"} / 1024 / 1024', "backend RSS (MiB)")]), 8),
    ], h=8)
    b.add([
        (ts("Error budget burn rate",
            [target("pulseops:error_budget_burn_rate:5m", "5m window"),
             target("pulseops:error_budget_burn_rate:1h", "1h window")],
            steps=((GREEN, None), (YELLOW, 6), (RED, 14.4)), show_thr=True, minv=0,
            desc="Multi-window burn rate. Fast-burn alert fires when both windows exceed 14.4."), 12),
        (ts("Slowest routes (p95)",
            [target("topk(5, histogram_quantile(0.95, sum by (le, route) (rate(pulseops_http_request_duration_seconds_bucket[$__rate_interval]))))", "{{route}}")],
            unit="s"), 12),
    ], h=8)

    b.row("Synthetic monitoring — websites registered in PulseOps")
    b.add([
        ({"type": "state-timeline", "title": "Monitored service status (up/down timeline)",
          "targets": [target("max by (service_name) (pulseops_service_up)", "{{service_name}}")],
          "fieldConfig": {"defaults": {"mappings": UP_MAP, "thresholds": thresholds((RED, None), (GREEN, 1)),
                                       "color": {"mode": "thresholds"}, "custom": {"fillOpacity": 80, "lineWidth": 0}},
                          "overrides": []},
          "options": {"showValue": "auto", "mergeValues": True, "alignValue": "center", "rowHeight": 0.8,
                      "legend": {"showLegend": False}, "tooltip": {"mode": "single"}}}, 12),
        ({"type": "bargauge", "title": "Services by status",
          "targets": [target("sum by (status) (pulseops_monitored_services)", "{{status}}", instant=True)],
          "fieldConfig": {"defaults": {"unit": "short", "min": 0, "color": {"mode": "thresholds"},
                                       "thresholds": thresholds((BLUE, None))},
                          "overrides": [{"matcher": {"id": "byName", "options": n},
                                         "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": c}}]}
                                        for n, c in (("operational", GREEN), ("degraded", YELLOW), ("down", RED))]},
          "options": {"displayMode": "gradient", "orientation": "horizontal", "showUnfilled": True,
                      "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}}}, 6),
        (stat("Check success rate (1h)",
              '(sum(increase(pulseops_monitoring_checks_total{outcome="success"}[1h])) or vector(0)) / sum(increase(pulseops_monitoring_checks_total[1h]))',
              unit="percentunit", decimals=1, steps=((RED, None), (YELLOW, 0.9), (GREEN, 0.99))), 6),
    ], h=7)
    b.add([
        (ts("Monitored service response time",
            [target("max by (service_name) (pulseops_service_response_seconds)", "{{service_name}}")], unit="s"), 12),
        (ts("Health checks per minute by outcome",
            [target("sum by (outcome) (rate(pulseops_monitoring_checks_total[$__rate_interval])) * 60", "{{outcome}}")],
            unit="short", stack=True), 12),
    ], h=8)

    b.row("Incidents — alerts currently firing (Prometheus rules)")
    b.add([
        ({"type": "table", "title": "Firing / pending alerts",
          "targets": [target('ALERTS{alertstate=~"firing|pending"}', instant=True, fmt="table")],
          "fieldConfig": {"defaults": {"custom": {"align": "auto"}},
                          "overrides": [{"matcher": {"id": "byName", "options": "severity"},
                                         "properties": [{"id": "custom.cellOptions", "value": {"type": "color-text"}},
                                                        {"id": "mappings", "value": [{"type": "value", "options": {
                                                            "critical": {"color": RED}, "warning": {"color": YELLOW}}}]}]}]},
          "transformations": [{"id": "organize", "options": {
              "excludeByName": {"Time": True, "Value": True, "__name__": True, "cluster": True},
              "indexByName": {"alertname": 0, "severity": 1, "alertstate": 2}}}],
          "options": {"showHeader": True, "cellHeight": "sm"}}, 24),
    ], h=7)
    return dashboard("pulseops-sre-overview", "PulseOps — SRE Overview (SLOs & Golden Signals)", b,
                     ["pulseops", "sre", "slo"],
                     links=[{"title": "Cluster & Node resources", "type": "link", "url": "/d/pulseops-infra", "icon": "dashboard"}])


def infra():
    b = Board()
    ns_var = {"name": "namespace", "label": "Namespace", "type": "query", "datasource": DS,
              "query": {"query": "label_values(container_memory_working_set_bytes, namespace)", "refId": "ns"},
              "definition": "label_values(container_memory_working_set_bytes, namespace)",
              "current": {"text": "pulseops", "value": "pulseops"}, "refresh": 2, "includeAll": True,
              "multi": False, "sort": 1}
    mem_used = "1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)"
    b.row("EC2 node (node-exporter)")
    b.add([
        (stat("CPU used", '1 - avg(rate(node_cpu_seconds_total{mode="idle"}[$__rate_interval]))', unit="percentunit",
              decimals=1, steps=((GREEN, None), (YELLOW, 0.7), (RED, 0.9))), 4),
        (stat("Memory used", mem_used, unit="percentunit", decimals=1, steps=((GREEN, None), (YELLOW, 0.8), (RED, 0.9))), 4),
        (stat("RAM available", "node_memory_MemAvailable_bytes", unit="bytes", decimals=0,
              steps=((RED, None), (YELLOW, 150 * 2**20), (GREEN, 300 * 2**20))), 4),
        (stat("Swap used", "node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes", unit="bytes", decimals=0,
              steps=((GREEN, None), (YELLOW, 512 * 2**20), (RED, 1536 * 2**20)),
              desc="On a 1 GiB instance some swap usage is expected; heavy swap = slow pods."), 4),
        (stat("Root disk used",
              '1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}',
              unit="percentunit", decimals=1, steps=((GREEN, None), (YELLOW, 0.75), (RED, 0.9))), 4),
        (stat("Uptime", "time() - node_boot_time_seconds", unit="s", decimals=0, color_mode="value",
              steps=((BLUE, None),)), 4),
    ], h=4)
    b.add([
        (ts("CPU usage by mode",
            [target('sum by (mode) (rate(node_cpu_seconds_total{mode!="idle"}[$__rate_interval])) / scalar(count(node_cpu_seconds_total{mode="idle"}))', "{{mode}}")],
            unit="percentunit", stack=True, minv=0), 8),
        (ts("Memory",
            [target("node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes", "used"),
             target("node_memory_MemAvailable_bytes", "available"),
             target("node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes", "swap used")], unit="bytes"), 8),
        (ts("Load average & memory pressure (PSI)",
            [target("node_load1", "load 1m"), target("node_load5", "load 5m"),
             target("rate(node_pressure_memory_waiting_seconds_total[$__rate_interval])", "memory stall (s/s)")]), 8),
    ], h=8)
    b.add([
        (ts("Network traffic",
            [target("sum(rate(node_network_receive_bytes_total[$__rate_interval]))", "receive"),
             target("-sum(rate(node_network_transmit_bytes_total[$__rate_interval]))", "transmit")], unit="Bps"), 12),
        (ts("Disk I/O",
            [target("sum(rate(node_disk_read_bytes_total[$__rate_interval]))", "read"),
             target("sum(rate(node_disk_written_bytes_total[$__rate_interval]))", "write")], unit="Bps"), 12),
    ], h=7)

    b.row("Kubernetes pods (kubelet cAdvisor) — namespace: $namespace")
    sel = 'namespace=~"$namespace", container!=""'
    b.add([
        (ts("Memory working set by pod",
            [target(f"sum by (pod) (container_memory_working_set_bytes{{{sel}}})", "{{pod}}")], unit="bytes", stack=True), 12),
        (ts("CPU by pod",
            [target(f"sum by (pod) (rate(container_cpu_usage_seconds_total{{{sel}}}[$__rate_interval]))", "{{pod}}")],
            unit="short", stack=True, desc="CPU cores used (1 = one full vCPU)."), 12),
    ], h=8)
    b.add([
        ({"type": "bargauge", "title": "Memory used vs limit (per container)",
          "targets": [target(f"max by (pod, container) (container_memory_working_set_bytes{{{sel}}}) / on (pod, container) max by (pod, container) (container_spec_memory_limit_bytes{{{sel}}} > 0)",
                             "{{container}}", instant=True)],
          "fieldConfig": {"defaults": {"unit": "percentunit", "min": 0, "max": 1, "color": {"mode": "thresholds"},
                                       "thresholds": thresholds((GREEN, None), (YELLOW, 0.75), (RED, 0.9))}, "overrides": []},
          "options": {"displayMode": "lcd", "orientation": "horizontal", "showUnfilled": True,
                      "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}}}, 12),
        (ts("CPU throttling (limit reached)",
            [target(f"sum by (pod) (rate(container_cpu_cfs_throttled_periods_total{{{sel}}}[$__rate_interval])) / sum by (pod) (rate(container_cpu_cfs_periods_total{{{sel}}}[$__rate_interval]))", "{{pod}}")],
            unit="percentunit", minv=0), 12),
    ], h=8)

    b.row("Prometheus scrape health")
    b.add([
        ({"type": "table", "title": "Scrape targets",
          "targets": refs([target("up", instant=True, fmt="table"),
                           target("scrape_duration_seconds", instant=True, fmt="table"),
                           target("scrape_samples_scraped", instant=True, fmt="table")]),
          "transformations": [{"id": "merge", "options": {}},
                              {"id": "organize", "options": {"excludeByName": {"Time": True, "cluster": True},
                                                             "renameByName": {"Value #A": "up", "Value #B": "scrape seconds",
                                                                              "Value #C": "samples"}}}],
          "fieldConfig": {"defaults": {}, "overrides": [
              {"matcher": {"id": "byName", "options": "up"},
               "properties": [{"id": "mappings", "value": UP_MAP}, {"id": "custom.cellOptions", "value": {"type": "color-background"}}]}]},
          "options": {"showHeader": True, "cellHeight": "sm"}}, 14),
        (ts("Prometheus memory & active series",
            [target('process_resident_memory_bytes{job="prometheus"} / 1024 / 1024', "Prometheus RSS (MiB)"),
             target("prometheus_tsdb_head_series / 100", "head series (x100)")]), 10),
    ], h=8)
    return dashboard("pulseops-infra", "PulseOps — Cluster & Node Resources", b, ["pulseops", "kubernetes", "node"],
                     templating=[ns_var],
                     links=[{"title": "SRE Overview", "type": "link", "url": "/d/pulseops-sre-overview", "icon": "dashboard"}])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, board in (("pulseops-sre-overview.json", sre_overview()), ("pulseops-infra.json", infra())):
        (OUT / name).write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")
        print("wrote", OUT / name, len(board["panels"]), "panels")
