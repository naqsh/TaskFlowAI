import Link from "next/link";

import type { Project } from "@/lib/projects";
import { Badge } from "@/components/ui/badge";

export function ProjectCard({
  project,
  overdueCount,
}: {
  project: Project;
  overdueCount: number;
}) {
  return (
    <article className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">{project.name}</h2>
          {project.description ? (
            <p className="mt-2 line-clamp-3 text-sm text-zinc-600 dark:text-zinc-400">
              {project.description}
            </p>
          ) : null}
        </div>
        {overdueCount > 0 ? (
          <Badge variant="destructive">{overdueCount} overdue</Badge>
        ) : (
          <Badge variant="secondary">No overdue</Badge>
        )}
      </div>

      <div className="mt-4">
        <Link
          href={`/projects/${project.id}`}
          className="text-sm font-medium text-taskflow-primary hover:underline"
        >
          View tasks
        </Link>
      </div>
    </article>
  );
}

