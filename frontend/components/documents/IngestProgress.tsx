"use client";

import { formatBytes } from "@/lib/format";
import type { IngestState } from "@/hooks/useWorkspace";

export function IngestProgress({ ingest }: { ingest: IngestState }) {
  const value = Math.max(0, Math.min(100, ingest.progress));
  return (
    <div className="w-full max-w-md">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <p className="truncate text-sm text-ink">{ingest.name}</p>
        <p className="shrink-0 text-xs text-muted">{ingest.error ? "Stopped" : `${Math.round(value)}%`}</p>
      </div>
      <div
        className="h-1.5 overflow-hidden rounded-full bg-[#f0f0f0]"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(value)}
        aria-label="Ingestion progress"
      >
        <div
          className="h-full rounded-full bg-ink transition-[width] duration-200 ease-linear"
          style={{ width: `${value}%` }}
        />
      </div>
      <p className={`mt-2 text-xs ${ingest.error ? "text-danger" : "text-muted"}`}>
        {ingest.error ?? (value >= 100 ? "Ready" : `Ingesting PDF · ${formatBytes(ingest.bytes)}`)}
      </p>
    </div>
  );
}
