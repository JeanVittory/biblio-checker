import { z } from "zod";

export const uploadStateSchema = z.object({
  status: z.enum(["idle", "uploading", "success", "error"]),
  progress: z.number(),
  error: z.string().nullable(),
  fileName: z.string().nullable(),
});

export const uploadResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  fileId: z.string(),
  fileName: z.string(),
  requestId: z.string().optional(),
  storage: z
    .object({
      bucket: z.string(),
      path: z.string(),
    })
    .optional(),
  backend: z.unknown().optional(),
});

export type UploadState = z.infer<typeof uploadStateSchema>;
export type UploadResponse = z.infer<typeof uploadResponseSchema>;
