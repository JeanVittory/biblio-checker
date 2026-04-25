"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Upload, FileText, X, FlaskConical } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { validateFile, formatFileSize } from "@/lib/file";
import { ALLOWED_MIME_TYPES, MAX_FILE_SIZE, ERROR_KEYS } from "@/lib/constants";
import { fetchSampleDocument } from "@/lib/sampleDocument";

interface FileDropzoneProps {
  file: File | null;
  onFileSelect: (file: File | null) => void;
  onError: (message: string) => void;
  disabled?: boolean;
}

export function FileDropzone({
  file,
  onFileSelect,
  onError,
  disabled,
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
    disabled: disabled || sampleLoading,
  });

  const handleTrySample = useCallback(
    async (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();

      if (disabled || sampleLoading) return;

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
    [disabled, sampleLoading, onFileSelect, onError, t]
  );

  const isSampleDisabled = disabled || sampleLoading;

  return (
    <div
      {...getRootProps()}
      className={cn(
        "glow-effect relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all duration-300",
        "sm:p-12",
        isDragActive
          ? "border-accent bg-accent/5 scale-[1.01]"
          : file
            ? "border-accent/40 bg-surface"
            : "border-border bg-surface hover:border-accent/40",
        disabled && "pointer-events-none opacity-50"
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

          {/* Sample document section */}
          <div className="mt-2 flex flex-col items-center gap-2">
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
        </div>
      )}
    </div>
  );
}
