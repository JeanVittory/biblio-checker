import { NextResponse } from "next/server";
import { z } from "zod";
import { v4 as uuidv4 } from "uuid";
import { ALLOWED_EXTENSIONS, ERROR_MESSAGES, HTTP_STATUS, MIME_TYPES } from "@/lib/constants";
import { extensionFromFileName, sanitizeFileName } from "@/lib/utils";
import { getSupabaseAdminClient } from "@/lib/supabaseAdmin";
import { signedUploadEnvSchema, signedUploadRequestSchema } from "@/lib/validation/signUploadURL";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const env = signedUploadEnvSchema.parse(process.env);
    const body = signedUploadRequestSchema.parse(await request.json());

    const extension = extensionFromFileName(body.fileName);
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      return NextResponse.json(
        { success: false, message: ERROR_MESSAGES.INVALID_TYPE },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    const expectedContentType = extension === ".pdf" ? MIME_TYPES.PDF : MIME_TYPES.DOCX;
    if (body.contentType !== expectedContentType) {
      return NextResponse.json(
        { success: false, message: ERROR_MESSAGES.INVALID_TYPE },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    const requestId = uuidv4();
    const bucket = env.SUPABASE_STORAGE_BUCKET;
    const safeFileName = sanitizeFileName(body.fileName);
    const filePath = `${bucket}/${requestId}/${safeFileName}`;

    const supabase = getSupabaseAdminClient();
    const { data, error } = await supabase.storage
      .from(bucket)
      .createSignedUploadUrl(filePath, { upsert: false });

    if (error || !data?.signedUrl) {
      return NextResponse.json(
        {
          success: false,
          message: error?.message ?? "Failed to create signed upload URL.",
        },
        { status: HTTP_STATUS.BAD_GATEWAY }
      );
    }

    const clientExpiresInSeconds = 60;
    const clientExpiresAt = new Date(Date.now() + clientExpiresInSeconds * 1000).toISOString();

    return NextResponse.json({
      success: true,
      message: "Signed upload URL created.",
      bucket,
      requestId,
      filePath,
      signedUrl: data.signedUrl,
      clientExpiresInSeconds,
      clientExpiresAt,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { success: false, message: "Invalid request.", issues: error.issues },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }
    if (error instanceof SyntaxError) {
      return NextResponse.json(
        { success: false, message: "Invalid JSON body." },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }
    const message = error instanceof Error ? error.message : ERROR_MESSAGES.SERVER_ERROR;
    return NextResponse.json(
      { success: false, message },
      { status: HTTP_STATUS.INTERNAL_SERVER_ERROR }
    );
  }
}
