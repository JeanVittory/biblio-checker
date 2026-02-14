import { NextResponse } from "next/server";
import {
  MAX_FILE_SIZE,
  ALLOWED_EXTENSIONS,
  ERROR_MESSAGES,
  EXTRACT_MODES,
  FORM_DATA_KEYS,
  HEADER_NAMES,
  HTTP_STATUS,
  MIME_TYPES,
  STORAGE_PROVIDERS,
  UPLOAD_MESSAGES,
  UPLOAD_PATHS,
} from "@/lib/constants";
import { getSupabaseAdminClient } from "@/lib/supabaseAdmin";
import { cleanupUploadedFile } from "@/lib/server/storageCleanup";
import { bibliographyCheckRequestSchema } from "@/lib/validation/bibliographyCheck";
import { sanitizeFileName, sourceTypeFromFileName } from "@/lib/utils";
import type { BibliographyCheckRequest } from "@/types/bibliographyCheck";
import { createHash } from "node:crypto";
import { v4 as uuidv4 } from "uuid";
import { routeEnvSchema } from "@/lib/validation/env";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let cleanupTarget: { bucket: string; path: string } | null = null;
  let uploadedSuccessfully = false;
  try {
    const env = routeEnvSchema.parse(process.env);
    const formData = await request.formData();
    const file = formData.get(FORM_DATA_KEYS.FILE) as File | null;

    if (!file) {
      return NextResponse.json(
        { success: false, message: ERROR_MESSAGES.NO_FILE, fileId: "", fileName: "" },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { success: false, message: ERROR_MESSAGES.FILE_TOO_LARGE, fileId: "", fileName: file.name },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    const extension = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      return NextResponse.json(
        { success: false, message: ERROR_MESSAGES.INVALID_TYPE, fileId: "", fileName: file.name },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    const sourceType = sourceTypeFromFileName(file.name);
    if (!sourceType) {
      return NextResponse.json(
        { success: false, message: ERROR_MESSAGES.INVALID_TYPE, fileId: "", fileName: file.name },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    const mimeType =
      file.type === MIME_TYPES.PDF || file.type === MIME_TYPES.DOCX
        ? file.type
        : null;

    if (!mimeType) {
      return NextResponse.json(
        { success: false, message: ERROR_MESSAGES.INVALID_TYPE, fileId: "", fileName: file.name },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    const requestId = uuidv4();
    const bucket = env.SUPABASE_STORAGE_BUCKET;
    const safeFileName = sanitizeFileName(file.name);
    const path = `${UPLOAD_PATHS.PREFIX}/${requestId}/${safeFileName}`;
    cleanupTarget = { bucket, path };

    const fileBytes = new Uint8Array(await file.arrayBuffer());
    const sha256 = createHash("sha256").update(Buffer.from(fileBytes)).digest("hex");

    const supabase = getSupabaseAdminClient();
    const uploadResult = await supabase.storage.from(bucket).upload(path, fileBytes, {
      contentType: mimeType,
      upsert: false,
    });

    if (uploadResult.error) {
      return NextResponse.json(
        {
          success: false,
          message: `${UPLOAD_MESSAGES.SUPABASE_UPLOAD_FAILED_PREFIX} ${uploadResult.error.message}`,
          fileId: "",
          fileName: file.name,
        },
        { status: HTTP_STATUS.BAD_GATEWAY }
      );
    }
    uploadedSuccessfully = true;

    const payload: BibliographyCheckRequest = {
      requestId,
      extractMode: EXTRACT_MODES.BACKEND_EXTRACT_REFERENCES,
      document: {
        sourceType,
        fileName: file.name,
        mimeType,
      },
      storage: {
        provider: STORAGE_PROVIDERS.SUPABASE,
        bucket,
        path,
      },
      integrity: {
        sha256,
      },
    };

    const validatedPayload = bibliographyCheckRequestSchema.parse(payload);

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

    if (!backendResponse.ok) {
      if (cleanupTarget && uploadedSuccessfully) {
        await cleanupUploadedFile(cleanupTarget.bucket, cleanupTarget.path);
      }
      return NextResponse.json(
        {
          success: false,
          message: UPLOAD_MESSAGES.BACKEND_REQUEST_FAILED,
          fileId: requestId,
          fileName: file.name,
          requestId,
          storage: { bucket, path },
          backend: backendJson,
        },
        { status: HTTP_STATUS.BAD_GATEWAY }
      );
    }

    return NextResponse.json({
      success: true,
      message: UPLOAD_MESSAGES.SUCCESS_UPLOADED_AND_FORWARDED,
      fileId: requestId,
      fileName: file.name,
      requestId,
      storage: { bucket, path },
      backend: backendJson,
    });
  } catch (error) {
    if (cleanupTarget && uploadedSuccessfully) {
      await cleanupUploadedFile(cleanupTarget.bucket, cleanupTarget.path);
    }
    const message = error instanceof Error ? error.message : ERROR_MESSAGES.SERVER_ERROR;
    return NextResponse.json(
      { success: false, message, fileId: "", fileName: "" },
      { status: HTTP_STATUS.INTERNAL_SERVER_ERROR }
    );
  }
}
