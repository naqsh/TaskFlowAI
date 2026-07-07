"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, fetchHealth, getApiBase } from "@/lib/api";

type BackendStatus = "loading" | "connected" | "error" | "unconfigured";

export function DashboardShell() {
  const apiBase = getApiBase();
  const isUnconfigured = apiBase.length === 0;
  const [backendStatus, setBackendStatus] = useState<BackendStatus>(
    isUnconfigured ? "unconfigured" : "loading",
  );
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    if (isUnconfigured) {
      return;
    }

    let cancelled = false;

    async function checkBackend() {
      try {
        const health = await fetchHealth();
        if (!cancelled) {
          setVersion(health.version);
          setBackendStatus("connected");
        }
      } catch (error) {
        if (!cancelled) {
          setBackendStatus("error");
          if (error instanceof ApiError && error.status === 401) {
            console.error("Unexpected 401 on public health endpoint");
          }
        }
      }
    }

    void checkBackend();
    return () => {
      cancelled = true;
    };
  }, [isUnconfigured]);

  return (
    <main className="mx-auto flex min-h-full w-full max-w-5xl flex-col gap-8 px-6 py-16">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-taskflow-primary">
            TaskFlow AI
          </p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight text-foreground">
            Dashboard
          </h1>
          <p className="mt-2 max-w-xl text-base text-zinc-600 dark:text-zinc-400">
            Enterprise task management — MVP 1. Auth is live; projects and tasks ship in
            TF-008+.
          </p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/login"
              className="rounded-lg border border-black/10 px-3 py-1.5 text-sm font-medium hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/5"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-taskflow-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-taskflow-primary/90"
            >
              Register
            </Link>
          </div>
          <span
            className="rounded-full border border-black/10 px-3 py-1 text-xs font-medium dark:border-white/15"
            aria-live="polite"
          >
            v0.1.0 scaffold
          </span>
        </div>
      </header>

      {isUnconfigured ? (
        <div
          role="alert"
          className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
        >
          Set <code className="font-mono">NEXT_PUBLIC_API_URL</code> in{" "}
          <code className="font-mono">frontend/.env.local</code> (e.g.{" "}
          <code className="font-mono">http://localhost:8010</code>).
        </div>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-3">
        <article className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
          <h2 className="text-sm font-medium text-zinc-500">Backend</h2>
          <p className="mt-2 text-2xl font-semibold capitalize">{backendStatus}</p>
          {version ? (
            <p className="mt-1 text-sm text-zinc-500">API version {version}</p>
          ) : null}
        </article>
        <article className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
          <h2 className="text-sm font-medium text-zinc-500">Projects</h2>
          <p className="mt-2 text-2xl font-semibold">—</p>
          <p className="mt-1 text-sm text-zinc-500">TF-008</p>
        </article>
        <article className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
          <h2 className="text-sm font-medium text-zinc-500">Tasks</h2>
          <p className="mt-2 text-2xl font-semibold">—</p>
          <p className="mt-1 text-sm text-zinc-500">TF-010</p>
        </article>
      </section>

      <section className="rounded-2xl border border-dashed border-black/15 p-8 dark:border-white/15">
        <h2 className="text-lg font-semibold">Getting started</h2>
        <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-zinc-600 dark:text-zinc-400">
          <li>
            Start backend:{" "}
            <code className="font-mono">
              uv run uvicorn backend.main:app --port 8010
            </code>
          </li>
          <li>
            Configure <code className="font-mono">NEXT_PUBLIC_API_URL</code> and refresh
          </li>
          <li>Continue TF-007 (RBAC) through TF-010 (dashboard UI)</li>
        </ol>
      </section>
    </main>
  );
}
