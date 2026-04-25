"use client";

import { useState, useEffect, useRef } from "react";
import { Link2, Check, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export interface ShareButtonProps {
  jobId: string;
  jobToken: string;
}

interface ShareApiResponse {
  shareToken: string;
  expiresAt: string;
}

/**
 * Returns true when the cached `expiresAt` ISO string is in the past.
 */
function isExpired(expiresAt: string): boolean {
  return Date.now() >= new Date(expiresAt).getTime();
}

/**
 * Share button for a succeeded analysis job.
 * - First click: calls POST /api/analysis/share, caches the token, copies URL.
 * - Subsequent clicks: reuses cached token (re-calls API if expired).
 * - Clipboard failure: shows URL inline as text.
 */
export function ShareButton({ jobId, jobToken }: ShareButtonProps) {
  const t = useTranslations();

  const [shareToken, setShareToken] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);
  const [fallbackUrl, setFallbackUrl] = useState<string | null>(null);

  // Timers for auto-reset of transient states.
  const copiedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up timers on unmount.
  useEffect(() => {
    return () => {
      if (copiedTimerRef.current !== null) clearTimeout(copiedTimerRef.current);
      if (errorTimerRef.current !== null) clearTimeout(errorTimerRef.current);
    };
  }, []);

  async function generateToken(): Promise<string | null> {
    const response = await fetch("/api/analysis/share", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobId, jobToken }),
    });

    if (!response.ok) {
      return null;
    }

    let body: unknown;
    try {
      body = await response.json();
    } catch {
      return null;
    }

    if (
      typeof body !== "object" ||
      body === null ||
      typeof (body as ShareApiResponse).shareToken !== "string" ||
      typeof (body as ShareApiResponse).expiresAt !== "string"
    ) {
      return null;
    }

    const data = body as ShareApiResponse;
    setShareToken(data.shareToken);
    setExpiresAt(data.expiresAt);
    return data.shareToken;
  }

  async function handleClick() {
    if (loading) return;

    setFallbackUrl(null);

    // Determine token to use — either cached (and not expired) or freshly generated.
    let token: string | null = null;

    if (shareToken !== null && expiresAt !== null && !isExpired(expiresAt)) {
      token = shareToken;
    } else {
      setLoading(true);
      setError(false);

      token = await generateToken().catch(() => null);

      setLoading(false);

      if (token === null) {
        setError(true);
        if (errorTimerRef.current !== null) clearTimeout(errorTimerRef.current);
        errorTimerRef.current = setTimeout(() => setError(false), 4000);
        return;
      }
    }

    const url = `${window.location.origin}/r/${token}`;

    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      if (copiedTimerRef.current !== null) clearTimeout(copiedTimerRef.current);
      copiedTimerRef.current = setTimeout(() => setCopied(false), 3000);
    } catch {
      // Clipboard access denied — show URL inline.
      setFallbackUrl(url);
    }
  }

  const baseButtonClass =
    "inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent";

  let buttonClass: string;
  if (error) {
    buttonClass = cn(baseButtonClass, "border text-red-400 border-red-400/50 hover:text-red-400");
  } else if (copied) {
    buttonClass = cn(baseButtonClass, "border text-green-500 border-green-500/50");
  } else if (loading) {
    buttonClass = cn(baseButtonClass, "border text-muted border-border cursor-not-allowed opacity-70");
  } else {
    buttonClass = cn(baseButtonClass, "border text-muted hover:text-accent border-border hover:border-accent/50");
  }

  function renderContent() {
    if (loading) {
      return (
        <>
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          {t("results.share.generating" as Parameters<typeof t>[0])}
        </>
      );
    }
    if (copied) {
      return (
        <>
          <Check className="h-3 w-3" aria-hidden="true" />
          <span role="status" aria-live="polite">
            {t("results.share.copied" as Parameters<typeof t>[0])}
          </span>
        </>
      );
    }
    if (error) {
      return (
        <>
          <Link2 className="h-3 w-3" aria-hidden="true" />
          {t("results.share.error" as Parameters<typeof t>[0])}
        </>
      );
    }
    return (
      <>
        <Link2 className="h-3 w-3" aria-hidden="true" />
        {t("results.share.button" as Parameters<typeof t>[0])}
      </>
    );
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        aria-label={t("results.share.button" as Parameters<typeof t>[0])}
        aria-busy={loading}
        className={buttonClass}
      >
        {renderContent()}
      </button>

      {/* Clipboard fallback: show URL as selectable text */}
      {fallbackUrl !== null && (
        <div className="flex items-center gap-1 text-xs text-muted">
          <span>{t("results.share.ready" as Parameters<typeof t>[0])}:</span>
          <span
            className="font-mono text-foreground break-all select-all cursor-text"
            role="status"
            aria-live="polite"
          >
            {fallbackUrl}
          </span>
        </div>
      )}
    </div>
  );
}
