import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export type StorageErrorBannerProps = {
  variant: "full" | "corrupted";
};

export function StorageErrorBanner({ variant }: StorageErrorBannerProps) {
  const message =
    variant === "full"
      ? "Storage full. Please remove old jobs to continue."
      : "Unable to load job history. Data may be corrupted.";

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-2 rounded-lg border p-3 text-sm",
        "border-amber-500/30 bg-amber-500/5 text-amber-500"
      )}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}
