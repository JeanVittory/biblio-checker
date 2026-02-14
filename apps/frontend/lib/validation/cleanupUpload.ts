import { z } from "zod";
import { UPLOAD_PATHS } from "@/lib/constants";

export const cleanupUploadRequestSchema = z.object({
  bucket: z.string().min(1),
  path: z
    .string()
    .min(1)
    .refine((value) => value.startsWith(`${UPLOAD_PATHS.PREFIX}/`), {
      message: `path must start with '${UPLOAD_PATHS.PREFIX}/'`,
    }),
});

export type CleanupUploadRequest = z.infer<typeof cleanupUploadRequestSchema>;

