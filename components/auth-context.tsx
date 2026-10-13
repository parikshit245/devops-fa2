"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";

type User = { id: string; name: string; email: string };
const AuthContext = createContext<{ user: User | null; loading: boolean; setUser: (user: User) => void; logout: () => Promise<void> }>({ user: null, loading: true, setUser: () => {}, logout: async () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.auth.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  async function logout() { await api.auth.logout(); setUser(null); }
  return <AuthContext.Provider value={{ user, loading, setUser, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() { return useContext(AuthContext); }

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, loading } = useAuth();
  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  if (loading || !user) return <div className="flex min-h-screen items-center justify-center bg-[#f6f8fb] text-sm text-slate-500">Loading your workspace...</div>;
  return children;
}
