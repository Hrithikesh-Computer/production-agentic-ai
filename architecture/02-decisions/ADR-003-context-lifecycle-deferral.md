# ADR-003: Defer Persistent Context Lifecycle

- **Status:** Proposed; consistent with the repository's existing deferral
- **Date:** 2026-10-03
- **Decision owner:** Product/workflow and data-governance owners to be assigned

## Context

The context article is research, not a runnable context manager. The repository's decision record deferred a context prototype because available workflows did not provide a representative multi-turn context stream, state store, or retention workload. The CRM mock currently processes a customer-ID request and has no cross-turn state.

The proposed CRM architecture introduces sensitive account and opportunity data, approval state, and model context. Persisting memory before defining purpose, data classes, access rules, retention, deletion, and evidence provenance could silently convert transient CRM data into unmanaged long-lived state.

## Options

1. Persist all conversation and tool history: easiest to implement, maximizes recoverability, and increases exposure, retention, and stale-context risk.
2. Add a summarizing/semantic memory layer immediately: may reduce prompt size, but requires a representative workload and quality evaluation; compression can lose constraints and rationale.
3. Defer general persistent agent memory: retain only workflow state required to complete a single request/approval, with explicit customer-owned retention; revisit after representative multi-turn evidence exists.

## Decision

Defer general-purpose persistent agent memory and context summarization. The first CRM workflow should use request-scoped context and separately modeled approval/audit records with explicit retention owners. Do not infer that approval records or audit data are “memory”; they have distinct purpose, access, integrity, and retention requirements.

## Consequences

- The initial design cannot promise cross-session personalization or long-term conversational recall.
- Request-scoped data still needs minimization, access controls, logging policy, and deletion behavior.
- Before adding memory, select a real workflow, identify testimonial versus derivable information, define retention/deletion and conflict rules, and evaluate retrieval/summary quality.
- This decision aligns with the repository's [context lifecycle decision](../../CONTEXT-LIFECYCLE-DECISION.md), but applying it to the CRM target remains a proposed design choice.

## Evidence and gaps

- [Context lifecycle research note](../../02-context-and-memory/01-beyond-token-windows.md).
- [Repository deferral rationale](../../CONTEXT-LIFECYCLE-DECISION.md).
- Customer retention policy, legal hold, deletion SLA, permitted model-provider data use, and representative multi-turn CRM tasks: **not found in repo; discovery required**.
