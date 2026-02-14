import { NextResponse } from "next/server";
import { z } from "zod";
import { signedUploadEnvSchema } from "@/lib/validation/signUploadURL";
import { cleanupUploadedFile } from "@/lib/server/storageCleanup";
import { cleanupUploadRequestSchema } from "@/lib/validation/cleanupUpload";
import { ERROR_MESSAGES, HTTP_STATUS } from "@/lib/constants";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const env = signedUploadEnvSchema.parse(process.env);
    const body = cleanupUploadRequestSchema.parse(await request.json());

    if (body.bucket !== env.SUPABASE_STORAGE_BUCKET) {
      return NextResponse.json(
        { ok: false, success: false, message: "Invalid storage bucket." },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    await cleanupUploadedFile(body.bucket, body.path);

    return NextResponse.json({
      ok: true,
      success: true,
      message: "Cleanup attempted.",
      bucket: body.bucket,
      path: body.path,
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
    const message = error instanceof Error ? error.message : ERROR_MESSAGES.SERVER_ERROR;
    return NextResponse.json(
      { ok: false, success: false, message },
      { status: HTTP_STATUS.INTERNAL_SERVER_ERROR }
    );
  }
}
