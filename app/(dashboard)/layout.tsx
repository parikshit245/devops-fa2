import { Shell } from "@/components/dashboard/shell";
import { AuthGuard } from "@/components/auth-context";
export default function DashboardLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <AuthGuard><Shell>{children}</Shell></AuthGuard>; }
