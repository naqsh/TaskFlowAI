"use client";

import { useEmailNotificationsPrefs } from "@/hooks/useEmailNotificationsPrefs";

export default function PreferencesPage() {
  const prefsQuery = useEmailNotificationsPrefs();

  return (
    <main className="mx-auto w-full max-w-2xl px-6 py-10">
      <h1 className="text-2xl font-semibold">Preferences</h1>

      <section className="mt-6 rounded-2xl border border-black/10 p-6 dark:border-white/10">
        <h2 className="text-sm font-semibold">Email notifications</h2>

        <label className="mt-4 flex items-center gap-3">
          <input
            type="checkbox"
            checked={prefsQuery.emailNotificationsEnabled}
            onChange={(e) => prefsQuery.update.mutate(e.target.checked)}
            disabled={prefsQuery.isLoading}
          />
          <span className="text-sm text-zinc-700 dark:text-zinc-300">
            Send transactional emails for task collaboration (assignment, reminders)
          </span>
        </label>

        {prefsQuery.update.isError ? (
          <p className="mt-3 text-sm text-red-600">Failed to save preference.</p>
        ) : null}
      </section>
    </main>
  );
}

