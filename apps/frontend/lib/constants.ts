export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

export const MIME_TYPES = {
  JSON: "application/json",
  PDF: "application/pdf",
  DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
} as const;

export const SOURCE_TYPES = {
  PDF: "pdf",
  DOCX: "docx",
} as const;

export const FILE_EXTENSIONS = {
  PDF: ".pdf",
  DOCX: ".docx",
} as const;

export const HEADER_NAMES = {
  CONTENT_TYPE: "content-type",
} as const;

export const FORM_DATA_KEYS = {
  FILE: "file",
} as const;

export const STORAGE_PROVIDERS = {
  SUPABASE: "supabase",
} as const;

export const EXTRACT_MODES = {
  BACKEND_EXTRACT_REFERENCES: "backend_extract_references",
} as const;

export const UPLOAD_PATHS = {
  PREFIX: "uploads",
} as const;

export const HTTP_STATUS = {
  BAD_REQUEST: 400,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
} as const;

export const UPLOAD_MESSAGES = {
  BACKEND_REQUEST_FAILED: "Backend request failed.",
  SUCCESS_UPLOADED_AND_FORWARDED:
    "File uploaded to Supabase and forwarded to backend successfully.",
  SUPABASE_UPLOAD_FAILED_PREFIX: "Supabase upload failed:",
} as const;

export const ALLOWED_MIME_TYPES: Record<string, string[]> = {
  [MIME_TYPES.PDF]: [FILE_EXTENSIONS.PDF],
  [MIME_TYPES.DOCX]: [FILE_EXTENSIONS.DOCX],
};

export const ALLOWED_EXTENSIONS: readonly string[] = [FILE_EXTENSIONS.PDF, FILE_EXTENSIONS.DOCX];

export const ERROR_MESSAGES = {
  FILE_TOO_LARGE: "File exceeds the maximum size of 10 MB.",
  INVALID_TYPE: "Only PDF and DOCX files are allowed.",
  UPLOAD_FAILED: "Upload failed. Please try again.",
  NO_FILE: "No file selected.",
  SERVER_ERROR: "An unexpected server error occurred.",
} as const;

export enum API_ROUTES {
  SIGNED_UPLOAD = "/api/signed-upload",
  ANALYSIS_START_GATEWAY = "/api/analysis-start-gateway",
  CLEANUP_UPLOAD = "/api/cleanup-upload",
}

export const BACKEND_ROUTES = {
  ANALYSIS_START: "/api/analysis/start",
} as const;

export enum ENDPOINT_ACTION_TYPES {
  POST = "POST",
  GET = "GET",
  PUT = "PUT",
  DELETE = "DELETE",
  PATCH = "PATCH",
}
