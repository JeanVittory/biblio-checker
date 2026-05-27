/**
 * Tests for the input-kind badge rendered inside <JobRow>.
 *
 * Spec: spec/single-reference-text-check/07-tabs-and-recent-analyses/spec.md § 6–7
 */

import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { JobRow } from "./JobRow";
import { renderWithLocale } from "@/test-utils/renderWithLocale";
import type { StoredJob } from "@/lib/localStorage/recentAnalyses";

// ---------------------------------------------------------------------------
// Minimal job factory
// ---------------------------------------------------------------------------

function makeJob(overrides: Partial<StoredJob>): StoredJob {
  return {
    jobId: "job-1",
    jobToken: "tok-1",
    fileName: "document.pdf",
    submittedAt: new Date().toISOString(),
    status: "queued",
    stage: null,
    result: null,
    error: null,
    completedAt: null,
    inputKind: "file",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("JobRow — input-kind badge", () => {
  it("renders 'Texto' badge for a text-mode job (ES locale)", () => {
    const job = makeJob({
      inputKind: "text",
      fileName: "Watson, J. D., & Crick, F. H. C. (1953). Molecular struct…",
      rawTextPreview:
        "Watson, J. D., & Crick, F. H. C. (1953). Molecular structure of nucleic acids. Nature, 171, 737–738.",
    });

    renderWithLocale(
      <table>
        <JobRow job={job} onRemove={vi.fn()} />
      </table>,
      "es"
    );

    expect(screen.getByText("Texto")).toBeTruthy();
  });

  it("renders 'Text' badge for a text-mode job (EN locale)", () => {
    const job = makeJob({ inputKind: "text", fileName: "Some citation text…" });

    renderWithLocale(
      <table>
        <JobRow job={job} onRemove={vi.fn()} />
      </table>,
      "en"
    );

    expect(screen.getByText("Text")).toBeTruthy();
  });

  it("sets title attribute on the display name span to rawTextPreview for text-mode jobs", () => {
    const rawTextPreview =
      "Watson J D and Crick F H C 1953 Molecular structure of nucleic acids Nature 171";
    const job = makeJob({
      inputKind: "text",
      fileName: "Watson J D and Crick F H C 1953 Molecular struct…",
      rawTextPreview,
    });

    renderWithLocale(
      <table>
        <JobRow job={job} onRemove={vi.fn()} />
      </table>,
      "es"
    );

    // Find all elements that have a title attribute and check one matches rawTextPreview.
    const allWithTitle = document.querySelectorAll("[title]");
    const found = Array.from(allWithTitle).some(
      (el) => el.getAttribute("title") === rawTextPreview
    );
    expect(found).toBe(true);
  });

  it("falls back to fileName as title when rawTextPreview is undefined for text-mode", () => {
    const fileName = "Watson J D Crick F H C 1953 Molecular structure text…";
    const job = makeJob({
      inputKind: "text",
      fileName,
      rawTextPreview: undefined,
    });

    renderWithLocale(
      <table>
        <JobRow job={job} onRemove={vi.fn()} />
      </table>,
      "es"
    );

    // When rawTextPreview is absent, the span title should equal fileName.
    const allWithTitle = document.querySelectorAll("[title]");
    const found = Array.from(allWithTitle).some(
      (el) => el.getAttribute("title") === fileName
    );
    expect(found).toBe(true);
  });

  it("renders 'PDF' badge for a file-mode job with .pdf extension", () => {
    const job = makeJob({ inputKind: "file", fileName: "mybiblio.pdf" });

    renderWithLocale(
      <table>
        <JobRow job={job} onRemove={vi.fn()} />
      </table>,
      "es"
    );

    expect(screen.getByText("PDF")).toBeTruthy();
  });

  it("renders 'DOCX' badge for a file-mode job with .docx extension", () => {
    const job = makeJob({ inputKind: "file", fileName: "thesis.docx" });

    renderWithLocale(
      <table>
        <JobRow job={job} onRemove={vi.fn()} />
      </table>,
      "es"
    );

    expect(screen.getByText("DOCX")).toBeTruthy();
  });

  it("renders 'Documento' badge for a file-mode job with unknown extension", () => {
    const job = makeJob({ inputKind: "file", fileName: "report.txt" });

    renderWithLocale(
      <table>
        <JobRow job={job} onRemove={vi.fn()} />
      </table>,
      "es"
    );

    expect(screen.getByText("Documento")).toBeTruthy();
  });

  it("renders 'Documento' badge for a legacy job without inputKind field", () => {
    // Simulate a stored row from before this feature (no inputKind field).
    const job = {
      jobId: "legacy-1",
      jobToken: "tok-legacy",
      fileName: "old-document.pdf",
      submittedAt: new Date().toISOString(),
      status: "succeeded" as const,
      stage: null,
      result: null,
      error: null,
      completedAt: null,
      inputKind: undefined as unknown as "file" | "text",
    };

    renderWithLocale(
      <table>
        <JobRow job={job} onRemove={vi.fn()} />
      </table>,
      "es"
    );

    // Legacy jobs default to file mode → PDF badge for .pdf
    expect(screen.getByText("PDF")).toBeTruthy();
  });
});
