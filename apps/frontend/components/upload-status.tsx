"use client";

import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UploadState } from "@/types/upload";

interface UploadStatusProps {
  state: UploadState;
}

export function UploadStatus({ state }: UploadStatusProps) {
  if (state.status === "idle") return null;

  return (
    <div className="animate-slide-up w-full">
      {state.status === "uploading" && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin text-accent" />
            <span>Uploading {state.fileName}...</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-border">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${state.progress}%`,
                background: "linear-gradient(90deg, var(--accent), var(--accent-secondary))",
              }}
            />
          </div>
        </div>
      )}

      {state.status === "success" && (
        <div
          className={cn(
            "flex items-center gap-2 rounded-lg border p-4",
            "border-green-500/30 bg-green-500/5 text-green-400"
          )}
          style={{ boxShadow: "0 0 15px rgba(34, 197, 94, 0.1)" }}
        >
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span className="text-sm">
            File uploaded successfully.
          </span>
        </div>
      )}

      {state.status === "error" && (
        <div
          className={cn(
            "flex items-center gap-2 rounded-lg border p-4",
            "border-red-500/30 bg-red-500/5 text-red-400"
          )}
        >
          <XCircle className="h-5 w-5 shrink-0" />
          <span className="text-sm">{state.error}</span>
        </div>
      )}
    </div>
  );
}
