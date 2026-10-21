"use client";

import { useEffect, useState } from "react";
import { Activity, Clock3, Gauge } from "lucide-react";
import { api, ServiceAnalytics } from "@/lib/api/client";
import { Service } from "@/types";
import { Card, EmptyState, PageTitle } from "./ui";

type AnalyticsRow = { service: Service; analytics: ServiceAnalytics };

function formatPercent(value: number | null) {
  return value === null ? "No data" : `${value.toFixed(2)}%`;
}

function formatLatency(value: number | null) {
  return value === null ? "No data" : `${Math.round(value)} ms`;
}

export function LiveAnalyticsPage() {
  const [days, setDays] = useState(1);
  const [rows, setRows] = useState<AnalyticsRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api.services.list()
      .then(async (services) => Promise.all(services.map(async (service) => ({
        service,
        analytics: await api.services.analytics(service.id, days),
      }))))
      .then((result) => { if (active) setRows(result); })
      .catch(() => { if (active) setError("Analytics could not be loaded. Check the API connection and try again."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [days]);

  const totalChecks = rows.reduce((sum, row) => sum + row.analytics.total_checks, 0);
  const successfulChecks = rows.reduce((sum, row) => sum + row.analytics.successful_checks, 0);
  const uptime = totalChecks ? (successfulChecks / totalChecks) * 100 : null;
  const responseValues = rows.map((row) => row.analytics.average_response_ms).filter((value): value is number => value !== null);
  const averageResponse = responseValues.length ? responseValues.reduce((sum, value) => sum + value, 0) / responseValues.length : null;

  return <>
    <PageTitle eyebrow="Insights" title="Service analytics" description={`Recorded health checks over the last ${days} ${days === 1 ? "day" : "days"}.`} action={<div className="flex gap-1" role="group" aria-label="Analytics range">{[1, 7, 30].map((option) => <button key={option} type="button" aria-pressed={days === option} onClick={() => setDays(option)} className={`rounded-md px-3 py-2 text-xs font-semibold ${days === option ? "bg-slate-900 text-white" : "border border-slate-200 bg-white text-slate-600"}`}>{option}d</button>)}</div>} />
    <div className="mb-5 grid gap-4 sm:grid-cols-3">
      <Card className="p-5"><div className="flex items-center gap-3"><Activity className="h-4 w-4 text-blue-600" /><div><p className="text-xs text-slate-500">Check-based uptime</p><p className="mt-1 text-xl font-semibold text-slate-950">{formatPercent(uptime)}</p></div></div></Card>
      <Card className="p-5"><div className="flex items-center gap-3"><Gauge className="h-4 w-4 text-emerald-600" /><div><p className="text-xs text-slate-500">Completed checks</p><p className="mt-1 text-xl font-semibold text-slate-950">{totalChecks}</p></div></div></Card>
      <Card className="p-5"><div className="flex items-center gap-3"><Clock3 className="h-4 w-4 text-amber-600" /><div><p className="text-xs text-slate-500">Mean service response</p><p className="mt-1 text-xl font-semibold text-slate-950">{formatLatency(averageResponse)}</p></div></div></Card>
    </div>
    {error && <p role="alert" className="mb-4 text-sm text-red-700">{error}</p>}
    <Card>
      <div className="grid grid-cols-[minmax(0,1.5fr)_0.8fr_0.8fr_0.8fr] gap-4 border-b border-slate-100 px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-slate-400"><span>Service</span><span>Uptime</span><span>Checks</span><span>Mean latency</span></div>
      {loading ? <p className="px-5 py-8 text-sm text-slate-500">Loading recorded checks...</p> : rows.length === 0 ? <EmptyState title="No monitored services" description="Add a service and allow health checks to run to see its analytics." /> : rows.map(({ service, analytics }) => <div key={service.id} className="grid grid-cols-[minmax(0,1.5fr)_0.8fr_0.8fr_0.8fr] items-center gap-4 border-b border-slate-100 px-5 py-4 last:border-0">
        <div className="min-w-0"><p className="truncate text-xs font-semibold text-slate-800">{service.name}</p><p className="mt-1 truncate text-[11px] text-slate-400">{service.url}</p><div className="mt-2 h-1.5 overflow-hidden rounded bg-slate-100"><div className="h-full bg-emerald-500" style={{ width: `${Math.min(100, analytics.uptime_percent ?? 0)}%` }} /></div></div>
        <span className="text-xs font-semibold text-slate-700">{formatPercent(analytics.uptime_percent)}</span>
        <span className="text-xs text-slate-600">{analytics.total_checks}</span>
        <span className="text-xs text-slate-600">{formatLatency(analytics.average_response_ms)}</span>
      </div>)}
    </Card>
  </>;
}