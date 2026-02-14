import { z } from "zod";
import { EXTRACT_MODES, MIME_TYPES, SOURCE_TYPES, STORAGE_PROVIDERS } from "@/lib/constants";

export const extractModeSchema = z.literal(EXTRACT_MODES.BACKEND_EXTRACT_REFERENCES);

export const sourceTypeSchema = z.union([z.literal(SOURCE_TYPES.PDF), z.literal(SOURCE_TYPES.DOCX)]);

export const mimeTypeSchema = z.union([
  z.literal(MIME_TYPES.PDF),
  z.literal(MIME_TYPES.DOCX),
]);

export const bibliographyCheckRequestSchema = z.object({
  requestId: z.string().uuid(),
  extractMode: extractModeSchema,
  document: z.object({
    sourceType: sourceTypeSchema,
    fileName: z.string().min(1),
    mimeType: mimeTypeSchema,
  }),
  storage: z.object({
    provider: z.literal(STORAGE_PROVIDERS.SUPABASE),
    bucket: z.string().min(1),
    path: z.string().min(1),
  }),
  integrity: z
    .object({
      sha256: z.string().regex(/^[a-f0-9]{64}$/),
    })
    .optional(),
});

export type BibliographyCheckRequestPayload = z.infer<typeof bibliographyCheckRequestSchema>;
