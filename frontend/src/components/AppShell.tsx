import { Link, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import {
  MessageSquare,
  ShieldAlert,
  Wrench,
  Lightbulb,
  Share2,
} from "lucide-react";
import { HealthIndicator } from "./HealthIndicator";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Copilot", icon: MessageSquare },
  { to: "/compliance", label: "Compliance", icon: ShieldAlert },
  { to: "/rca", label: "RCA", icon: Wrench },
  { to: "/lessons", label: "Lessons", icon: Lightbulb },
  { to: "/graph", label: "Graph", icon: Share2 },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="flex min-h-dvh w-full bg-background text-foreground">
      {/* Desktop rail */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface md:flex">
        <div className="flex h-16 items-center gap-2 border-b border-border px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary font-bold text-primary-foreground">
            S
          </div>
          <div>
            <p className="text-sm font-semibold leading-none">SETU</p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Ops intelligence
            </p>
          </div>
        </div>
        <nav className="flex-1 p-2">
          {nav.map((item) => {
            const active =
              item.to === "/"
                ? pathname === "/"
                : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-border p-3">
          <HealthIndicator />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-surface/60 px-4 backdrop-blur md:h-16 md:px-6">
          <div className="flex items-center gap-2 md:hidden">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
              S
            </div>
            <span className="text-sm font-semibold">SETU</span>
          </div>
          <div className="hidden md:block" />
          <div className="md:hidden">
            <HealthIndicator />
          </div>
          <div className="hidden md:block">
            <HealthIndicator />
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto pb-20 md:pb-0">
          {children}
        </main>
      </div>

      {/* Mobile bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-surface/95 backdrop-blur md:hidden">
        {nav.map((item) => {
          const active =
            item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex flex-col items-center justify-center gap-0.5 py-2 text-[11px]",
                active ? "text-primary" : "text-muted-foreground",
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
