"use client";

import { useState, useCallback } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { FileDropzone } from "@/components/file-dropzone";
import { UploadStatus } from "@/components/upload-status";
import { BackgroundGrid } from "@/components/background-grid";
import { simulateProgress } from "@/lib/utils";
import { ERROR_MESSAGES } from "@/lib/constants";
import type { UploadState } from "@/types/upload";
import type { SignedUploadInitResponse } from "@/types/signedUpload";

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

    try {
      const initResponse = await fetch("/api/signed-upload", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ fileName: file.name, contentType: file.type }),
      });

      const initData = (await initResponse.json()) as SignedUploadInitResponse;

      if (!initResponse.ok || !initData.success || !initData.signedUrl || !initData.filePath) {
        stopProgress();
        setUploadState({
          status: "error",
          progress: 0,
          error: initData.message || ERROR_MESSAGES.UPLOAD_FAILED,
          fileName: file.name,
        });
        return;
      }

      const uploadBody = new FormData();
      uploadBody.append("cacheControl", "3600");
      uploadBody.append("", file);

      const uploadResponse = await fetch(initData.signedUrl, {
        method: "PUT",
        headers: { "x-upsert": "false" },
        body: uploadBody,
      });

      stopProgress();

      if (!uploadResponse.ok) {
        setUploadState({
          status: "error",
          progress: 0,
          error: ERROR_MESSAGES.UPLOAD_FAILED,
          fileName: file.name,
        });
        return;
      }

      setUploadState({
        status: "success",
        progress: 100,
        error: null,
        fileName: file.name,
      });
    } catch {
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
              backgroundImage:
                "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
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
          <p className="mt-3 text-muted">
            Upload a PDF or DOCX file.
          </p>
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
                  background:
                    "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
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
