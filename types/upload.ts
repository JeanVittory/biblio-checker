export interface UploadState {
  status: "idle" | "uploading" | "success" | "error";
  progress: number;
  error: string | null;
  fileName: string | null;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  fileId: string;
  fileName: string;
  requestId?: string;
  storage?: {
    bucket: string;
    path: string;
  };
  backend?: unknown;
}
