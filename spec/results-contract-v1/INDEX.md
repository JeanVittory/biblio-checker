# Results Contract v1 — Specification Index

This folder is a Spec-Driven Development (SDD) suite defining the **normative** `results` JSON contract (v1) used by the system.

## Reading order

1. `01-overview/spec.md`
2. `02-json-shape/spec.md`
3. `03-enums/spec.md`
4. `04-matrices-and-nullability/spec.md`
5. `05-normative-rules/spec.md`
6. `06-json-schema-artifact/spec.md`
7. `07-backend-integration/spec.md`
8. `08-worker-persistence-contract/spec.md`
9. `09-frontend-integration/spec.md`
10. `10-examples-and-fixtures/spec.md`
11. `11-acceptance-and-validation/spec.md`

## Dependency graph (conceptual)

```
01 Overview
 └─ 02 JSON Shape
     ├─ 03 Enums
     ├─ 04 Matrices + Nullability
     └─ 05 Normative Rules
         └─ 06 JSON Schema Artifact
             ├─ 07 Backend Integration
             ├─ 08 Worker Persistence Contract
             ├─ 09 Frontend Integration
             └─ 10 Examples + Fixtures
                 └─ 11 Acceptance + Validation
```

## Suite “done” criteria

The suite is considered ready for implementation when:

- The contract is fully specified (no TBD fields, no ambiguous meanings).
- Enums are closed and matrices are explicit.
- JSON Schema requirements are precise enough to build a validator that rejects all invalid combinations.
- Valid and invalid examples are provided and mapped to specific rules.

