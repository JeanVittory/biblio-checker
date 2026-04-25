import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExpandedDetail } from "./ExpandedDetail";
import { renderWithLocale } from "@/test-utils/renderWithLocale";
import type { StoredJob } from "@/lib/localStorage/recentAnalyses";
import type { ResultsV1 } from "@/lib/schemas/resultsV1";

const SENTINEL_DECISION_REASON = "SENTINEL_UNTRANSLATED_DECISION_REASON";

const baseResult: ResultsV1 = {
  schemaVersion: "1.0",
  reportLanguage: "es",
  pipeline: { name: "test", version: "1.0" },
  summary: {
    totalReferencesDetected: 1,
    totalReferencesAnalyzed: 1,
    countsByClassification: {
      verified: 1,
      likely_verified: 0,
      ambiguous: 0,
      not_found: 0,
      suspicious: 0,
      processing_error: 0,
    },
  },
  references: [
    {
      referenceId: "ref-1",
      rawText: "Some raw reference text",
      normalized: {
        title: "Test Paper Title",
        authors: ["Author A"],
        year: 2023,
        venue: null,
        doi: null,
        arxivId: null,
      },
      classification: "verified",
      confidenceScore: 0.95,
      confidenceBand: "very_high",
      manualReviewRequired: false,
      reasonCode: "exact_doi_match",
      decisionReason: SENTINEL_DECISION_REASON,
      evidence: [],
    },
  ],
  warnings: [],
};

const succeededJob: StoredJob = {
  jobId: "job-1",
  jobToken: "token-1",
  fileName: "test.pdf",
  submittedAt: new Date().toISOString(),
  status: "succeeded",
  stage: null,
  result: baseResult,
  error: null,
  completedAt: new Date().toISOString(),
};

const queuedJob: StoredJob = {
  ...succeededJob,
  status: "queued",
  result: null,
  completedAt: null,
};

describe("ExpandedDetail — status states", () => {
  it("renders waiting message in Spanish for queued job", () => {
    renderWithLocale(<ExpandedDetail job={queuedJob} panelId="panel" />, "es");
    expect(screen.getByText("Esperando para ser procesado…")).toBeTruthy();
  });

  it("renders waiting message in Portuguese for queued job", () => {
    renderWithLocale(<ExpandedDetail job={queuedJob} panelId="panel" />, "pt");
    expect(screen.getByText("Aguardando processamento…")).toBeTruthy();
  });

  it("renders waiting message in English for queued job", () => {
    renderWithLocale(<ExpandedDetail job={queuedJob} panelId="panel" />, "en");
    expect(screen.getByText("Waiting to be processed…")).toBeTruthy();
  });
});

const runningJob: StoredJob = {
  ...succeededJob,
  status: "running",
  stage: null,
  result: null,
  completedAt: null,
};

const runningJobWithStage: StoredJob = {
  ...runningJob,
  stage: "extract",
};

describe("ExpandedDetail — running state (i18n)", () => {
  it("renders processing_started label in English when no stage", () => {
    renderWithLocale(<ExpandedDetail job={runningJob} panelId="panel" />, "en");
    expect(screen.getByText(/Processing/)).toBeTruthy();
    expect(screen.getByText(/started .+ ago/)).toBeTruthy();
  });

  it("renders processing_started label in Spanish when no stage", () => {
    renderWithLocale(<ExpandedDetail job={runningJob} panelId="panel" />, "es");
    expect(screen.getByText(/Procesando/)).toBeTruthy();
    expect(screen.getByText(/comenz\u00f3 hace/)).toBeTruthy();
  });

  it("renders processing_started label in Portuguese when no stage", () => {
    renderWithLocale(<ExpandedDetail job={runningJob} panelId="panel" />, "pt");
    expect(screen.getByText(/Processando/)).toBeTruthy();
    expect(screen.getByText(/iniciado h\u00e1/)).toBeTruthy();
  });

  it("renders processing_elapsed label in English when stage is present", () => {
    renderWithLocale(<ExpandedDetail job={runningJobWithStage} panelId="panel" />, "en");
    expect(screen.getByText(/processing for/)).toBeTruthy();
  });

  it("renders processing_elapsed label in Spanish when stage is present", () => {
    renderWithLocale(<ExpandedDetail job={runningJobWithStage} panelId="panel" />, "es");
    expect(screen.getByText(/procesando desde hace/)).toBeTruthy();
  });

  it("renders processing_elapsed label in Portuguese when stage is present", () => {
    renderWithLocale(<ExpandedDetail job={runningJobWithStage} panelId="panel" />, "pt");
    expect(screen.getByText(/processando h\u00e1/)).toBeTruthy();
  });
});

describe("ExpandedDetail — succeeded with results", () => {
  it("renders 'Analysis Result' section heading in Spanish", () => {
    renderWithLocale(<ExpandedDetail job={succeededJob} panelId="panel" />, "es");
    expect(screen.getAllByText("Resultado del análisis").length).toBeGreaterThan(0);
  });

  it("renders 'Analysis Result' section heading in English", () => {
    renderWithLocale(<ExpandedDetail job={succeededJob} panelId="panel" />, "en");
    expect(screen.getAllByText("Analysis Result").length).toBeGreaterThan(0);
  });

  it("renders classification label from catalog — not hardcoded Spanish", async () => {
    const user = userEvent.setup();
    renderWithLocale(<ExpandedDetail job={succeededJob} panelId="panel" />, "pt");
    // Click the reference card to expand it (first button — export buttons follow)
    const refButton = screen.getAllByRole("button")[0];
    await user.click(refButton);
    // "Verificada" is the PT translation for "verified" — may appear more than once
    expect(screen.getAllByText("Verificada").length).toBeGreaterThan(0);
  });

  it("renders decisionReason verbatim (not translated)", async () => {
    const user = userEvent.setup();
    renderWithLocale(<ExpandedDetail job={succeededJob} panelId="panel" />, "en");
    const refButton = screen.getAllByRole("button")[0];
    await user.click(refButton);
    // The sentinel value must appear as-is — the worker pre-translates it
    expect(screen.getByText(SENTINEL_DECISION_REASON)).toBeTruthy();
  });
});

describe("ExpandedDetail — section headings per locale", () => {
  it("shows 'Campos normalizados' for normalized fields in Spanish", async () => {
    const user = userEvent.setup();
    renderWithLocale(<ExpandedDetail job={succeededJob} panelId="panel" />, "es");
    await user.click(screen.getAllByRole("button")[0]);
    expect(screen.getByText("Campos normalizados")).toBeTruthy();
  });

  it("shows 'Normalized fields' in English", async () => {
    const user = userEvent.setup();
    renderWithLocale(<ExpandedDetail job={succeededJob} panelId="panel" />, "en");
    await user.click(screen.getAllByRole("button")[0]);
    expect(screen.getByText("Normalized fields")).toBeTruthy();
  });
});

/**
 * Cross-locale immutability invariant (Step 01 §6):
 * Chrome labels must follow the active UI locale (EN here), while
 * decisionReason is rendered verbatim in the job's original locale (PT).
 * The worker pre-translates it; the frontend must never re-wrap it in t().
 */
describe("ExpandedDetail — cross-locale immutability invariant", () => {
  const PT_DECISION_REASON =
    "O DOI 10.1/x corresponde a 'Example Title' (2023) em OpenAlex.";

  const ptResult: ResultsV1 = {
    schemaVersion: "1.0",
    reportLanguage: "pt",
    pipeline: { name: "test", version: "1.0" },
    summary: {
      totalReferencesDetected: 1,
      totalReferencesAnalyzed: 1,
      countsByClassification: {
        verified: 1,
        likely_verified: 0,
        ambiguous: 0,
        not_found: 0,
        suspicious: 0,
        processing_error: 0,
      },
    },
    references: [
      {
        referenceId: "ref-pt",
        rawText: "Some raw reference text",
        normalized: {
          title: "Example Title",
          authors: ["Author A"],
          year: 2023,
          venue: null,
          doi: "10.1/x",
          arxivId: null,
        },
        classification: "verified",
        confidenceScore: 0.95,
        confidenceBand: "very_high",
        manualReviewRequired: false,
        reasonCode: "exact_doi_match",
        decisionReason: PT_DECISION_REASON,
        evidence: [],
      },
    ],
    warnings: [],
  };

  const ptJobRenderedInEn: StoredJob = {
    jobId: "job-pt",
    jobToken: "token-pt",
    fileName: "test.pdf",
    submittedAt: new Date().toISOString(),
    status: "succeeded",
    stage: null,
    result: ptResult,
    error: null,
    completedAt: new Date().toISOString(),
  };

  it("renders Chrome labels in English when UI locale is EN", async () => {
    const user = userEvent.setup();
    renderWithLocale(
      <ExpandedDetail job={ptJobRenderedInEn} panelId="panel-cross" />,
      "en"
    );
    await user.click(screen.getAllByRole("button")[0]);
    // Chrome label: "Decision reason" must appear in English
    expect(screen.getByText("Decision reason")).toBeTruthy();
    // Chrome label: "Normalized fields" in English
    expect(screen.getByText("Normalized fields")).toBeTruthy();
    // Classification label: "Verified" (English)
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
  });

  it("renders decisionReason verbatim in Portuguese even when UI locale is EN", async () => {
    const user = userEvent.setup();
    renderWithLocale(
      <ExpandedDetail job={ptJobRenderedInEn} panelId="panel-cross2" />,
      "en"
    );
    await user.click(screen.getAllByRole("button")[0]);
    // Portuguese decisionReason from the worker must appear unchanged
    expect(screen.getByText(PT_DECISION_REASON)).toBeTruthy();
    // Must NOT appear translated into English
    expect(screen.queryByText(/DOI.*matches.*Example Title.*in OpenAlex/i)).toBeNull();
  });
});
