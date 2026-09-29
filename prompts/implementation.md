# Implementation Prompt

Use this to build or extend a module in the local reference implementation under `04-reference-implementation/`. Fill in the bracketed values before use.

---

You are implementing a module for the repository's checked-in reference implementation, not for a production service. This is an educational implementation, not a product — it exists to make a specific engineering lesson concrete and measurable.

Engineering lesson this module demonstrates: [LESSON]
Production problem it solves: [PROBLEM]
Current local stack constraints: Python standard library only unless a future article explicitly adds a dependency. Broader ecosystem items such as FastAPI, LangGraph, Pydantic, Redis, PostgreSQL, OpenTelemetry, Docker, and GitHub Actions remain future research context unless they are added explicitly to the project configuration and CI.

Requirements:

- Implement only the documented lesson within the current local stack. Do not add FastAPI, LangGraph, Pydantic, Redis, PostgreSQL, OpenTelemetry, Docker, or other infrastructure unless a separately approved future article explicitly requires it and project configuration and CI are updated with it.
- Do not claim a measurable before-and-after unless a reproducible benchmark is implemented and run. Tests demonstrate behavior; they are not performance benchmarks.
- Keep the implementation proportionate to this educational repository. No client-specific logic, credentials, or production service scaffolding.
- Explain significant decisions in the matching article or ADR rather than adding comments that merely narrate code.
- Include tests for the behavior and failure mode the module addresses, not only a happy path.
- If a required dependency or infrastructure choice is outside the current stack, describe it as a future extension and stop before adding it.

Implement the module now, and note explicitly which parts of this module correspond to which section of the matching article.
