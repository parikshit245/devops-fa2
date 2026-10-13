import { Deployment, Incident, Service } from "@/types";

export const services: Service[] = [
  { id: "svc-api", name: "Core API", url: "api.pulseops.dev", environment: "Production", status: "operational", uptime: 99.99, responseTime: 118, lastChecked: "12 sec ago", team: "Platform" },
  { id: "svc-web", name: "Web application", url: "app.pulseops.dev", environment: "Production", status: "operational", uptime: 99.97, responseTime: 243, lastChecked: "18 sec ago", team: "Product" },
  { id: "svc-worker", name: "Event processor", url: "worker.pulseops.dev", environment: "Production", status: "degraded", uptime: 99.72, responseTime: 481, lastChecked: "22 sec ago", team: "Platform" },
  { id: "svc-checkout", name: "Checkout service", url: "checkout.pulseops.dev", environment: "Production", status: "operational", uptime: 99.95, responseTime: 186, lastChecked: "31 sec ago", team: "Payments" },
  { id: "svc-docs", name: "Documentation", url: "docs.pulseops.dev", environment: "Staging", status: "down", uptime: 97.84, responseTime: 0, lastChecked: "2 min ago", team: "Developer Experience" },
  { id: "svc-auth", name: "Identity service", url: "auth.pulseops.dev", environment: "Production", status: "operational", uptime: 99.99, responseTime: 92, lastChecked: "14 sec ago", team: "Security" },
];

export const deployments: Deployment[] = [
  { id: "dep-8f42c1", service: "Core API", environment: "Production", branch: "main", commit: "8f42c1d", time: "Today, 10:42 AM", status: "success", author: "Maya Chen", duration: "3m 18s" },
  { id: "dep-7aa920", service: "Event processor", environment: "Production", branch: "main", commit: "7aa920f", time: "Today, 09:18 AM", status: "success", author: "Jordan Lee", duration: "4m 02s" },
  { id: "dep-6b10af", service: "Web application", environment: "Production", branch: "release/2.4", commit: "6b10af4", time: "Yesterday, 6:31 PM", status: "failed", author: "Maya Chen", duration: "1m 44s" },
  { id: "dep-4cc82e", service: "Checkout service", environment: "Staging", branch: "feat/receipts", commit: "4cc82e1", time: "Yesterday, 4:09 PM", status: "in_progress", author: "Sam Rivera", duration: "—" },
  { id: "dep-2c881a", service: "Identity service", environment: "Production", branch: "main", commit: "2c881a0", time: "Mon, 11:12 AM", status: "success", author: "Priya Shah", duration: "2m 27s" },
];

export const incidents: Incident[] = [
  { id: "inc-1042", title: "Documentation site unavailable", service: "Documentation", severity: "major", status: "open", created: "12 min ago", updates: [{ time: "12 min ago", text: "Synthetic checks report a 100% failure rate.", type: "alert" }, { time: "8 min ago", text: "On-call engineer has been paged.", type: "person" }] },
  { id: "inc-1041", title: "Elevated event processing latency", service: "Event processor", severity: "minor", status: "investigating", created: "1h 24m ago", updates: [{ time: "1h 24m ago", text: "P95 latency crossed the 400ms threshold.", type: "alert" }, { time: "48 min ago", text: "Investigating queue depth in us-east-1.", type: "person" }] },
  { id: "inc-1039", title: "Checkout timeouts", service: "Checkout service", severity: "critical", status: "resolved", created: "Yesterday, 2:14 PM", resolved: "Yesterday, 2:42 PM", updates: [{ time: "Yesterday, 2:14 PM", text: "Timeout rate reached 3.2% for checkout requests.", type: "alert" }, { time: "Yesterday, 2:42 PM", text: "Rolled back deployment dep-6b10af.", type: "check" }] },
  { id: "inc-1037", title: "Brief API latency spike", service: "Core API", severity: "minor", status: "resolved", created: "Mon, 9:02 AM", resolved: "Mon, 9:09 AM", updates: [{ time: "Mon, 9:02 AM", text: "P99 response time exceeded 1 second.", type: "alert" }, { time: "Mon, 9:09 AM", text: "Latency returned to baseline.", type: "check" }] },
];

export const responseTime = [142, 155, 148, 163, 177, 168, 182, 175, 194, 187, 201, 193, 211, 198, 224, 216, 208, 232, 219, 244, 226, 238, 221, 243];
export const chartLabels = ["12 AM", "2 AM", "4 AM", "6 AM", "8 AM", "10 AM", "12 PM", "2 PM", "4 PM", "6 PM", "8 PM", "10 PM"];
