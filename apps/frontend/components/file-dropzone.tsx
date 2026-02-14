"use client";

import { useCallback } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Upload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { validateFile, formatFileSize } from "@/lib/utils";
import { ALLOWED_MIME_TYPES, MAX_FILE_SIZE } from "@/lib/constants";

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
  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        const code = rejected[0].errors[0]?.code;
        if (code === "file-too-large") {
          onError("File exceeds the maximum size of 10 MB.");
        } else {
          onError("Only PDF and DOCX files are allowed.");
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
    [onFileSelect, onError]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ALLOWED_MIME_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
    disabled,
  });

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
            Remove
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
                ? "Drop your file here"
                : "Drag & drop your file here"}
            </p>
            <p className="mt-1 text-sm text-muted">
              PDF or DOCX, up to 10 MB
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
