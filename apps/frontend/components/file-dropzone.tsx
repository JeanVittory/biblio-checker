"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Upload, FileText, X, FlaskConical, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { validateFile, formatFileSize } from "@/lib/file";
import { ALLOWED_MIME_TYPES, MAX_FILE_SIZE, ERROR_KEYS } from "@/lib/constants";
import { fetchSampleDocument } from "@/lib/sampleDocument";
import { FeatureLockedTooltip } from "@/components/ui/feature-locked-tooltip";

interface FileDropzoneProps {
  file: File | null;
  onFileSelect: (file: File | null) => void;
  onError: (message: string) => void;
  disabled?: boolean;
  /**
   * When true, the drop area + file input are visually and functionally
   * disabled with a "coming soon" tooltip. The sample/demo button stays
   * enabled so users can still try the app with the bundled example.
   */
  uploadLocked?: boolean;
}

export function FileDropzone({
  file,
  onFileSelect,
  onError,
  disabled,
  uploadLocked = false,
}: FileDropzoneProps) {
  const t = useTranslations();
  const [sampleLoading, setSampleLoading] = useState(false);

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        const code = rejected[0].errors[0]?.code;
        if (code === "file-too-large") {
          onError(t(ERROR_KEYS.FILE_TOO_LARGE as Parameters<typeof t>[0]));
        } else {
          onError(t(ERROR_KEYS.UNSUPPORTED_FORMAT as Parameters<typeof t>[0]));
        }
        return;
      }

      if (accepted.length > 0) {
        const error = validateFile(accepted[0]);
        if (error) {
          onError(error);
          return;
        }
        onFileSelect(accepted[0]);
      }
    },
    [onFileSelect, onError, t]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ALLOWED_MIME_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
    disabled: uploadLocked || disabled || sampleLoading,
  });

  const handleTrySample = useCallback(
    async (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();

      if (sampleLoading) return;

      setSampleLoading(true);
      try {
        const sampleFile = await fetchSampleDocument();
        onFileSelect(sampleFile);
      } catch {
        onError(t(ERROR_KEYS.NETWORK_ERROR as Parameters<typeof t>[0]));
      } finally {
        setSampleLoading(false);
      }
    },
    [sampleLoading, onFileSelect, onError, t]
  );

  // The sample button remains usable even when uploadLocked is true — that is
  // the only path users have to try the app while uploads are gated.
  const isSampleDisabled = sampleLoading;

  // When uploadLocked is true, the empty-state prompt area is wrapped in the
  // tooltip wrapper. The sample button is rendered OUTSIDE the locked region
  // so it remains interactive.
  const lockedTooltip = uploadLocked
    ? t("featureLocked.uploadTooltip" as Parameters<typeof t>[0])
    : null;

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "glow-effect relative rounded-xl border-2 border-dashed p-8 text-center transition-all duration-300",
          "sm:p-12",
          uploadLocked
            ? "cursor-not-allowed border-border bg-surface opacity-60"
            : isDragActive
              ? "cursor-pointer border-accent bg-accent/5 scale-[1.01]"
              : file
                ? "cursor-pointer border-accent/40 bg-surface"
                : "cursor-pointer border-border bg-surface hover:border-accent/40",
          disabled && !uploadLocked && "pointer-events-none opacity-50"
        )}
      >
        <input {...getInputProps()} />

        {/* Decorative corners */}
        <div className="absolute top-0 left-0 h-4 w-4 border-t-2 border-l-2 border-accent rounded-tl-xl" />
        <div className="absolute top-0 right-0 h-4 w-4 border-t-2 border-r-2 border-accent rounded-tr-xl" />
        <div className="absolute bottom-0 left-0 h-4 w-4 border-b-2 border-l-2 border-accent rounded-bl-xl" />
        <div className="absolute bottom-0 right-0 h-4 w-4 border-b-2 border-r-2 border-accent rounded-br-xl" />

        {file ? (
          <div className="flex flex-col items-center gap-3 animate-slide-up">
            <FileText className="h-10 w-10 text-accent" />
            <div>
              <p className="font-medium text-foreground">{file.name}</p>
              <p className="text-sm text-muted">{formatFileSize(file.size)}</p>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onFileSelect(null);
              }}
              className="mt-1 flex items-center gap-1 text-sm text-muted hover:text-red-400 transition-colors"
            >
              <X className="h-3 w-3" />
              {t("common.remove" as Parameters<typeof t>[0])}
            </button>
          </div>
        ) : uploadLocked && lockedTooltip ? (
          <FeatureLockedTooltip message={lockedTooltip}>
            <div className="flex flex-col items-center gap-3">
              <Lock className="h-10 w-10 text-muted" aria-hidden="true" />
              <div>
                <p className="font-medium text-foreground">
                  {t("dropzone.lockedPrompt" as Parameters<typeof t>[0])}
                </p>
                <p className="mt-1 text-sm text-muted">
                  {t("dropzone.lockedHint" as Parameters<typeof t>[0])}
                </p>
              </div>
            </div>
          </FeatureLockedTooltip>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <Upload
              className={cn(
                "h-10 w-10 transition-colors",
                isDragActive ? "text-accent" : "text-muted"
              )}
            />
            <div>
              <p className="font-medium text-foreground">
                {isDragActive
                  ? t("dropzone.prompt_primary" as Parameters<typeof t>[0])
                  : t("dropzone.prompt_primary" as Parameters<typeof t>[0])}
              </p>
              <p className="mt-1 text-sm text-muted">
                {t("dropzone.prompt_secondary" as Parameters<typeof t>[0])}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Sample document section — always available, including when uploadLocked is true */}
      {!file && (
        <div className="flex flex-col items-center gap-2">
          <span className="text-xs text-muted">
            {t("dropzone.or" as Parameters<typeof t>[0])}
          </span>
          <button
            type="button"
            onClick={handleTrySample}
            disabled={isSampleDisabled}
            className={cn(
              "flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm transition-colors",
              isSampleDisabled
                ? "cursor-not-allowed opacity-50 text-muted"
                : "text-foreground hover:border-accent/60 hover:text-accent"
            )}
          >
            <FlaskConical className="h-4 w-4" />
            {sampleLoading
              ? t("dropzone.sampleLoading" as Parameters<typeof t>[0])
              : t("dropzone.trySample" as Parameters<typeof t>[0])}
          </button>
          {!sampleLoading && (
            <p className="text-xs text-muted">
              {t("dropzone.sampleDescription" as Parameters<typeof t>[0])}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
