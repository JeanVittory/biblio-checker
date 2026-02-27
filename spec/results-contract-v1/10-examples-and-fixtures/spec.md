# Step 10 — Canonical Examples and Fixtures

## Scope

This spec defines canonical valid and invalid example payloads for Results Contract v1.

These examples are the “source of truth” for implementers to validate both:
- JSON Schema artifact validation (Step 06)
- Backend/frontend runtime validators (Steps 07 and 09)

## Requirements

### 1) Valid examples (MUST validate)

All examples MUST include:
- `schemaVersion: "1.0"`
- `reportLanguage: "es"`
- `pipeline`
- `summary` consistent with `references[]`
- `warnings: []` (or populated)

#### A) Valid — verified (high)

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 1,
      "likely_verified": 0,
      "ambiguous": 0,
      "not_found": 0,
      "suspicious": 0,
      "processing_error": 0
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Ejemplo con DOI exacto",
      "normalized": {
        "title": "Título real",
        "authors": ["Autor A"],
        "year": 2021,
        "venue": "Revista X",
        "doi": "10.1234/abcd.2021.001",
        "arxivId": null
      },
      "classification": "verified",
      "confidenceScore": 0.91,
      "confidenceBand": "very_high",
      "manualReviewRequired": false,
      "reasonCode": "exact_doi_match",
      "decisionReason": "El DOI coincide exactamente con un registro canónico.",
      "evidence": [
        {
          "source": "openalex",
          "matchType": "exact_doi_match",
          "score": 0.95,
          "matchedRecord": {
            "externalId": "W1234567890",
            "title": "Título real",
            "year": 2021,
            "doi": "10.1234/abcd.2021.001",
            "url": "https://openalex.org/W1234567890"
          }
        }
      ]
    }
  ],
  "warnings": []
}
```

#### B) Valid — likely_verified (medium)

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 0,
      "likely_verified": 1,
      "ambiguous": 0,
      "not_found": 0,
      "suspicious": 0,
      "processing_error": 0
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Ejemplo con metadatos fuertes sin DOI",
      "normalized": {
        "title": "Título candidato",
        "authors": ["Autor A", "Autor B"],
        "year": 2020,
        "venue": "Revista Y",
        "doi": null,
        "arxivId": null
      },
      "classification": "likely_verified",
      "confidenceScore": 0.72,
      "confidenceBand": "medium",
      "manualReviewRequired": false,
      "reasonCode": "strong_metadata_match",
      "decisionReason": "Existe una coincidencia fuerte por metadatos, pero no hay identificador canónico.",
      "evidence": [
        {
          "source": "scielo",
          "matchType": "strong_metadata_match",
          "score": 0.78,
          "matchedRecord": {
            "externalId": "S1234-56782020000100001",
            "title": "Título candidato",
            "year": 2020,
            "doi": null,
            "url": "https://www.scielo.org/..."
          }
        }
      ]
    }
  ],
  "warnings": []
}
```

#### C) Valid — ambiguous (low + manualReviewRequired=true)

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 0,
      "likely_verified": 0,
      "ambiguous": 1,
      "not_found": 0,
      "suspicious": 0,
      "processing_error": 0
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Referencia con múltiples candidatos",
      "normalized": {
        "title": "Título similar",
        "authors": ["Autor A"],
        "year": 2021,
        "venue": null,
        "doi": null,
        "arxivId": null
      },
      "classification": "ambiguous",
      "confidenceScore": 0.41,
      "confidenceBand": "low",
      "manualReviewRequired": true,
      "reasonCode": "multiple_plausible_candidates",
      "decisionReason": "Se encontraron múltiples coincidencias plausibles sin evidencia suficiente para confirmar una sola.",
      "evidence": [
        {
          "source": "openalex",
          "matchType": "strong_metadata",
          "score": 0.71,
          "matchedRecord": {
            "externalId": "W1234567890",
            "title": "Título candidato A",
            "year": 2021,
            "doi": null,
            "url": "https://openalex.org/W1234567890"
          }
        },
        {
          "source": "scielo",
          "matchType": "weak_metadata",
          "score": 0.48,
          "matchedRecord": {
            "externalId": "S1234-56782021000100001",
            "title": "Título candidato B",
            "year": 2020,
            "doi": null,
            "url": "https://www.scielo.org/..."
          }
        }
      ]
    }
  ],
  "warnings": []
}
```

#### D) Valid — not_found (very_low + manualReviewRequired=true)

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 0,
      "likely_verified": 0,
      "ambiguous": 0,
      "not_found": 1,
      "suspicious": 0,
      "processing_error": 0
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Referencia sin evidencia suficiente",
      "normalized": {
        "title": null,
        "authors": [],
        "year": null,
        "venue": null,
        "doi": null,
        "arxivId": null
      },
      "classification": "not_found",
      "confidenceScore": 0.08,
      "confidenceBand": "very_low",
      "manualReviewRequired": true,
      "reasonCode": "insufficient_metadata",
      "decisionReason": "La referencia no contiene metadatos suficientes para encontrar coincidencias confiables.",
      "evidence": []
    }
  ],
  "warnings": []
}
```

#### E) Valid — suspicious (high + manualReviewRequired=true)

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 0,
      "likely_verified": 0,
      "ambiguous": 0,
      "not_found": 0,
      "suspicious": 1,
      "processing_error": 0
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Referencia con DOI conflictivo",
      "normalized": {
        "title": "Título declarado",
        "authors": ["Autor A"],
        "year": 2022,
        "venue": null,
        "doi": "10.9999/conflict.2022.123",
        "arxivId": null
      },
      "classification": "suspicious",
      "confidenceScore": 0.81,
      "confidenceBand": "high",
      "manualReviewRequired": true,
      "reasonCode": "strong_doi_conflict",
      "decisionReason": "El DOI citado apunta a un trabajo incompatible con el título/año reportados.",
      "evidence": [
        {
          "source": "openalex",
          "matchType": "exact_doi_match",
          "score": 0.90,
          "matchedRecord": {
            "externalId": "W9999999999",
            "title": "Título incompatible",
            "year": 2017,
            "doi": "10.9999/conflict.2022.123",
            "url": "https://openalex.org/W9999999999"
          }
        }
      ]
    }
  ],
  "warnings": []
}
```

#### F) Valid — processing_error (null band/score + manualReviewRequired=true)

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 0,
      "likely_verified": 0,
      "ambiguous": 0,
      "not_found": 0,
      "suspicious": 0,
      "processing_error": 1
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Referencia que falló al procesarse",
      "normalized": {
        "title": null,
        "authors": [],
        "year": null,
        "venue": null,
        "doi": null,
        "arxivId": null
      },
      "classification": "processing_error",
      "confidenceScore": null,
      "confidenceBand": null,
      "manualReviewRequired": true,
      "reasonCode": "reference_processing_failure",
      "decisionReason": "Ocurrió un error interno al procesar esta referencia; no fue posible puntuar con evidencia suficiente.",
      "evidence": []
    }
  ],
  "warnings": []
}
```

### 2) Invalid examples (MUST fail validation)

Each invalid example MUST be rejected by schema validation and MUST be referenced in Step 11 validation.

#### I) Invalid — verified + very_low

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 1,
      "likely_verified": 0,
      "ambiguous": 0,
      "not_found": 0,
      "suspicious": 0,
      "processing_error": 0
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Caso inválido",
      "normalized": { "title": null, "authors": [], "year": null, "venue": null, "doi": null, "arxivId": null },
      "classification": "verified",
      "confidenceScore": 0.10,
      "confidenceBand": "very_low",
      "manualReviewRequired": false,
      "reasonCode": "exact_identifier_match",
      "decisionReason": "Esto debe fallar por matriz de compatibilidad.",
      "evidence": []
    }
  ],
  "warnings": []
}
```

#### II) Invalid — not_found + very_high

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 0,
      "likely_verified": 0,
      "ambiguous": 0,
      "not_found": 1,
      "suspicious": 0,
      "processing_error": 0
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Caso inválido",
      "normalized": { "title": null, "authors": [], "year": null, "venue": null, "doi": null, "arxivId": null },
      "classification": "not_found",
      "confidenceScore": 0.95,
      "confidenceBand": "very_high",
      "manualReviewRequired": true,
      "reasonCode": "no_match_any_source",
      "decisionReason": "Esto debe fallar por matriz de compatibilidad.",
      "evidence": []
    }
  ],
  "warnings": []
}
```

#### III) Invalid — processing_error with non-null band/score

```json
{
  "schemaVersion": "1.0",
  "reportLanguage": "es",
  "pipeline": { "name": "reference_verification_pipeline", "version": "v1" },
  "summary": {
    "totalReferencesDetected": 1,
    "totalReferencesAnalyzed": 1,
    "countsByClassification": {
      "verified": 0,
      "likely_verified": 0,
      "ambiguous": 0,
      "not_found": 0,
      "suspicious": 0,
      "processing_error": 1
    }
  },
  "references": [
    {
      "referenceId": "ref-001",
      "rawText": "Caso inválido",
      "normalized": { "title": null, "authors": [], "year": null, "venue": null, "doi": null, "arxivId": null },
      "classification": "processing_error",
      "confidenceScore": 0.20,
      "confidenceBand": "low",
      "manualReviewRequired": true,
      "reasonCode": "reference_processing_failure",
      "decisionReason": "Debe fallar: processing_error exige score/band null.",
      "evidence": []
    }
  ],
  "warnings": []
}
```

## Acceptance Criteria

- Implementers can use these examples to test JSON Schema validation and runtime parsing.
- Every example maps clearly to the compatibility rules in Step 04.

## Dependencies

- Steps 02–05 define the rules these examples must satisfy.

