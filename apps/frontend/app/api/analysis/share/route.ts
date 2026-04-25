/**
 * POST /api/analysis/share
 *
 * Transparent proxy to the backend share-creation endpoint. Forwards the
 * JSON request body to the backend and preserves the backend HTTP status
 * code.
 */

import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { HTTP_STATUS } from "@/lib/constants";

export const runtime = "nodejs";

/** 30-second hard timeout for the upstream request. */
const UPSTREAM_TIMEOUT_MS = 30_000;

const routeEnvSchema = z.object({
  BIBLIO_BACKEND_CHECK_URL: z.string().url().default("http://localhost:8000"),
});

export async function POST(request: NextRequest): Promise<Response> {
  // --- Resolve backend URL from environment ---
  let env: z.infer<typeof routeEnvSchema>;
  try {
    env = routeEnvSchema.parse(process.env);
  } catch {
    return NextResponse.json(
      { error: "Analysis service is not configured." },
      { status: HTTP_STATUS.INTERNAL_SERVER_ERROR }
    );
  }

  const backendOrigin = new URL(env.BIBLIO_BACKEND_CHECK_URL).origin;
  const upstreamUrl = `${backendOrigin}/api/analysis/share`;

  // --- Read and forward the request body ---
  let requestBody: string;
  try {
    requestBody = await request.text();
  } catch {
    return NextResponse.json(
      { error: "Failed to read request body." },
      { status: HTTP_STATUS.BAD_REQUEST }
    );
  }

  // --- Forward request to backend with timeout ---
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);

  let backendResponse: Response;
  try {
    backendResponse = await fetch(upstreamUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: requestBody,
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

    return NextResponse.json(
      { error: "Unable to reach analysis service." },
      { status: HTTP_STATUS.BAD_GATEWAY }
    );
  }

  clearTimeout(timeoutId);

  // --- Transparently forward backend response ---
  const cloned = backendResponse.clone();
  let body: unknown;
  try {
    body = await backendResponse.json();
  } catch {
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
