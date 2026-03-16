import type { Application, ApplicationStatus } from "@/types/application";
import ApplicationCard from "./ApplicationCard";

interface Props {
  label: string;
  headerColor: string;
  statuses: ApplicationStatus[];
  applications: Application[];
  onUpdate: () => void;
}

export default function ApplicationColumn({
  label,
  headerColor,
  applications,
  onUpdate,
}: Props) {
  return (
    <div className="flex flex-col min-w-[260px] w-full">
      {/* En-tête colonne */}
      <div
        className={`border-t-4 ${headerColor} bg-white rounded-t-lg px-4 py-3 flex items-center justify-between`}
      >
        <h2 className="font-semibold text-sm text-gray-700">{label}</h2>
        <span className="text-xs bg-gray-100 text-gray-500 rounded-full px-2 py-0.5 font-medium">
          {applications.length}
        </span>
      </div>

      {/* Cartes */}
      <div className="flex flex-col gap-3 bg-gray-50 rounded-b-lg p-3 min-h-[120px]">
        {applications.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-4">Aucune candidature</p>
        ) : (
          applications.map((app) => (
            <ApplicationCard key={app.id} application={app} onUpdate={onUpdate} />
          ))
        )}
      </div>
    </div>
  );
}
