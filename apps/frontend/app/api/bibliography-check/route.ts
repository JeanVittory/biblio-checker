import { NextResponse } from "next/server";
import { z } from "zod";
import { createHash } from "node:crypto";
import { getSupabaseAdminClient } from "@/lib/supabaseAdmin";
import { cleanupUploadedFile } from "@/lib/server/storageCleanup";
import { bibliographyCheckRequestSchema } from "@/lib/validation/bibliographyCheck";
import { routeEnvSchema } from "@/lib/validation/env";
import { ERROR_MESSAGES, HEADER_NAMES, HTTP_STATUS, MIME_TYPES } from "@/lib/constants";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let cleanupTarget: { bucket: string; path: string } | null = null;
  try {
    const env = routeEnvSchema.parse(process.env);
    const payload = bibliographyCheckRequestSchema.parse(await request.json());
    cleanupTarget = { bucket: payload.storage.bucket, path: payload.storage.path };

    if (payload.storage.bucket !== env.SUPABASE_STORAGE_BUCKET) {
      return NextResponse.json(
        { ok: false, success: false, message: "Invalid storage bucket." },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    const supabase = getSupabaseAdminClient();
    const { data, error } = await supabase.storage
      .from(payload.storage.bucket)
      .download(payload.storage.path);

    if (error || !data) {
      await cleanupUploadedFile(payload.storage.bucket, payload.storage.path);
      return NextResponse.json(
        {
          ok: false,
          success: false,
          message: error?.message ?? "Failed to download uploaded file.",
        },
        { status: HTTP_STATUS.BAD_GATEWAY }
      );
    }

    const fileBytes = new Uint8Array(await data.arrayBuffer());
    const sha256 = createHash("sha256").update(Buffer.from(fileBytes)).digest("hex");

    const payloadWithIntegrity = {
      ...payload,
      integrity: { sha256 },
    };

    const validatedPayload = bibliographyCheckRequestSchema.parse(payloadWithIntegrity);

    const backendResponse = await fetch(env.BIBLIO_BACKEND_CHECK_URL, {
      method: "POST",
      headers: { [HEADER_NAMES.CONTENT_TYPE]: MIME_TYPES.JSON },
      body: JSON.stringify(validatedPayload),
    });

    const backendText = await backendResponse.text();
    let backendJson: unknown = null;
    try {
      backendJson = backendText ? JSON.parse(backendText) : null;
    } catch {
      backendJson = backendText;
    }

    const backendBodyIndicatesError =
      backendJson &&
      typeof backendJson === "object" &&
      (("ok" in backendJson && (backendJson as Record<string, unknown>).ok === false) ||
        ("success" in backendJson && (backendJson as Record<string, unknown>).success === false));

    if (!backendResponse.ok || backendBodyIndicatesError) {
      await cleanupUploadedFile(validatedPayload.storage.bucket, validatedPayload.storage.path);
      return NextResponse.json(
        {
          ok: false,
          success: false,
          message: "Backend request failed.",
          requestId: validatedPayload.requestId,
          storage: validatedPayload.storage,
          backend: backendJson,
        },
        { status: HTTP_STATUS.BAD_GATEWAY }
      );
    }

    return NextResponse.json({
      ok: true,
      success: true,
      message: "Bibliography check forwarded successfully.",
      requestId: validatedPayload.requestId,
      storage: validatedPayload.storage,
      backend: backendJson,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { ok: false, success: false, message: "Invalid request.", issues: error.issues },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }
    if (error instanceof SyntaxError) {
      return NextResponse.json(
        { ok: false, success: false, message: "Invalid JSON body." },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }
    if (cleanupTarget) {
      await cleanupUploadedFile(cleanupTarget.bucket, cleanupTarget.path);
    }
    const message = error instanceof Error ? error.message : ERROR_MESSAGES.SERVER_ERROR;
    return NextResponse.json(
      { ok: false, success: false, message },
      { status: HTTP_STATUS.INTERNAL_SERVER_ERROR }
    );
  }
}
