"use client";

import { useState, useCallback } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { FileDropzone } from "@/components/file-dropzone";
import { UploadStatus } from "@/components/upload-status";
import { BackgroundGrid } from "@/components/background-grid";
import { simulateProgress, sourceTypeFromFileName } from "@/lib/utils";
import { ERROR_MESSAGES, EXTRACT_MODES, MIME_TYPES, STORAGE_PROVIDERS } from "@/lib/constants";
import type { UploadState } from "@/types/upload";
import type { BibliographyCheckRequest } from "@/types/bibliographyCheck";
import { bibliographyCheckBaseSchema } from "@/lib/validation/bibliographyCheck";
import { signedUploadService } from "@/services/signedUpload";
import { uploadFileService } from "@/services/uploadFile";
import { cleanupUploadService } from "@/services/cleanupUpload";
import { verifyAuthenticityGatewayService } from "@/services/verifyAuthenticityGateway";

const initialState: UploadState = {
  status: "idle",
  progress: 0,
  error: null,
  fileName: null,
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>(initialState);

  const handleFileSelect = useCallback((selected: File | null) => {
    setFile(selected);
    setUploadState(initialState);
  }, []);

  const handleError = useCallback((message: string) => {
    setUploadState({
      status: "error",
      progress: 0,
      error: message,
      fileName: null,
    });
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) return;

    setUploadState({
      status: "uploading",
      progress: 0,
      error: null,
      fileName: file.name,
    });

    const stopProgress = simulateProgress((progress) => {
      setUploadState((prev) => ({ ...prev, progress }));
    });

    let cleanupTarget: { bucket: string; path: string } | null = null;
    const attemptCleanup = async () => {
      if (!cleanupTarget) return;
      try {
        await cleanupUploadService(cleanupTarget.bucket, cleanupTarget.path);
      } catch {
        // best-effort
      }
    };

    try {
      const initData = await signedUploadService(file);
      const initPath = initData.path ?? initData.filePath;
      if (
        !initData.success ||
        !initData.signedUrl ||
        !initData.bucket ||
        !initData.requestId ||
        !initPath
      ) {
        stopProgress();
        setUploadState({
          status: "error",
          progress: 0,
          error: initData.message || ERROR_MESSAGES.UPLOAD_FAILED,
          fileName: file.name,
        });
        return;
      }

      cleanupTarget = { bucket: initData.bucket, path: initPath };

      const uploadResponse = await uploadFileService(file, initData);
      if (!uploadResponse || !uploadResponse.ok) {
        await attemptCleanup();
        stopProgress();
        setUploadState({
          status: "error",
          progress: 0,
          error: ERROR_MESSAGES.UPLOAD_FAILED,
          fileName: file.name,
        });
        return;
      }

      const sourceType = sourceTypeFromFileName(file.name);
      if (!sourceType) {
        await attemptCleanup();
        stopProgress();
        setUploadState({
          status: "error",
          progress: 0,
          error: ERROR_MESSAGES.INVALID_TYPE,
          fileName: file.name,
        });
        return;
      }

      const mimeType =
        file.type === MIME_TYPES.PDF || file.type === MIME_TYPES.DOCX ? file.type : null;

      if (!mimeType) {
        await attemptCleanup();
        stopProgress();
        setUploadState({
          status: "error",
          progress: 0,
          error: ERROR_MESSAGES.INVALID_TYPE,
          fileName: file.name,
        });
        return;
      }

      const payload: BibliographyCheckRequest = {
        requestId: initData.requestId,
        extractMode: EXTRACT_MODES.BACKEND_EXTRACT_REFERENCES,
        document: {
          sourceType,
          fileName: file.name,
          mimeType,
        },
        storage: {
          provider: STORAGE_PROVIDERS.SUPABASE,
          bucket: initData.bucket,
          path: initPath,
        },
      };

      const validatedPayload = bibliographyCheckBaseSchema.parse(payload);

      const bibliographyCheckResponse = await verifyAuthenticityGatewayService(validatedPayload);

      const bibliographyCheck = await bibliographyCheckResponse.json();

      if (
        !bibliographyCheckResponse.ok ||
        !bibliographyCheck ||
        typeof bibliographyCheck !== "object"
      ) {
        await attemptCleanup();
        stopProgress();
        setUploadState({
          status: "error",
          progress: 0,
          error: ERROR_MESSAGES.UPLOAD_FAILED,
          fileName: file.name,
        });
        return;
      }

      const checkObj = bibliographyCheck as Record<string, unknown>;
      const checkMessage = typeof checkObj.message === "string" ? checkObj.message : null;
      const checkSuccess = typeof checkObj.success === "boolean" ? checkObj.success : false;

      if (!checkSuccess) {
        await attemptCleanup();
        stopProgress();
        setUploadState({
          status: "error",
          progress: 0,
          error: checkMessage || ERROR_MESSAGES.UPLOAD_FAILED,
          fileName: file.name,
        });
        return;
      }

      stopProgress();
      setUploadState({
        status: "success",
        progress: 100,
        error: null,
        fileName: file.name,
      });
    } catch {
      await attemptCleanup();
      stopProgress();
      setUploadState({
        status: "error",
        progress: 0,
        error: ERROR_MESSAGES.UPLOAD_FAILED,
        fileName: file.name,
      });
    }
  }, [file]);

  const handleReset = useCallback(() => {
    setFile(null);
    setUploadState(initialState);
  }, []);

  return (
    <div className="relative flex min-h-screen flex-col">
      <BackgroundGrid />

      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 sm:px-8">
        <h1 className="text-lg font-bold tracking-tight">
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage: "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
            }}
          >
            Biblio Checker
          </span>
        </h1>
        <ThemeToggle />
      </header>

      {/* Main */}
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-8 px-6 pb-16 sm:px-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Upload Your Bibliography
          </h2>
          <p className="mt-3 text-muted">Upload a PDF or DOCX file.</p>
        </div>

        <div className="w-full space-y-6">
          <FileDropzone
            file={file}
            onFileSelect={handleFileSelect}
            onError={handleError}
            disabled={uploadState.status === "uploading"}
          />

          {file && uploadState.status !== "uploading" && uploadState.status !== "success" && (
            <div className="flex gap-3 animate-slide-up">
              <button
                onClick={handleUpload}
                className="glow-effect flex-1 rounded-lg px-6 py-2.5 text-sm font-medium text-white transition-colors"
                style={{
                  background: "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
                }}
              >
                Upload
              </button>
              <button
                onClick={handleReset}
                className="rounded-lg border border-border bg-surface px-6 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
              >
                Clear
              </button>
            </div>
          )}

          <UploadStatus state={uploadState} />

          {uploadState.status === "success" && (
            <button
              onClick={handleReset}
              className="mx-auto block text-sm text-accent hover:underline transition-colors animate-slide-up"
            >
              Upload another file
            </button>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-xs text-muted">
        Biblio Checker &mdash; Academic reference validation
      </footer>
    </div>
  );
}
