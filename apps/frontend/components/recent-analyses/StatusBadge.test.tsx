import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";
import { renderWithLocale } from "@/test-utils/renderWithLocale";

describe("StatusBadge — locale rendering", () => {
  it("renders 'queued' label in Spanish as 'En cola'", () => {
    renderWithLocale(<StatusBadge status="queued" />, "es");
    expect(screen.getByText("En cola")).toBeTruthy();
  });

  it("renders 'queued' label in Portuguese as 'Na fila'", () => {
    renderWithLocale(<StatusBadge status="queued" />, "pt");
    expect(screen.getByText("Na fila")).toBeTruthy();
  });

  it("renders 'queued' label in English as 'Queued'", () => {
    renderWithLocale(<StatusBadge status="queued" />, "en");
    expect(screen.getByText("Queued")).toBeTruthy();
  });

  it("renders 'running' in ES as 'En ejecución'", () => {
    renderWithLocale(<StatusBadge status="running" />, "es");
    expect(screen.getByText("En ejecución")).toBeTruthy();
  });

  it("renders 'running' in PT as 'Em execução'", () => {
    renderWithLocale(<StatusBadge status="running" />, "pt");
    expect(screen.getByText("Em execução")).toBeTruthy();
  });

  it("renders 'running' in EN as 'Running'", () => {
    renderWithLocale(<StatusBadge status="running" />, "en");
    expect(screen.getByText("Running")).toBeTruthy();
  });

  it("renders 'succeeded' in ES as 'Completado'", () => {
    renderWithLocale(<StatusBadge status="succeeded" />, "es");
    expect(screen.getByText("Completado")).toBeTruthy();
  });

  it("renders 'succeeded' in PT as 'Concluído'", () => {
    renderWithLocale(<StatusBadge status="succeeded" />, "pt");
    expect(screen.getByText("Concluído")).toBeTruthy();
  });

  it("renders 'failed' in EN as 'Failed'", () => {
    renderWithLocale(<StatusBadge status="failed" />, "en");
    expect(screen.getByText("Failed")).toBeTruthy();
  });

  it("renders 'expired' in ES as 'Expirado'", () => {
    renderWithLocale(<StatusBadge status="expired" />, "es");
    expect(screen.getByText("Expirado")).toBeTruthy();
  });

  it("renders 'expired' in EN as 'Expired'", () => {
    renderWithLocale(<StatusBadge status="expired" />, "en");
    expect(screen.getByText("Expired")).toBeTruthy();
  });
});
