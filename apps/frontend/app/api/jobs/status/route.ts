/**
 * GET /api/jobs/status?jobId=xxx&jobToken=yyy
 *
 * Transparent proxy to the backend job-status endpoint. Validates query
 * params, forwards the request to the backend, and preserves the backend
 * HTTP status code. Never exposes the backend URL or raw token values in
 * error responses or logs.
 */

import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { HTTP_STATUS } from "@/lib/constants";


export const runtime = "nodejs";

/** 30-second hard timeout for the upstream request. */
const UPSTREAM_TIMEOUT_MS = 30_000;

const querySchema = z.object({
  jobId: z.string().min(1).max(256),
  jobToken: z.string().min(1).max(256),
});

const routeEnvSchema = z.object({
  BIBLIO_BACKEND_CHECK_URL: z.string().url(),
});

export async function GET(request: NextRequest): Promise<NextResponse> {
  // --- Validate query parameters ---
  const { searchParams } = request.nextUrl;
  const queryParseResult = querySchema.safeParse({
    jobId: searchParams.get("jobId"),
    jobToken: searchParams.get("jobToken"),
  });

  if (!queryParseResult.success) {
    return NextResponse.json(
      { error: "Missing or invalid query parameters: jobId and jobToken are required (max 256 chars each)." },
      { status: HTTP_STATUS.BAD_REQUEST }
    );
  }

  const { jobId, jobToken } = queryParseResult.data;

  // --- Resolve backend URL from environment ---
  let env: z.infer<typeof routeEnvSchema>;
  try {
    env = routeEnvSchema.parse(process.env);
  } catch {
    console.error("[jobs/status] BIBLIO_BACKEND_CHECK_URL is not configured.");
    return NextResponse.json(
      { error: "Analysis service is not configured." },
      { status: HTTP_STATUS.INTERNAL_SERVER_ERROR }
    );
  }

  // Derive the base origin from the backend URL so we can construct a path
  // independently of what the backend base URL contains.
  const backendOrigin = new URL(env.BIBLIO_BACKEND_CHECK_URL).origin;
  const upstreamUrl = `${backendOrigin}/api/analysis/status?jobId=${encodeURIComponent(jobId)}&jobToken=${encodeURIComponent(jobToken)}`;

  // --- Forward request to backend with timeout ---
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);

  let backendResponse: Response;
  try {
    backendResponse = await fetch(upstreamUrl, {
      method: "GET",
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof Error && error.name === "AbortError") {
      return NextResponse.json(
        { error: "Request timed out." },
        { status: HTTP_STATUS.GATEWAY_TIMEOUT }
      );
    }

    // Connection failure or network error — transient.
    return NextResponse.json(
      { error: "Unable to reach analysis service." },
      { status: HTTP_STATUS.BAD_GATEWAY }
    );
  }

  clearTimeout(timeoutId);

  // --- Transparently forward backend response ---
  // Clone before reading so the original stream is available for text fallback.
  const cloned = backendResponse.clone();
  let body: unknown;
  try {
    body = await backendResponse.json();
  } catch {
    // Non-JSON backend response — forward as text, preserve status (09-R10).
    const textBody = await cloned.text().catch(() => "");
    return new Response(textBody, {
      status: backendResponse.status,
      headers: {
        "Content-Type": backendResponse.headers.get("Content-Type") ?? "text/plain",
      },
    });
  }

  return NextResponse.json(body, { status: backendResponse.status });
}
