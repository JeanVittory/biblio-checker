import { createClient } from "@supabase/supabase-js";
import { z } from "zod";

const supabaseEnvSchema = z.object({
  SUPABASE_URL: z.string().url(),
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
});

export function getSupabaseAdminClient() {
  const env = supabaseEnvSchema.parse(process.env);

  return createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false },
  });
}
