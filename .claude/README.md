# Claude Sub-Agents (SDD Workflow)

This repo includes a set of **Claude sub-agents** under `.claude/agents/`.

These files are **prompts/roles** intended for tooling that supports selecting a specialized agent (e.g., Product Manager vs. QA) while working in a **Spec-Driven Development (SDD)** workflow.

## Agents

| File | Role | When to use |
| --- | --- | --- |
| `.claude/agents/product-manager.md` | Product spec writer | Turn an idea into a functional spec (the “what/why”), no code. |
| `.claude/agents/technical-lead.md` | Spec gatekeeper | Review a set of specs for coherence/feasibility before implementation. |
| `.claude/agents/frontend-developer.md` | Frontend implementer | Implement UI against approved specs/contracts. |
| `.claude/agents/backend-developer.md` | Backend implementer | Implement APIs/workers against approved specs/contracts. |
| `.claude/agents/qa-developer.md` | Spec → test cases | Validate an implementation against the approved spec set. |
| `.claude/agents/security-dev-expert.md` | Security review | Threat model / secure review of sensitive code and contracts. |

## How this fits in this repo

Typical flow:

1. **Product**: create/update feature requirements in `spec/<feature>/`.
2. **Tech lead**: review `spec/<feature>/` for readiness.
3. **Dev**: implement across `apps/frontend`, `apps/backend`, `apps/worker`.
4. **QA**: validate behavior vs. spec acceptance criteria.

See `spec/README.md` for how SDD suites are structured.

