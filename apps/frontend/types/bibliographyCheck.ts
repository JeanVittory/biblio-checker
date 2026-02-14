import type { EXTRACT_MODES, MIME_TYPES, SOURCE_TYPES, STORAGE_PROVIDERS } from "@/lib/constants";

export type ExtractMode = (typeof EXTRACT_MODES)[keyof typeof EXTRACT_MODES];
export type SourceType = (typeof SOURCE_TYPES)[keyof typeof SOURCE_TYPES];

export interface BibliographyCheckRequest {
  requestId: string;
  extractMode: ExtractMode;
  document: {
    sourceType: SourceType;
    fileName: string;
    mimeType: typeof MIME_TYPES.PDF | typeof MIME_TYPES.DOCX;
  };
  storage: {
    provider: typeof STORAGE_PROVIDERS.SUPABASE;
    bucket: string;
    path: string;
  };
  integrity?: {
    sha256?: string;
  };
}
