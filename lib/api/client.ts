import type { Service } from "@/types";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
type ApiService = { id: string; name: string; description?: string | null; endpoint_url: string; environment: "production" | "staging" | "development"; status: Service["status"]; monitoring_enabled: boolean; last_check_at?: string | null; latest_response_ms?: number | null; created_at: string; updated_at: string };
function mapService(service: ApiService): Service { return { id: service.id, name: service.name, url: service.endpoint_url.replace(/^https?:\/\//, ""), environment: service.environment[0].toUpperCase() + service.environment.slice(1) as Service["environment"], status: service.status, uptime: 100, responseTime: service.latest_response_ms ?? 0, lastChecked: service.last_check_at ? new Date(service.last_check_at).toLocaleString() : "Not checked", team: "Unassigned" }; }
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { ...init, credentials: "include", headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.detail ?? "The request could not be completed.") as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export const api = {
  auth: {
    login: (payload: { email: string; password: string }) => request<{ user: { id: string; name: string; email: string } }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(payload) }),
    register: (payload: { name: string; email: string; password: string }) => request<{ user: { id: string; name: string; email: string } }>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(payload) }),
    me: () => request<{ id: string; name: string; email: string }>("/api/v1/auth/me"),
    logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  },
  services: {
    list: async () => (await request<ApiService[]>("/api/v1/services")).map(mapService),
    create: async (payload: Pick<Service, "name" | "url">) => mapService(await request<ApiService>("/api/v1/services", { method: "POST", body: JSON.stringify({ name: payload.name, endpoint_url: `https://${payload.url}`, environment: "production" }) })),
    update: async (id: string, payload: Partial<Service>) => mapService(await request<ApiService>(`/api/v1/services/${id}`, { method: "PATCH", body: JSON.stringify(payload) })),
    remove: (id: string) => request<void>(`/api/v1/services/${id}`, { method: "DELETE" }),
  },
  deployments: { list: () => request<Array<{ id: string; service_id: string; version: string; environment: string; branch?: string | null; commit_sha?: string | null; status: string; deployed_at?: string | null }>>("/api/v1/deployments") },
  incidents: { list: () => request<Array<{ id: string; service_id: string; title: string; severity: string; status: string; created_at: string; resolved_at?: string | null }>>("/api/v1/incidents") },
};
