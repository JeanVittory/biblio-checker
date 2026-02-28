import { z } from "zod";

export const envSchema = z.object({
  SUPABASE_URL: z.string().url(),
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
  SUPABASE_STORAGE_BUCKET: z.string().min(1),
  BIBLIO_BACKEND_CHECK_URL: z.string().url(),
});

export const supabaseEnvSchema = envSchema.pick({
  SUPABASE_URL: true,
  SUPABASE_SERVICE_ROLE_KEY: true,
});

export const routeEnvSchema = envSchema.pick({
  SUPABASE_STORAGE_BUCKET: true,
  BIBLIO_BACKEND_CHECK_URL: true,
});

export const signedUploadEnvSchema = envSchema.pick({
  SUPABASE_STORAGE_BUCKET: true,
});
