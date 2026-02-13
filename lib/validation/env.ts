import { z } from "zod";

export const routeEnvSchema = z.object({
  SUPABASE_STORAGE_BUCKET: z.string().min(1),
  BIBLIO_BACKEND_CHECK_URL: z.string().url(),
});
