"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";

interface FeatureLockedTooltipProps {
  message: string;
  children: ReactNode;
  className?: string;
}

/**
 * Wraps a disabled CTA and exposes the reason via a tooltip that works on
 * both desktop (hover) and mobile (tap toggle, dismiss on outside tap).
 *
 * The wrapper intercepts pointer events on the inner trigger so the wrapped
 * element cannot navigate or fire its own click handler.
 */
export function FeatureLockedTooltip({
  message,
  children,
  className,
}: FeatureLockedTooltipProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);
  const tooltipId = useId();

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current) return;
      if (containerRef.current.contains(event.target as Node)) return;
      close();
    };

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open, close]);

  const handleTriggerClick = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setOpen((prev) => !prev);
  }, []);

  return (
    <span
      ref={containerRef}
      className={cn("relative inline-flex", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span
        className="contents"
        onClick={handleTriggerClick}
        aria-describedby={open ? tooltipId : undefined}
      >
        {children}
      </span>
      {open && (
        <span
          role="tooltip"
          id={tooltipId}
          aria-live="polite"
          className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 w-max max-w-[260px] -translate-x-1/2 rounded-md border border-border bg-foreground px-3 py-2 text-center text-xs font-medium text-background shadow-lg"
        >
          {message}
        </span>
      )}
    </span>
  );
}
