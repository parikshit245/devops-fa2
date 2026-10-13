"use client";
import Link from "next/link";
import { Activity, ArrowLeft, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/dashboard/ui";
import { api } from "@/lib/api/client";
import { useAuth } from "@/components/auth-context";

export function AuthCard({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const { setUser } = useAuth();
  const isLogin = mode === "login";
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") ?? "");
    if (password.length < 8) return setError("Password must be at least 8 characters.");
    if (!isLogin && password !== data.get("confirm")) return setError("Passwords do not match.");
    setLoading(true);
    try {
      const result = isLogin
        ? await api.auth.login({ email: String(data.get("email")), password })
        : await api.auth.register({ name: String(data.get("name")), email: String(data.get("email")), password });
      setUser(result.user);
      router.push("/dashboard");
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Unable to complete the request."); }
    finally { setLoading(false); }
  }
  return <main className="flex min-h-screen bg-[#f6f8fb]"><div className="hidden w-[42%] flex-col justify-between bg-[#101b31] p-12 text-white lg:flex"><Link href="/" className="flex items-center gap-2.5 text-base font-semibold"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500"><Activity className="h-4 w-4" /></span>Pulse<span className="text-blue-400">Ops</span></Link><div><div className="mb-5 h-1 w-10 rounded bg-blue-400" /><h2 className="max-w-md text-4xl font-semibold leading-tight tracking-tight">Clarity when your systems matter most.</h2><p className="mt-5 max-w-sm text-sm leading-6 text-slate-400">Monitor health, trace deployments, and respond to incidents from one calm workspace.</p></div><p className="text-xs text-slate-500">© 2026 PulseOps</p></div><div className="flex flex-1 items-center justify-center p-6 sm:p-12"><div className="w-full max-w-[390px]"><Link href="/dashboard" className="mb-10 flex items-center gap-2 text-xs font-medium text-slate-500 hover:text-slate-800"><ArrowLeft className="h-3.5 w-3.5" />Back to overview</Link><div className="mb-8 lg:hidden"><Link href="/" className="flex items-center gap-2 text-base font-semibold text-slate-900"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white"><Activity className="h-4 w-4" /></span>Pulse<span className="text-blue-600">Ops</span></Link></div><h1 className="text-2xl font-semibold tracking-tight text-slate-950">{isLogin ? "Welcome back" : "Create your workspace"}</h1><p className="mt-2 text-sm text-slate-500">{isLogin ? "Sign in to continue to your reliability workspace." : "Set up your account to start monitoring your services."}</p><form onSubmit={submit} className="mt-7 space-y-4">{!isLogin && <label className="block text-xs font-semibold text-slate-700">Full name<input name="name" required className="mt-1.5 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-400" placeholder="Maya Chen" /></label>}<label className="block text-xs font-semibold text-slate-700">Email address<input name="email" type="email" required className="mt-1.5 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-400" placeholder="you@company.com" /></label><label className="block text-xs font-semibold text-slate-700">Password<div className="relative mt-1.5"><input name="password" type={show ? "text" : "password"} required className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 pr-10 text-sm outline-none focus:border-blue-400" placeholder="At least 8 characters" /><button type="button" aria-label="Toggle password visibility" onClick={() => setShow(!show)} className="absolute right-3 top-3 text-slate-400">{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></label>{!isLogin && <label className="block text-xs font-semibold text-slate-700">Confirm password<input name="confirm" type="password" required className="mt-1.5 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-400" placeholder="Repeat your password" /></label>}{isLogin && <label className="flex items-center gap-2 text-xs text-slate-500"><input type="checkbox" className="rounded border-slate-300" />Remember me</label>}{error && <p className="text-xs font-medium text-red-600">{error}</p>}<Button type="submit">{loading ? "Connecting..." : isLogin ? "Sign in" : "Create account"}</Button></form><p className="mt-7 text-center text-xs text-slate-500">{isLogin ? "New to PulseOps?" : "Already have an account?"} <Link href={isLogin ? "/register" : "/login"} className="font-semibold text-blue-600 hover:text-blue-700">{isLogin ? "Create an account" : "Sign in"}</Link></p></div></div></main>;
}
