"use client";

import { useState, useRef, useCallback, useId, useEffect } from "react";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { startTextAnalysisGatewayService } from "@/services/startTextAnalysisGateway";
import logger from "@/lib/logger";

const log = logger.child({ module: "single-reference-form" });

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SubmitStatus =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success" }
  | { kind: "error"; message: string };

export interface SingleReferenceFormProps {
  /**
   * Called with four args when a job is successfully created.
   * - jobId: backend job identifier
   * - jobToken: polling token
   * - displayName: trimmed text ≤60 chars + ellipsis when longer
   * - rawTextPreview: trimmed text sliced to 500 chars (no ellipsis)
   */
  onJobCreated: (
    jobId: string,
    jobToken: string,
    displayName: string,
    rawTextPreview: string
  ) => void;
  /** Disables all interactive elements (e.g. when upload is feature-locked). */
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Form that lets a user paste a single bibliographic reference and submit it
 * for text-mode analysis.
 *
 * Spec: spec/single-reference-text-check/06-input-component/spec.md
 *
 * XSS / render safety (§ 7a): displayName and rawTextPreview are derived from
 * untrusted user input and MUST be rendered exclusively as React text nodes.
 * No dangerouslySetInnerHTML or innerHTML anywhere in this component.
 */
export function SingleReferenceForm({
  onJobCreated,
  disabled = false,
}: SingleReferenceFormProps) {
  const t = useTranslations();
  const [text, setText] = useState<string>("");
  const [status, setStatus] = useState<SubmitStatus>({ kind: "idle" });
  // Only show validation hints after the first failed submit attempt.
  const [triedSubmit, setTriedSubmit] = useState(false);
  // Banner visibility timer — independent of text clearing.
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Mounted ref prevents stale state updates after unmount.
  const mountedRef = useRef(true);

  const textareaId = useId();
  const hintId = `${textareaId}-hint`;
  const statusId = `${textareaId}-status`;

  // Track mount state to avoid stale setState on unmount (§ 10).
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (successTimerRef.current !== null) {
        clearTimeout(successTimerRef.current);
      }
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  const trimmed = text.trim();
  const trimmedLength = trimmed.length;
  const isSubmitting = status.kind === "submitting";
  const isDisabled = disabled || isSubmitting;

  // Inline validation hint (only shown after first failed submit).
  let validationHint: string | null = null;
  if (triedSubmit) {
    if (trimmedLength === 0) {
      validationHint = t("paste.empty");
    } else if (trimmedLength < 20) {
      validationHint = t("paste.too_short");
    } else if (trimmedLength > 2000) {
      validationHint = t("paste.too_long");
    }
  }

  // ---------------------------------------------------------------------------
  // Submission flow (§ 5)
  // ---------------------------------------------------------------------------

  const handleSubmit = useCallback(async () => {
    setTriedSubmit(true);

    const currentTrimmed = text.trim();

    // Step 1 — client-side validation.
    if (currentTrimmed.length === 0) {
      setStatus({ kind: "error", message: t("paste.empty") });
      return;
    }
    if (currentTrimmed.length < 20) {
      setStatus({ kind: "error", message: t("paste.too_short") });
      return;
    }
    if (currentTrimmed.length > 2000) {
      setStatus({ kind: "error", message: t("paste.too_long") });
      return;
    }

    // Step 2 — set submitting state.
    setStatus({ kind: "submitting" });

    // Step 3 — generate requestId.
    const requestId =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : generateFallbackUUID();

    // Step 4 — build payload.
    const payload = {
      requestId,
      reference: { rawText: currentTrimmed },
    };

    try {
      // Step 5 — call service.
      const response = await startTextAnalysisGatewayService(payload);

      if (!mountedRef.current) return;

      // Step 6 — handle non-OK response.
      if (!response.ok) {
        let errorMessage = t("paste.submit_failed");
        try {
          const body = (await response.json()) as Record<string, unknown>;

          const topLevelCode = typeof body.code === "string" ? body.code : null;
          const backendObj =
            typeof body.backend === "object" && body.backend !== null
              ? (body.backend as Record<string, unknown>)
              : null;
          const nestedCode =
            backendObj !== null && typeof backendObj.code === "string"
              ? backendObj.code
              : null;

          if (topLevelCode === "service_offline" || nestedCode === "service_offline") {
            errorMessage = t("errors.service_offline");
          } else if (typeof body.message === "string" && body.message.length > 0) {
            errorMessage = t("paste.backend_error", { message: body.message });
          }
        } catch {
          // Non-JSON error body — use default.
        }
        if (mountedRef.current) {
          setStatus({ kind: "error", message: errorMessage });
        }
        return;
      }

      // Step 7 — parse success response.
      const body = (await response.json()) as Record<string, unknown>;
      const backend =
        typeof body.backend === "object" && body.backend !== null
          ? (body.backend as Record<string, unknown>)
          : null;

      const jobId = backend !== null && typeof backend.jobId === "string" ? backend.jobId : null;
      const jobToken =
        backend !== null && typeof backend.jobToken === "string" ? backend.jobToken : null;

      if (!mountedRef.current) return;

      if (jobId === null || jobToken === null) {
        setStatus({ kind: "error", message: t("paste.backend_error", { message: "Missing job data." }) });
        return;
      }

      // Compute displayName and rawTextPreview from the single trimmed source.
      // User-supplied; React text-node escaping is the only XSS defense.
      const displayName =
        currentTrimmed.length > 60
          ? currentTrimmed.slice(0, 60) + "…"
          : currentTrimmed;
      // User-supplied; React text-node escaping is the only XSS defense.
      const rawTextPreview = currentTrimmed.slice(0, 500);

      // Call onJobCreated inside try/catch to handle QuotaExceededError.
      try {
        onJobCreated(jobId, jobToken, displayName, rawTextPreview);
      } catch (trackingError) {
        if (
          trackingError instanceof DOMException &&
          trackingError.name === "QuotaExceededError"
        ) {
          if (mountedRef.current) {
            setStatus({ kind: "error", message: t("paste.storage_full") });
          }
          return;
        }
        // Non-fatal tracking error — log but treat submission as successful.
        log.warn({ err: trackingError }, "onJobCreated threw non-quota error; treating as success");
      }

      if (!mountedRef.current) return;

      // Clear text immediately on success; banner stays 2s independently.
      setText("");
      setStatus({ kind: "success" });

      // Reset status to idle after 2 seconds, independent of text clearing.
      successTimerRef.current = setTimeout(() => {
        if (mountedRef.current) {
          setStatus({ kind: "idle" });
        }
      }, 2_000);
    } catch {
      if (mountedRef.current) {
        setStatus({ kind: "error", message: t("paste.submit_failed") });
      }
    }
  }, [text, t, onJobCreated]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Allow Ctrl/Cmd+Enter to submit from the textarea.
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (!isDisabled && trimmedLength >= 20) {
          void handleSubmit();
        }
      }
    },
    [isDisabled, trimmedLength, handleSubmit]
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="w-full space-y-4">
      {/* Label */}
      <label
        htmlFor={textareaId}
        className="block text-sm font-medium text-foreground"
      >
        {t("paste.label")}
      </label>

      {/* Helper text */}
      <p className="text-xs text-muted -mt-3">{t("paste.helper")}</p>

      {/* Textarea */}
      <textarea
        id={textareaId}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("paste.placeholder")}
        maxLength={2000}
        rows={5}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        aria-describedby={`${hintId} ${statusId}`}
        className={cn(
          "w-full rounded-xl border border-border bg-surface px-4 py-3",
          "text-sm text-foreground placeholder:text-muted",
          "resize-y min-h-[7rem]",
          "focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/60",
          "transition-colors duration-200",
          isDisabled && "cursor-not-allowed opacity-50"
        )}
      />

      {/* Character counter */}
      <p
        id={hintId}
        className={cn(
          "text-xs text-right",
          trimmedLength < 20 && trimmedLength > 0 ? "text-amber-400" : "text-muted"
        )}
        aria-live="polite"
      >
        {/* User-supplied count displayed as a number — safe as React text node */}
        {t("paste.counter", { count: trimmedLength })}
      </p>

      {/* Inline validation hint (only after first failed submit) */}
      {validationHint !== null && (
        <p
          className="text-xs text-red-400"
          role="alert"
        >
          {validationHint}
        </p>
      )}

      {/* Submit button */}
      <button
        type="button"
        onClick={() => { void handleSubmit(); }}
        disabled={isDisabled || trimmedLength < 20}
        aria-disabled={isDisabled || trimmedLength < 20}
        className={cn(
          "glow-effect w-full rounded-lg px-6 py-2.5 text-sm font-medium text-white transition-colors",
          isDisabled || trimmedLength < 20
            ? "cursor-not-allowed opacity-50"
            : "cursor-pointer"
        )}
        style={{
          background: "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
        }}
      >
        {isSubmitting ? t("paste.submitting") : t("paste.submit")}
      </button>

      {/* Status banner */}
      <div
        id={statusId}
        role="status"
        aria-live="polite"
        className="w-full"
      >
        {status.kind === "submitting" && (
          <div className="animate-slide-up flex items-center gap-2 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden="true" />
            <span>{t("paste.submitting")}</span>
          </div>
        )}

        {status.kind === "success" && (
          <div
            className={cn(
              "animate-slide-up flex items-center gap-2 rounded-lg border p-4",
              "border-green-500/30 bg-green-500/5 text-green-400"
            )}
          >
            <CheckCircle2 className="h-5 w-5 shrink-0" aria-hidden="true" />
            <span className="text-sm">{t("paste.success")}</span>
          </div>
        )}

        {status.kind === "error" && (
          <div
            className={cn(
              "animate-slide-up flex items-center gap-2 rounded-lg border p-4",
              "border-red-500/30 bg-red-500/5 text-red-400"
            )}
          >
            <XCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
            {/* User-supplied; React text-node escaping is the only XSS defense. */}
            <span className="text-sm">{status.message}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Fallback UUID v4 generator
// Used only when crypto.randomUUID() is unavailable (very old browsers).
// Produces a v4 UUID-shaped string; not cryptographically strong.
// ---------------------------------------------------------------------------

function generateFallbackUUID(): string {
  const randHex = (bytes: number) =>
    Array.from({ length: bytes }, () =>
      Math.floor(Math.random() * 256)
        .toString(16)
        .padStart(2, "0")
    ).join("");

  const b = randHex(16).split("");
  // Set version 4
  b[12] = "4";
  // Set variant bits
  b[16] = ((parseInt(b[16], 16) & 0x3) | 0x8).toString(16);

  const s = b.join("");
  return (
    s.slice(0, 8) +
    "-" +
    s.slice(8, 12) +
    "-" +
    s.slice(12, 16) +
    "-" +
    s.slice(16, 20) +
    "-" +
    s.slice(20, 32)
  );
}
