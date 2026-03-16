"use client";

import type { Application } from "@/types/application";
import { KANBAN_COLUMNS } from "@/types/application";
import ApplicationColumn from "./ApplicationColumn";

interface Props {
  applications: Application[];
  onUpdate: () => void;
}

export default function ApplicationPipeline({ applications, onUpdate }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {KANBAN_COLUMNS.map((col) => {
        const colApps = applications.filter((a) =>
          (col.statuses as string[]).includes(a.status)
        );
        return (
          <ApplicationColumn
            key={col.id}
            label={col.label}
            headerColor={col.headerColor}
            statuses={col.statuses}
            applications={colApps}
            onUpdate={onUpdate}
          />
        );
      })}
    </div>
  );
}
