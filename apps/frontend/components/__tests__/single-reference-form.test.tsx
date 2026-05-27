/**
 * Tests for <SingleReferenceForm>.
 *
 * Spec: spec/single-reference-text-check/06-input-component/spec.md
 * Spec: spec/single-reference-text-check/09-acceptance-and-validation/spec.md § C
 *
 * Framework: Vitest + @testing-library/react
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { SingleReferenceForm } from "@/components/single-reference-form";
import { renderWithLocale } from "@/test-utils/renderWithLocale";

// ---------------------------------------------------------------------------
// Mock the service so tests do not make real HTTP calls.
// ---------------------------------------------------------------------------

vi.mock("@/services/startTextAnalysisGateway", () => ({
  startTextAnalysisGatewayService: vi.fn(),
}));

import { startTextAnalysisGatewayService } from "@/services/startTextAnalysisGateway";

const mockService = startTextAnalysisGatewayService as ReturnType<typeof vi.fn>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** A valid reference text of exactly 20 characters. */
const MIN_VALID = "12345678901234567890";

/** A valid reference text longer than 60 characters. */
const LONG_REF =
  "Watson, J. D., & Crick, F. H. C. (1953). Molecular structure of nucleic acids. Nature, 171, 737–738.";

/** A 500-char string (maxes out rawTextPreview). */
const FIVE_HUNDRED_CHARS = "A".repeat(500);

/** A 501-char string that should be capped to 500 in rawTextPreview. */
const FIVE_HUNDRED_ONE_CHARS = "A".repeat(501);

/** Creates a mock successful Response with the given jobId / jobToken. */
function mockSuccessResponse(jobId = "job-1", jobToken = "tok-1") {
  return Promise.resolve(
    new Response(
      JSON.stringify({
        ok: true,
        success: true,
        message: "Analysis started successfully.",
        requestId: "req-1",
        backend: { jobId, jobToken, status: "queued", success: true, message: "ok" },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    )
  );
}

/** Creates a mock error Response with the given status and message. */
function mockErrorResponse(status: number, message: string) {
  return Promise.resolve(
    new Response(
      JSON.stringify({ ok: false, success: false, message }),
      { status, headers: { "Content-Type": "application/json" } }
    )
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SingleReferenceForm — rendering", () => {
  it("renders a textarea, character counter, disabled submit button, and status region", () => {
    renderWithLocale(
      <SingleReferenceForm onJobCreated={vi.fn()} />,
      "es"
    );

    // Textarea
    const textarea = screen.getByRole("textbox");
    expect(textarea).toBeTruthy();

    // Counter shows 0 / 2000
    expect(screen.getByText("0 / 2000")).toBeTruthy();

    // Submit button exists and is disabled (no text yet)
    const btn = screen.getByRole("button", { name: /Verificar/i });
    expect(btn).toBeTruthy();
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows the label text", () => {
    renderWithLocale(
      <SingleReferenceForm onJobCreated={vi.fn()} />,
      "es"
    );
    expect(screen.getByText("Pega tu cita bibliográfica")).toBeTruthy();
  });

  it("renders English strings when locale is 'en'", () => {
    renderWithLocale(
      <SingleReferenceForm onJobCreated={vi.fn()} />,
      "en"
    );
    expect(screen.getByText("Paste your bibliographic citation")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Verify/i })).toBeTruthy();
  });
});

describe("SingleReferenceForm — character counter and button enable", () => {
  it("button is disabled when textarea is empty", () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const btn = screen.getByRole("button", { name: /Verificar/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("button is disabled when trimmed text is 19 chars", () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "1234567890123456789" } });
    const btn = screen.getByRole("button", { name: /Verificar/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("button is enabled when trimmed text is 20 chars", () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    const btn = screen.getByRole("button", { name: /Verificar/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("button is enabled for a long reference", () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: LONG_REF } });
    const btn = screen.getByRole("button", { name: /Verificar/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("counter updates as user types", () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "hello" } });
    expect(screen.getByText("5 / 2000")).toBeTruthy();
  });
});

describe("SingleReferenceForm — validation: no network call for invalid input", () => {
  it("button is disabled (no submit possible) for all-whitespace input — paste.empty case", () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "   " } });

    // All-whitespace → trimmedLength=0 → button disabled → no network call possible.
    const btn = screen.getByRole("button", { name: /Verificar/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(mockService).not.toHaveBeenCalled();
  });

  it("button is disabled for 19-char input — paste.too_short case", () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "1234567890123456789" } }); // 19 chars
    const btn = screen.getByRole("button", { name: /Verificar/i }) as HTMLButtonElement;
    // 19 < 20 → button disabled → service cannot be called.
    expect(btn.disabled).toBe(true);
    expect(mockService).not.toHaveBeenCalled();
  });

});


describe("SingleReferenceForm — successful submission", () => {
  beforeEach(() => {
    mockService.mockImplementation(() => mockSuccessResponse("job-42", "tok-abc"));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("calls startTextAnalysisGatewayService once with correct payload on submit", async () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });

    const btn = screen.getByRole("button", { name: /Verificar/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(mockService).toHaveBeenCalledTimes(1);
    });

    const [payload] = mockService.mock.calls[0] as [Record<string, unknown>];
    expect(typeof payload.requestId).toBe("string");
    expect((payload.reference as Record<string, string>).rawText).toBe(MIN_VALID);
  });

  it("calls onJobCreated with correctly truncated displayName (≤60 chars)", async () => {
    const onJobCreated = vi.fn();
    renderWithLocale(<SingleReferenceForm onJobCreated={onJobCreated} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });

    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(onJobCreated).toHaveBeenCalledTimes(1);
    });

    const [, , displayName] = onJobCreated.mock.calls[0] as [string, string, string, string];
    // 20 chars → no truncation
    expect(displayName).toBe(MIN_VALID);
    expect(displayName.endsWith("…")).toBe(false);
  });

  it("calls onJobCreated with displayName truncated to 60 chars + ellipsis for long input", async () => {
    const onJobCreated = vi.fn();
    renderWithLocale(<SingleReferenceForm onJobCreated={onJobCreated} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: LONG_REF } });

    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(onJobCreated).toHaveBeenCalledTimes(1);
    });

    const [, , displayName, rawTextPreview] = onJobCreated.mock.calls[0] as [
      string,
      string,
      string,
      string,
    ];

    expect(displayName.length).toBeLessThanOrEqual(61); // 60 chars + "…"
    expect(displayName.endsWith("…")).toBe(true);
    expect(displayName).toBe(LONG_REF.slice(0, 60) + "…");

    // rawTextPreview is capped at 500 (no ellipsis)
    expect(rawTextPreview).toBe(LONG_REF.slice(0, 500));
    expect(rawTextPreview.endsWith("…")).toBe(false);
  });

  it("rawTextPreview is capped at exactly 500 chars for very long input", async () => {
    const onJobCreated = vi.fn();
    mockService.mockImplementation(() => mockSuccessResponse());
    renderWithLocale(<SingleReferenceForm onJobCreated={onJobCreated} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: FIVE_HUNDRED_ONE_CHARS } });

    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(onJobCreated).toHaveBeenCalledTimes(1);
    });

    const [, , , rawTextPreview] = onJobCreated.mock.calls[0] as [
      string,
      string,
      string,
      string,
    ];
    expect(rawTextPreview.length).toBe(500);
  });

  it("rawTextPreview equals full text when input is exactly 500 chars", async () => {
    const onJobCreated = vi.fn();
    mockService.mockImplementation(() => mockSuccessResponse());
    renderWithLocale(<SingleReferenceForm onJobCreated={onJobCreated} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: FIVE_HUNDRED_CHARS } });

    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(onJobCreated).toHaveBeenCalledTimes(1);
    });

    const [, , , rawTextPreview] = onJobCreated.mock.calls[0] as [
      string,
      string,
      string,
      string,
    ];
    expect(rawTextPreview).toBe(FIVE_HUNDRED_CHARS);
  });

  it("clears the textarea immediately after successful submission", async () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: LONG_REF } });

    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(textarea.value).toBe("");
    });
  });

  it("shows success banner after submit", async () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Cita enviada. La verás en Análisis Recientes.")
      ).toBeTruthy();
    });
  });

  /**
   * After a successful submit (triedSubmit=true), shortening the text below 20
   * shows the paste.too_short inline hint.
   */
  it("shows paste.too_short inline hint after a successful submit when text is then shortened", async () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");

    // Submit valid text.
    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));
    await waitFor(() => expect(mockService).toHaveBeenCalledTimes(1));

    // Type a short string (textarea was cleared on success, type fresh).
    fireEvent.change(textarea, { target: { value: "short" } }); // 5 chars < 20

    // triedSubmit=true + trimmedLength < 20 → inline hint.
    await waitFor(() => {
      expect(screen.getByText("La cita debe tener al menos 20 caracteres.")).toBeTruthy();
    });
  });

  /**
   * After a successful submit (triedSubmit=true), leaving the textarea empty (or whitespace)
   * shows the paste.empty inline hint.
   */
  it("shows paste.empty inline hint after a successful submit when textarea is left empty", async () => {
    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");

    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));
    await waitFor(() => expect(mockService).toHaveBeenCalledTimes(1));

    // Textarea was cleared on success — type whitespace to get paste.empty.
    fireEvent.change(textarea, { target: { value: "   " } });

    await waitFor(() => {
      expect(screen.getByText("Pega una cita para verificarla.")).toBeTruthy();
    });
  });
});

describe("SingleReferenceForm — QuotaExceededError from onJobCreated", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows storage_full error when onJobCreated throws QuotaExceededError", async () => {
    mockService.mockImplementation(() => mockSuccessResponse());

    const onJobCreated = vi.fn().mockImplementation(() => {
      throw new DOMException("QuotaExceededError", "QuotaExceededError");
    });

    renderWithLocale(
      <SingleReferenceForm onJobCreated={onJobCreated} />,
      "es"
    );

    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      // The storage_full message (truncated for match)
      expect(
        screen.getByText(/Tu navegador no tiene espacio/)
      ).toBeTruthy();
    });
  });
});

describe("SingleReferenceForm — network / backend errors", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows submit_failed when fetch rejects (network offline)", async () => {
    mockService.mockRejectedValue(new TypeError("Failed to fetch"));

    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/No pudimos enviar la cita/)
      ).toBeTruthy();
    });
  });

  it("shows backend_error when service returns a non-OK response with a message", async () => {
    mockService.mockImplementation(() =>
      mockErrorResponse(400, "Validation failed by server.")
    );

    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/El servidor rechazó la solicitud/)
      ).toBeTruthy();
    });
  });

  it("shows service_offline message when gateway returns code='service_offline'", async () => {
    mockService.mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: false,
            success: false,
            code: "service_offline",
            message: "Service temporarily unavailable",
          }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        )
      )
    );

    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/El servicio no está disponible en este momento/)
      ).toBeTruthy();
    });
  });

  it("falls back to backend_error when code is not service_offline (no-regression)", async () => {
    mockService.mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ok: false,
            success: false,
            code: "analysis_job_create_failed",
            message: "DB write failed.",
          }),
          { status: 502, headers: { "Content-Type": "application/json" } }
        )
      )
    );

    renderWithLocale(<SingleReferenceForm onJobCreated={vi.fn()} />, "es");
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: MIN_VALID } });
    fireEvent.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/El servidor rechazó la solicitud/)
      ).toBeTruthy();
    });
  });
});
