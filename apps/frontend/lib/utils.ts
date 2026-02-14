import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import {
  MAX_FILE_SIZE,
  ALLOWED_EXTENSIONS,
  ERROR_MESSAGES,
  FILE_EXTENSIONS,
  SOURCE_TYPES,
} from "./constants";
import type { SourceType } from "@/types/bibliographyCheck";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function sanitizeFileName(fileName: string) {
  const cleaned = fileName
    .replace(/[^\w.\-() ]/g, "_")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned.length ? cleaned : "upload";
}

export function sourceTypeFromFileName(fileName: string): SourceType | null {
  const ext = "." + fileName.split(".").pop()?.toLowerCase();
  if (ext === FILE_EXTENSIONS.PDF) return SOURCE_TYPES.PDF;
  if (ext === FILE_EXTENSIONS.DOCX) return SOURCE_TYPES.DOCX;
  return null;
}

export function validateFile(file: File): string | null {
  if (file.size > MAX_FILE_SIZE) {
    return ERROR_MESSAGES.FILE_TOO_LARGE;
  }

  const extension = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return ERROR_MESSAGES.INVALID_TYPE;
  }

  return null;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function simulateProgress(onProgress: (progress: number) => void): () => void {
  let current = 0;
  const interval = setInterval(() => {
    current += Math.random() * 15;
    if (current >= 90) {
      current = 90;
      clearInterval(interval);
    }
    onProgress(Math.round(current));
  }, 200);

  return () => clearInterval(interval);
}

export function extensionFromFileName(fileName: string): string {
  return "." + fileName.split(".").pop()?.toLowerCase();
}
