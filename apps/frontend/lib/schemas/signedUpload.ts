import { z } from "zod";

export const signedUploadInitRequestSchema = z.object({
  fileName: z.string(),
  contentType: z.string(),
});

export const signedUploadInitResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  bucket: z.string().optional(),
  requestId: z.string().optional(),
  path: z.string().optional(),
  filePath: z.string().optional(),
  signedUrl: z.string().optional(),
  clientExpiresInSeconds: z.number().optional(),
  clientExpiresAt: z.string().optional(),
});

export type SignedUploadInitRequest = z.infer<typeof signedUploadInitRequestSchema>;
export type SignedUploadInitResponse = z.infer<typeof signedUploadInitResponseSchema>;
