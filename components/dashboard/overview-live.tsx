"use client";

import { useEffect, useState } from "react";
import { Activity, Gauge } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, ServiceAnalytics } from "@/lib/api/client";
import { Service } from "@/types";
import { Card, CardHeader, EmptyState, PageTitle, StatusDot } from "./ui";

type OverviewData = { services: Service[]; incidents: Array<{ id: string }> ; analytics: ServiceAnalytics[] };

export function LiveOverviewPage() {
  const [data, setData] = useState<OverviewData>({ services: [], incidents: [], analytics: [] });
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([api.services.list(), api.incidents.list()])
      .then(async ([services, incidents]) => {
        const analytics = await Promise.all(services.map((service) => api.services.analytics(service.id, 1)));
        if (active) setData({ services, incidents, analytics });
      })
      .catch(() => { if (active) setError("Live overview data could not be loaded. Check the API connection and retry."); })
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, []);

  const totalChecks = data.analytics.reduce((sum, summary) => sum + summary.total_checks, 0);
  const successfulChecks = data.analytics.reduce((sum, summary) => sum + summary.successful_checks, 0);
  const uptime = totalChecks ? `${((successfulChecks / totalChecks) * 100).toFixed(2)}%` : "—";
  const responseValues = data.services.map((service) => service.responseTime).filter((value) => value > 0);
  const averageResponse = responseValues.length ? `${Math.round(responseValues.reduce((sum, value) => sum + value, 0) / responseValues.length)} ms` : "—";
  const responsePoints = data.analytics.flatMap((summary) => summary.checks.filter((check) => check.response_ms !== null).map((check) => ({ timestamp: new Date(check.checked_at).getTime(), time: new Date(check.checked_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), value: check.response_ms as number }))).sort((left, right) => left.timestamp - right.timestamp).slice(-100);
  const operational = data.services.filter((service) => service.status === "operational").length;
  const attention = data.services.filter((service) => service.status === "degraded" || service.status === "down").length;

  return <>
    <PageTitle eyebrow="Workspace" title="Your reliability overview" description="Live data from the services and incidents in your account." />
    {error && <p role="alert" className="mb-4 text-sm text-red-700">{error}</p>}
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card className="p-5"><div className="flex items-start justify-between"><div><p className="text-xs font-medium text-slate-500">Check-based uptime</p><p className="mt-2 text-2xl font-semibold text-slate-950">{loaded ? uptime : "Loading..."}</p><p className="mt-2 text-[11px] text-slate-500">{totalChecks} checks in the last 24 hours</p></div><Activity className="h-4 w-4 text-blue-600" /></div></Card>
      <Card className="p-5"><div><p className="text-xs font-medium text-slate-500">Monitored services</p><p className="mt-2 text-2xl font-semibold text-slate-950">{loaded ? data.services.length : "..."}</p><p className="mt-2 text-[11px] text-slate-500">{operational} operational · {attention} need attention</p></div></Card>
      <Card className="p-5"><div className="flex items-start justify-between"><div><p className="text-xs font-medium text-slate-500">Avg. latest response</p><p className="mt-2 text-2xl font-semibold text-slate-950">{averageResponse}</p><p className="mt-2 text-[11px] text-slate-500">Across services with a recorded response</p></div><Gauge className="h-4 w-4 text-emerald-600" /></div></Card>
      <Card className="p-5"><div><p className="text-xs font-medium text-slate-500">Active incidents</p><p className="mt-2 text-2xl font-semibold text-slate-950">{loaded ? data.incidents.length : "..."}</p><p className="mt-2 text-[11px] text-slate-500">Owned by your workspace</p></div></Card>
    </div>
    <div className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_1fr]">
      <Card><CardHeader title="Response time" subtitle="Recorded health-check responses over the last 24 hours" /><div className="p-4">{responsePoints.length ? <ResponsiveContainer width="100%" height={260}><AreaChart data={responsePoints} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}><defs><linearGradient id="liveResponseFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3978f6" stopOpacity={0.18} /><stop offset="100%" stopColor="#3978f6" stopOpacity={0} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf0f5" /><XAxis dataKey="time" tick={{ fontSize: 11, fill: "#98a2b3" }} tickLine={false} axisLine={false} interval="preserveStartEnd" /><YAxis tick={{ fontSize: 11, fill: "#98a2b3" }} tickLine={false} axisLine={false} tickFormatter={(value) => `${value}ms`} /><Tooltip formatter={(value) => [`${value} ms`, "Response time"]} /><Area type="monotone" dataKey="value" stroke="#3978f6" strokeWidth={2} fill="url(#liveResponseFill)" /></AreaChart></ResponsiveContainer> : <p className="py-16 text-center text-sm text-slate-500">{loaded ? "No response-time samples recorded yet." : "Loading recorded checks..."}</p>}</div></Card>
      <Card><CardHeader title="Service health" subtitle="Current status across your workspace" /><div className="divide-y divide-slate-100">{loaded && data.services.length === 0 ? <EmptyState title="No services yet" description="Add your first service to start collecting health data." /> : data.services.slice(0, 5).map((service) => <div key={service.id} className="flex items-center justify-between px-5 py-3.5"><div className="flex min-w-0 items-center gap-3"><StatusDot status={service.status} /><div className="min-w-0"><p className="truncate text-xs font-semibold text-slate-800">{service.name}</p><p className="mt-0.5 truncate text-[11px] text-slate-400">{service.url}</p></div></div><div className="text-right"><p className="text-xs font-semibold text-slate-700">{service.responseTime ? `${service.responseTime} ms` : "Not checked"}</p></div></div>)}</div></Card>
    </div>
  </>;
}