# Production Agentic AI

**Building Reliable Agentic AI Systems**

This repository documents the engineering of production Agentic AI systems: how autonomous agents are architected, how context is managed reliably, and why these systems tend to work in demonstrations but fail once real constraints are introduced. Every article is backed by a reproducible experiment, a benchmark, or a documented production failure — not opinion alone.

---

## Mission

To document engineering knowledge gained through building, measuring, and breaking production Agentic AI systems — and to explain not just what works, but why the obvious alternatives were tried first and failed.

This is an engineering handbook, not a framework tutorial. The tools referenced in the reference implementation will change. The trade-offs documented here are written to outlast them.

---

## Why This Repository Exists

Most public writing about agentic systems shows a working demo. Very little of it explains what breaks when that demo meets real-world conditions: ambiguous inputs, unreliable tools, growing context, and requirements that shift after the system is already live.

This repository exists to close that gap — one narrow, well-evidenced question at a time, rather than as a broad survey of the field. It intentionally covers two and a half themes instead of ten. What it publishes, it backs with a working implementation and a number, not just a description.

---

## Who This Repository Is For

- **Engineers** building agentic systems who want implementation detail and reproducible benchmarks, not just conceptual overviews.
- **Architects** deciding between approaches who want the trade-offs and failure modes laid out explicitly, including the ones that don't show up until production.
- **Engineering leaders** who want a fast, honest read on whether a given approach is worth the investment before their team commits to it.

Every article is written so each of these readers can stop at the depth relevant to them — see [Reading Path](#reading-path) below.

---

## Engineering Philosophy

- Explain **why** a pattern exists and **when** it breaks — not just what it is.
- Every claim is backed by an experiment, a benchmark, or a documented failure. Opinion alone does not get published.
- Depth over breadth. A small number of thoroughly tested ideas outlasts a large number of shallow ones.
- The reference implementation and the writing stay in sync — code that isn't discussed, and articles that aren't demonstrated, are both treated as unfinished.

The full set of engineering standards this repository holds itself to — including the publishing gate, the article template, and the scope boundary — is defined in [`ROADMAP.md`](./ROADMAP.md).

---

## Repository Structure

```
production-agentic-ai/

README.md
ROADMAP.md
CONTRIBUTING.md
LICENSE

01-agent-architecture/       Agent design, orchestration, and coordination patterns
02-context-and-memory/       Context budgeting, compression, and memory as context management
03-production-lessons/       Documented production failures and what they changed
04-reference-implementation/ The evolving reference project, built one module per article
05-field-notes/              Shorter, looser notes — open questions, links, early observations

diagrams/                    Mermaid source for every architecture, sequence, and state diagram
templates/                   The standard article and ADR templates
prompts/                     Reusable prompts used to produce repository content
```

---

## Reading Path

If you're new here, start in this order:

1. **This README** — for orientation.
2. **[`01-agent-architecture/`](./01-agent-architecture/)** — start with whichever pattern is closest to a decision you're currently facing.
3. **[`02-context-and-memory/`](./02-context-and-memory/)** — read this once you've settled on an agent architecture and are running into context or memory limits.
4. **[`03-production-lessons/`](./03-production-lessons/)** — read across both folders above once you want to see how these decisions held up (or didn't) once deployed.
5. **[`04-reference-implementation/`](./04-reference-implementation/)** — read alongside any article, not on its own; each module is written to accompany the article that motivated it.

If you only have a few minutes, read the **Decision Summary** at the top of any article — it's written for exactly that.

If you want to understand how this repository is run rather than what it contains, read [`ROADMAP.md`](./ROADMAP.md) instead.

---

## Reference Implementation

The repository maintains one evolving reference project rather than a collection of disconnected demos:

```
production-agent-reference
```

Built with Python, FastAPI, LangGraph, Pydantic, Redis, PostgreSQL, OpenTelemetry, Docker, and GitHub Actions. Each module demonstrates one engineering lesson from a specific article and includes a reproducible before-and-after benchmark — it is not a concept demo. See [`04-reference-implementation/`](./04-reference-implementation/) for setup instructions.

---

## Roadmap

This repository is governed by [`ROADMAP.md`](./ROADMAP.md), which defines:

- the scope boundary and what is explicitly out of scope
- the standard article template and publishing gate
- the two-week publication cadence
- the engineering workflow every topic follows, from hypothesis to publication
- how success is measured

Read it if you're deciding whether to contribute, or if you want to understand why the repository is organized the way it is.

---

## Contributing

Contributions are welcome and are held to the same publishing gate as the rest of the repository: a contribution must include a reproducible experiment, a benchmark, a documented failure, or a measurable trade-off. Opinion alone is not sufficient.

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the process, and [`ROADMAP.md`](./ROADMAP.md) for the standards a contribution is expected to meet.

---

## License

See [`LICENSE`](./LICENSE).