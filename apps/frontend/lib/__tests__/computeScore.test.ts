import { describe, it, expect } from "vitest";
import { computeScore } from "@/lib/computeScore";
import type { CountsByClassification } from "@/lib/computeScore";

function counts(overrides: Partial<CountsByClassification> = {}): CountsByClassification {
  return {
    verified: 0,
    likely_verified: 0,
    ambiguous: 0,
    not_found: 0,
    suspicious: 0,
    processing_error: 0,
    ...overrides,
  };
}

describe("computeScore", () => {
  it("all verified → score=100, band='high'", () => {
    expect(computeScore(counts({ verified: 5 }))).toEqual({ score: 100, band: "high" });
  });

  it("all not_found → score=0, band='low'", () => {
    expect(computeScore(counts({ not_found: 5 }))).toEqual({ score: 0, band: "low" });
  });

  it("all likely_verified → score=75, band='medium'", () => {
    expect(computeScore(counts({ likely_verified: 4 }))).toEqual({ score: 75, band: "medium" });
  });

  it("all ambiguous → score=25, band='low'", () => {
    expect(computeScore(counts({ ambiguous: 3 }))).toEqual({ score: 25, band: "low" });
  });

  it("all processing_error → score=0, band='low'", () => {
    expect(computeScore(counts({ processing_error: 10 }))).toEqual({ score: 0, band: "low" });
  });

  it("zero total → score=0, band='low'", () => {
    expect(computeScore(counts())).toEqual({ score: 0, band: "low" });
  });

  it("mix: 3 verified + 2 not_found + 1 ambiguous → score=54, band='medium'", () => {
    // eligible=6, weightedSum = 3×1.0 + 0 + 1×0.25 = 3.25
    // score = round((3.25/6)*100) = round(54.166…) = 54
    expect(computeScore(counts({ verified: 3, not_found: 2, ambiguous: 1 }))).toEqual({
      score: 54,
      band: "medium",
    });
  });

  it("4 verified + 1 processing_error → score=100, band='high' (processing_error excluded)", () => {
    // eligible=4 (processing_error excluded), weightedSum=4×1.0=4
    // score = round((4/4)*100) = 100
    expect(computeScore(counts({ verified: 4, processing_error: 1 }))).toEqual({
      score: 100,
      band: "high",
    });
  });

  it("boundary: score exactly 80 → band='high'", () => {
    // Need score = round((w/e)*100) = 80
    // 4 verified + 1 likely_verified: eligible=5, weightedSum=4+0.75=4.75, score=round(95)=95 — not 80
    // Try: 8 verified + 2 not_found: eligible=10, weightedSum=8, score=80
    expect(computeScore(counts({ verified: 8, not_found: 2 }))).toEqual({
      score: 80,
      band: "high",
    });
  });

  it("boundary: score exactly 50 → band='medium'", () => {
    // 2 verified + 2 not_found: eligible=4, weightedSum=2, score=round(50)=50
    expect(computeScore(counts({ verified: 2, not_found: 2 }))).toEqual({
      score: 50,
      band: "medium",
    });
  });
});
