import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { textReferenceCheckSchema } from "@/lib/schemas/bibliographyCheck";
import { HTTP_STATUS } from "@/lib/constants";
import { LOCALE_COOKIE, normalizeLocale } from "@/i18n/config";
import logger from "@/lib/logger";

export const runtime = "nodejs";

const log = logger.child({ module: "analysis-text-gateway" });

/**
 * POST /api/analysis-text-gateway
 *
 * Thin proxy: validate body shape, override locale from cookie, forward to
 * the backend text-analysis endpoint. No Supabase Storage involved.
 *
 * Spec: spec/single-reference-text-check/05-frontend-gateway/spec.md
 */
export async function POST(request: Request) {
  let requestId: string | undefined;

  try {
    // -------------------------------------------------------------------------
    // 1. Parse the request body as JSON.
    // -------------------------------------------------------------------------
    let rawBody: unknown;
    try {
      rawBody = await request.json();
    } catch {
      return NextResponse.json(
        { ok: false, success: false, message: "Invalid JSON body." },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    // -------------------------------------------------------------------------
    // 2. Validate against the strict Zod schema.
    // -------------------------------------------------------------------------
    const parsed = textReferenceCheckSchema.safeParse(rawBody);

    if (!parsed.success) {
      const errors = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`);

      // Attempt to extract requestId for logging even on failure, without
      // trusting raw input types.
      const maybeId =
        rawBody !== null &&
        typeof rawBody === "object" &&
        "requestId" in (rawBody as object) &&
        typeof (rawBody as Record<string, unknown>).requestId === "string"
          ? (rawBody as Record<string, unknown>).requestId
          : undefined;

      log.warn(
        { requestId: maybeId, errors },
        "text_gateway_validation_failed"
      );

      // Error responses MUST NOT echo requestId (§ 7).
      return NextResponse.json(
        { ok: false, success: false, message: "Invalid request body." },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    const body = parsed.data;
    requestId = body.requestId;

    log.info({ requestId, text_length: body.reference.rawText.length }, "text_gateway_request_received");

    // -------------------------------------------------------------------------
    // 3. Derive locale from cookie (server-side source of truth).
    // -------------------------------------------------------------------------
    const cookieStore = await cookies();
    const localeFromCookie = cookieStore.get(LOCALE_COOKIE)?.value ?? null;
    const locale = normalizeLocale(localeFromCookie);

    // -------------------------------------------------------------------------
    // 4. Resolve the backend URL from the environment.
    // -------------------------------------------------------------------------
    const backendBaseUrl = process.env.BIBLIO_BACKEND_CHECK_URL;
    if (!backendBaseUrl) {
      log.error({ requestId }, "BIBLIO_BACKEND_CHECK_URL is not configured");
      return NextResponse.json(
        { ok: false, success: false, message: "Server configuration error." },
        { status: HTTP_STATUS.INTERNAL_SERVER_ERROR }
      );
    }

    // -------------------------------------------------------------------------
    // 5. Build the forwarded payload — locale overrides any client value.
    // -------------------------------------------------------------------------
    const forwardedPayload = {
      requestId: body.requestId,
      reference: { rawText: body.reference.rawText },
      locale,
    };

    // -------------------------------------------------------------------------
    // 6. Forward to backend with a 30-second timeout.
    // -------------------------------------------------------------------------
    log.info({ requestId }, "text_gateway_forwarded");

    let backendResponse: Response;
    try {
      backendResponse = await fetch(
        `${backendBaseUrl}/api/analysis/start-text`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept-Language": locale,
          },
          body: JSON.stringify(forwardedPayload),
          signal: AbortSignal.timeout(30_000),
        }
      );
    } catch (fetchError) {
      const isTimeout =
        fetchError instanceof Error &&
        (fetchError.name === "TimeoutError" || fetchError.name === "AbortError");
      log.error(
        { requestId, err: isTimeout ? "timeout" : String(fetchError) },
        "text_gateway_backend_error"
      );
      return NextResponse.json(
        { ok: false, success: false, message: "Backend unreachable." },
        { status: HTTP_STATUS.BAD_GATEWAY }
      );
    }

    // -------------------------------------------------------------------------
    // 7. Map backend response to gateway response.
    // -------------------------------------------------------------------------
    if (backendResponse.ok) {
      const backendBody = (await backendResponse.json()) as Record<string, unknown>;

      return NextResponse.json({
        ok: true,
        success: true,
        message: "Analysis started successfully.",
        requestId,
        backend: {
          message: backendBody.message,
          success: backendBody.success,
          jobId: backendBody.jobId,
          status: backendBody.status,
          jobToken: backendBody.jobToken,
        },
      });
    }

    // Non-200 from backend — map to gateway error.
    log.warn(
      { requestId, status: backendResponse.status },
      "text_gateway_backend_error"
    );

    if (backendResponse.status === 422) {
      return NextResponse.json(
        { ok: false, success: false, message: "Validation error from backend." },
        { status: HTTP_STATUS.BAD_REQUEST }
      );
    }

    if (backendResponse.status >= 500) {
      let backendCode: string | undefined;
      let backendTitle: string | undefined;
      try {
        const errBody = (await backendResponse.json()) as Record<string, unknown>;
        if (typeof errBody.code === "string") backendCode = errBody.code;
        if (typeof errBody.title === "string") backendTitle = errBody.title;
      } catch {
        // Non-JSON body — leave undefined.
      }

      // Preserve 503 only when the backend identifies a "service_offline"
      // condition; otherwise keep the existing 502 mapping.
      const passThroughStatus =
        backendCode === "service_offline" && backendResponse.status === 503
          ? 503
          : HTTP_STATUS.BAD_GATEWAY;

      return NextResponse.json(
        {
          ok: false,
          success: false,
          code: backendCode,
          message: backendTitle ?? "Internal error.",
        },
        { status: passThroughStatus }
      );
    }

    // Other 4xx — forward a safe summary without echoing requestId.
    let safeMessage = "Request rejected by backend.";
    let backendCode: string | undefined;
    try {
      const errBody = (await backendResponse.json()) as Record<string, unknown>;
      if (typeof errBody.message === "string") {
        safeMessage = errBody.message;
      }
      if (typeof errBody.code === "string") {
        backendCode = errBody.code;
      }
    } catch {
      // Non-JSON body — use default.
    }

    return NextResponse.json(
      { ok: false, success: false, code: backendCode, message: safeMessage },
      { status: HTTP_STATUS.BAD_REQUEST }
    );
  } catch (error) {
    log.error({ requestId, err: error }, "text_gateway_unexpected_error");
    return NextResponse.json(
      { ok: false, success: false, message: "An unexpected error occurred." },
      { status: HTTP_STATUS.INTERNAL_SERVER_ERROR }
    );
  }
}
