export type ServiceStatus = "operational" | "degraded" | "down" | "unknown" | "paused";
export type DeploymentStatus = "success" | "failed" | "in_progress";
export type IncidentSeverity = "critical" | "major" | "minor";
export type IncidentStatus = "open" | "investigating" | "resolved";

export type Service = {
  id: string; name: string; url: string; environment: "Production" | "Staging" | "Development";
  status: ServiceStatus; uptime: number; responseTime: number; lastChecked: string; team: string;
};
export type Deployment = {
  id: string; service: string; environment: string; branch: string; commit: string;
  time: string; status: DeploymentStatus; author: string; duration: string;
};
export type Incident = {
  id: string; title: string; service: string; severity: IncidentSeverity;
  status: IncidentStatus; created: string; resolved?: string; updates: { time: string; text: string; type: string }[];
};
