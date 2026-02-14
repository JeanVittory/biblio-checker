import { z } from "zod";
import { MIME_TYPES } from "../constants";

export const signedUploadRequestSchema = z.object({
  fileName: z.string().min(1),
  contentType: z.union([z.literal(MIME_TYPES.PDF), z.literal(MIME_TYPES.DOCX)]),
});

export const signedUploadEnvSchema = z.object({
  SUPABASE_STORAGE_BUCKET: z.string().min(1),
});
