# Production Agentic AI — Engineering Roadmap

**Subtitle:** Building Reliable Agentic AI Systems

This document defines the scope, standards, and operating discipline for the `production-agentic-ai` repository. It exists to protect the repository from two failure modes that are common in engineering-focused public work: scope that grows faster than the work itself, and publication that stalls indefinitely in the name of getting things right. Everything below is written to prevent both.

---

## The One Rule

> **Depth compounds. Scope dilutes.**

A small body of work built on reproducible experiments, reference implementations, and clear engineering reasoning creates more long-term value than a large collection of shallow content.

Whenever this roadmap starts expanding in themes, folders, or deliverables, remove something before adding anything. The goal is not to build the largest repository on Agentic AI. The goal is to build the repository engineers bookmark when they need to understand why production Agentic AI systems fail and how to make them reliable.

---

## The North Star

Become recognized as an engineer who explains, measures, and improves the reliability of production Agentic AI systems.

Every article should answer one engineering question. Every implementation should demonstrate one architectural principle. Every benchmark should validate or challenge one engineering assumption.

Everything published should strengthen one reputation:

> This engineer understands why LLM systems work in demonstrations but fail in production.

Everything ultimately traces back to one question:

> Why do production Agentic AI systems fail, and how can they be made reliable?

---

## Mission

This repository is an engineering handbook. It is not a framework tutorial, and it is not a general collection of AI notes.

Its purpose is to document engineering knowledge gained through:

- studying production architectures
- building reference implementations
- running experiments
- measuring trade-offs
- documenting failures
- refining engineering decisions over time

The objective is to understand why systems behave the way they do, not merely how to operate a particular framework. Frameworks change. The underlying engineering reasoning does not.

This distinction matters more than it first appears. Most public content about agentic systems documents how to use a specific tool at a specific version — a router built with a particular orchestration library, a memory pattern built on a particular vector store. That content has a short shelf life, because the tool underneath it changes faster than the writing does. This repository takes the opposite approach: the tools used in the reference implementation are a means of testing an idea, not the idea itself. An article on context budgeting should remain useful to a reader even after the specific library referenced in its code has been replaced by something else, because the underlying trade-off it documents — how much context a system can afford to carry, and what it costs to carry too much or too little — does not go away with a new release.

---

## Scope Guard

This repository intentionally focuses on the engineering of production Agentic AI systems.

General software engineering topics are discussed only when they directly explain an architectural decision, production failure, or engineering trade-off within an Agentic AI system. They are never discussed as standalone subjects.

The test for any new topic, article, folder, or theme:

> If a topic can stand alone without mentioning production Agentic AI, it belongs in another repository.

Apply this test before adding:

- folders
- themes
- articles
- experiments
- implementations

Protecting scope is more important than expanding coverage. When in doubt, the correct action is to leave a topic out and revisit it later, not to include it provisionally.

---

## Repository Scope

This repository focuses on two and a half themes. Nothing else is added as a standalone category during this iteration of the repository.

The half-theme is deliberate rather than an oversight. Failure modes are treated as a lens applied to the other two themes rather than a third full category, because failure modes documented in isolation — a list of ways agents can go wrong, detached from the architecture that produced them — are far less useful to a reader than the same failures documented as part of the specific design decision that caused them. A reader trying to decide between two routing strategies is better served by seeing the failure inside the router article than by cross-referencing a separate failure catalog.

### 1. Agent Architecture

Understanding how autonomous agents are designed, coordinated, and orchestrated in production systems.

Representative topics include:

- Single-agent systems
- Multi-agent systems
- Router pattern
- Planner pattern
- Supervisor pattern
- Reflection and self-correction
- Critic pattern
- Tool selection
- Human-in-the-loop design
- State machines for agent control flow
- Agent-to-agent communication

### 2. Context Engineering

Understanding how reliable context is created, budgeted, compressed, and maintained across an agent's operation.

Memory is treated as a specialized form of context management, not as an independent theme. A memory system is, functionally, a context retrieval and injection problem, and is documented as such.

Representative topics include:

- Context budgeting
- Context compression
- Prompt assembly
- Context routing
- Working memory
- Long-term memory
- Memory compression
- Context refresh strategies
- Instruction hierarchy
- Prompt versioning

### 3. Failure Modes (Half Theme)

Failure modes are not a standalone category with its own separate articles. Instead, every article in the two themes above is required to address, as part of its own narrative:

- what failed
- why it failed
- how the failure was detected
- how it was addressed
- what trade-offs were introduced by the fix

Reliability is woven through every topic rather than isolated into its own section. This is deliberate: failure modes divorced from the architecture that produced them are far less useful than failure modes documented in context.

---

## Out of Scope

The following topics are intentionally not standalone themes during this iteration of the repository:

- Security
- Kubernetes
- Kafka
- Cloud Platforms
- Vector Databases
- LLMOps
- MLOps
- AI Framework Comparisons
- General Distributed Systems
- General Software Architecture

These topics may appear inside an article only when necessary to explain a specific engineering decision within an Agentic AI system — for example, referencing a specific vector database's latency characteristics when explaining a retrieval failure. They do not receive their own folders, their own articles, or their own themes. If a draft's primary subject is one of these topics rather than Agentic AI, it does not belong in this repository.

---

## Repository Structure

```
production-agentic-ai/

README.md
ROADMAP.md
CONTRIBUTING.md
LICENSE

01-agent-architecture/
02-context-and-memory/
03-production-lessons/
04-reference-implementation/
05-field-notes/
archive/

diagrams/
templates/
prompts/
```

Active content stays deliberately small. Historical design sketches, evaluations, and dated review artifacts belong under `archive/`, not in the active article tree.

---

## Evidence Layer and Benchmark Discipline

This repository is intentionally building toward a stronger evidence posture. The benchmark layer is not a sign that the repository is becoming a product or a framework; it is the mechanism that turns the strongest architecture and reliability claims into reproducible local evidence.

Every major claim should eventually map to:

1. article / design rationale
2. implementation or local protocol slice
3. tests and/or benchmark execution
4. explicit limits and missing evidence

The benchmark layer exists to prevent the repository from confusing conceptual reasoning with measured results. Benchmark outputs are treated as local, controlled evidence, not as production deployment metrics.

## Current Implemented Surface vs Future Research Context

The repository contains two different kinds of material, and readers should not blur them together.

Read its maturity in four layers:

1. **Current:** research articles, prompts, templates, and conceptual Mermaid diagrams.
2. **Implemented reference slice:** local Python policy, UTF-8-safe chunking, authenticated envelopes (CRC32 plus HMAC-SHA256), bounded reassembly, message-scoped session retry/fallback, tests, CI, static checks, and demo.
3. **Future reference extensions:** optional experiments or adapters, added only when a specific article and reproducible test justify them.
4. **Potential production architecture:** servers, models, databases, queues, clients, telemetry backends, and deployment systems discussed as context only until code, dependencies, tests, and CI implement them.

### Current implemented surface

The code that is actively present and testable in the repo today is intentionally small and local. It consists primarily of the Python package under `04-reference-implementation/adaptive-response-filter/` and the tests for that package. This is the only place where the repository currently implements a concrete wire-contract, chunking policy, checksum validation, and reassembly logic.

At the moment, the local implementation includes:

- a validated `WireEnvelope` contract with CRC32 checksums and HMAC-SHA256 authentication
- a `DeliveryPolicy` that decides whether to chunk
- a `semantic_split()`/`_fixed_size_split()` chunking path
- a bounded single-message `Reassembler`, plus `ReassemblySession` timeout/retry/fallback behavior and a manager for interleaved message IDs
- a small demo script and pytest suite

This local implementation is deliberately not a full runtime stack. It does not require FastAPI, Pydantic, Redis, Postgres, a browser client, or a TypeScript service to run the tests and demo in this repository. The checked-in pytest suite and demo run against the local Python implementation only; no database, queue, HTTP service, or external transport layer is required for the current execution boundary.

### Broader ecosystem ideas and future research context

The following technologies and architectures may appear in article writing or future research because they shape agentic production systems, but they are not active requirements of the current repository implementation:

- FastAPI or other web service runtimes
- Pydantic models and request validation layers
- Redis or other external state stores
- Postgres or other durable persistence layers
- message queues, brokers, or stream infrastructure
- TypeScript client SDKs or browser transport code
- progressive UI rendering and transport adapters
- authenticated transport security or end-to-end encryption

These ideas belong in the conceptual or future-facing portion of the project, not in the current local execution contract. They are research context, design vocabulary, or future integration directions. They should be treated as optional ecosystem patterns, not as repository dependencies required to run the reference slice.

### Systemic Context vs. Active Dependencies

This repository should be read as a documentation-led engineering knowledge base with a narrow local implementation slice, not as a monorepo for a live service stack.

The active local dependencies are intentionally minimal:

- Python standard library for the protocol logic
- pytest for the executable tests
- ruff and mypy for linting and static checks
- the checked-in source modules under `04-reference-implementation/adaptive-response-filter/`

The following are systemic context or future research directions rather than active runtime requirements for the current repo:

- FastAPI, Starlette, or other HTTP servers
- Pydantic, dataclasses-driven API models, or browser-side schema validation
- Redis, Postgres, Kafka, or queue-backed persistence
- TypeScript client code such as `client_reassembler.ts`
- browser rendering, progressive UI state machines, or transport-connected retry callbacks
- LLM provider SDKs and telemetry toolchains that belong in a larger deployed system

This distinction matters because the repository's executable boundary is intentionally small: readers are meant to inspect the wire contract, chunk semantics, checksum validation, and bounded reassembly in local Python code without needing a database, queue, or external service runtime.

### Systemic Dependencies & Future Research Context

This repository does not currently contain a deployment-ready agent service. It is not a monorepo for a production platform. The article set may discuss systems that depend on external services, but those services are not part of the local execution environment necessary to run the repository's tests.

When a diagram, article, or architectural discussion references a network boundary, queue, browser, store, or backend dependency, that reference should be read as:

- conceptual architecture or production system context, or
- a proposed extension beyond the current repository implementation, not
- a currently required runtime dependency for this local codebase.

A rule for future work:

> If a dependency is required to make the local tests or demo run, it belongs in the current implementation boundary. If it is only required in a production deployment or a future research prototype, it belongs in the future context section.

This keeps the repository honest: the local Python implementation verifies a narrow and useful protocol idea, while the broader ecosystem remains a larger engineering field to investigate later.

---

## Writing Philosophy

Articles do not explain what a pattern is. They explain:

- why it exists
- which problem it solves
- why the obvious alternatives were tried first and failed
- what trade-offs were accepted by the approach that won
- where the approach breaks
- when it should not be used

The objective of every piece of writing in this repository is engineering understanding, not documentation completeness. A shorter article that explains a genuine trade-off is more valuable than a longer article that lists options without judgment.

As a concrete example: an article on the router pattern does not open by defining what a router is. It opens with the question a system actually has to answer — how should this piece of work be sent to the component best equipped to handle it — and then walks through why a fixed rule set was tried first, why it broke down as the number of cases grew, why a learned or model-based router was introduced next, and what new failure modes that introduced in exchange. The reader finishes the article understanding a decision, not memorizing a definition. This same discipline applies whether the topic is a well-known pattern or something specific to this repository's own experiments — the writing always argues toward a conclusion rather than surveying a category.

---

## Writing for Multiple Audiences

Every article is written once, but structured so that different readers can stop at the depth relevant to them. The scope of the content does not change across audiences — only the depth at which a given reader engages with it.

### Decision Summary

**Audience:** CTOs, engineering managers, staff engineers.

**Length:** Three to five concise sentences.

**Contents:** the problem, the recommendation, the business impact, and the cost of getting it wrong.

A reader at this level should understand why the topic matters without reading any further.

### Engineering Analysis

**Audience:** Architects, senior engineers.

**Contents:** architecture, trade-offs, alternatives considered, failure modes, and the engineering reasoning behind the decision.

This is the core of every article and typically its longest section. A reader at this level is deciding which approach fits their own constraints.

### Implementation

**Audience:** Engineers building the system.

**Contents:** reference implementation, benchmarks, experiments, configuration details, and diagrams.

Implementation validates the engineering discussion. It does not replace it — code without the reasoning that produced it is not useful to this repository's readers.

---

## Article Template

Every article in this repository follows the same structure without exception:

```
Decision Summary
Problem
Motivation
Hypothesis
Background
Why the Obvious Solution Fails
Architecture
Trade-offs
Failure Modes
Reference Implementation
Experiment
Benchmark
Observations
Decision
Interview Questions
Further Reading
```

Consistency across articles improves readability for repeat readers and enforces disciplined thinking during writing. If a section genuinely does not apply to a given topic, it is stated explicitly ("no meaningful trade-off was found") rather than silently omitted.

---

## Publishing Gate

Documentation is published only when it contributes new engineering knowledge.

Every article must include at least one of the following:

- a reproducible experiment
- a benchmark
- a debugging story
- a documented production failure
- a measurable trade-off
- a surprising observation

Opinion alone is not sufficient.

Every article begins with a hypothesis, stated plainly enough to be wrong. Every conclusion is supported by evidence gathered during the article's own research and implementation cycle, not by citation of external claims alone.

---

## Engineering Workflow

Every topic in this repository follows the same lifecycle, without exception:

```
Question
   ↓
Research
   ↓
Hypothesis
   ↓
Experiment
   ↓
Implementation
   ↓
Benchmark
   ↓
Analysis
   ↓
Documentation
   ↓
Review
   ↓
Repository Update
```

This workflow does not change based on topic, urgency, or how confident the author already feels about the answer. Confidence going in is exactly what the hypothesis step is meant to test, not skip.

The workflow is deliberately linear rather than iterative within a single cycle. It is tempting, when a first experiment produces an inconclusive result, to immediately redesign the experiment and try again within the same two-week window. In practice this is where cycles quietly expand past their intended length. If an experiment produces an inconclusive or negative result, that outcome is documented as the article's finding for the cycle, and a redesigned experiment becomes the hypothesis for the next cycle. A negative result, clearly documented, is more valuable to a reader than a positive result reached by quietly discarding the first attempt.

---

## Publication Cadence

The repository operates on a two-week publication cycle.

### Week One

- Read relevant papers and engineering blogs
- Formulate the hypothesis for the cycle
- Design the experiment that will test it
- Create supporting diagrams
- Draft the article

### Week Two

- Build or extend the reference implementation
- Run the experiment
- Record benchmark results
- Finish writing the article
- Publish
- Share an engineering summary
- Gather feedback for the next cycle

The cadence exists to prevent endless planning. A two-week cycle is short enough that no single article can expand into an open-ended research project, and long enough to include a genuine experiment rather than a surface-level opinion.

---

## Architecture Decision Records

Every significant engineering decision made in the course of building the reference implementation receives an Architecture Decision Record.

Template:

```
Context
Problem
Options Considered
Decision
Trade-offs
Consequences
```

Representative examples:

- Structured contracts versus free-text agent communication
- Context budgeting strategy
- Planner strategy selection
- Memory architecture
- Tool selection policy

Architecture Decision Records live alongside the article that produced them rather than in a separate top-level folder. Their purpose is to explain why a decision was made, in a form that remains useful even after the decision itself is revisited.

---

## Reference Implementation

The repository maintains a small, checked-in reference implementation rather than a collection of unrelated demos.

```
04-reference-implementation/
└── adaptive-response-filter/
```

**Intended ecosystem for future reference modules (not the current installed stack):**

- Python
- FastAPI
- LangGraph
- Pydantic
- Redis
- PostgreSQL
- OpenTelemetry
- Docker
- GitHub Actions

These are technologies that future modules may evaluate where an article needs them. Their appearance here does not mean that current tests require the services or packages. The current implementation inventory and runtime prerequisites are maintained in the following section.

Each module in the reference implementation demonstrates one engineering lesson and is added in the same publication cycle as the article that motivates it — the implementation is never a separate, multi-month build phase disconnected from the writing.

Every module must solve one documented production problem drawn from the article it accompanies. A concept demonstration that cannot be measured against a before-and-after benchmark is not sufficient for inclusion.

## Systemic Dependencies & Future Research Context

This repository contains engineering articles and a small executable reference slice; it is not currently a production service or a deployed runtime. Use the checked-in package configuration and CI workflow as the source of truth for what can be run today.

### Implemented locally

- The checked-in runtime code is the standard-library Python module under `04-reference-implementation/adaptive-response-filter/`. `pyproject.toml` declares Python `>=3.10` and no runtime package dependencies.
- The optional `dev` extra supplies pytest, Ruff, and mypy. Setuptools builds the project metadata; it does not turn the flat reference files into a production service package.
- GitHub Actions runs on Ubuntu with Python 3.10, installs the development extra, then runs Ruff, mypy, pytest, and the standalone demo.
- Articles and diagrams are Markdown and Mermaid source. They do not require local database, model-serving, or transport services.

### Not active local dependencies

FastAPI, LangGraph, Pydantic, Redis, PostgreSQL, OpenTelemetry, Docker, and an LLM provider are ecosystem options and future research context in this roadmap and in authoring prompts. They are not imported or started by the current reference implementation, and no Redis/PostgreSQL containers or credentials are needed to run the current tests.

The response-delivery article discusses a broader browser and HTTP production system, but those integrations are not checked in. The local reference contract validates CRC32 and HMAC-SHA256, and `ReassemblySession` models timeout, retry, and full-buffer fallback through caller-provided callbacks. It does not connect those callbacks to a real transport, manage production keys, or implement client rendering. The implementation boundary is documented in `04-reference-implementation/README.md` and the response-delivery article.

When adding a future dependency, service, or client, update this inventory in the same change as its package configuration, local setup, CI, and article boundary. Mentioning a technology as a trade-off or research subject is not a declaration that it is a required dependency.

---

## Diagram Standards

Every article that describes a system includes visual documentation. Preferred diagram types:

- Architecture diagram
- Sequence diagram
- State diagram
- Data flow diagram

Mermaid is the default format, since it renders natively in GitHub Markdown and keeps diagrams version-controlled alongside the text that describes them.

Diagrams are updated whenever the reference implementation they describe changes. A diagram that no longer matches the code it documents is treated as a defect, not a cosmetic issue.

---

## Prompt Library

Reusable prompts used to produce repository content are maintained once and improved continuously, rather than rewritten for each article.

```
prompts/

article.md
diagram.md
review.md
benchmark.md
implementation.md
critique.md
linkedin.md
```

Prompts are shared infrastructure. They are not article content and are not published as standalone repository entries.

---

## Quarterly Roadmap

### Quarter 1 — Foundation

- Establish repository standards and templates
- Build the initial reference implementation
- Publish foundational articles on agent architecture
- Define documentation quality bar
- Begin sharing work publicly from the first cycle onward

### Quarter 2 — Context Engineering

- Explore context management strategies in depth
- Study memory architectures as a context management problem
- Improve context reliability in the reference implementation
- Expand implementation modules to match published articles

### Quarter 3 — Reliability

- Document production failures observed across both themes
- Improve and re-run earlier benchmarks with more rigor
- Expand experiments based on reader feedback from Q1 and Q2
- Refine earlier architectural decisions where evidence has changed

### Quarter 4 — Consolidation

- Revisit and improve earlier articles
- Refresh benchmarks against current tooling
- Update diagrams to match the current state of the implementation
- Refine engineering opinions where the evidence has shifted
- Strengthen consistency between documentation and implementation

Visibility efforts — sharing work, engaging in discussion, gathering feedback — continue throughout all four quarters rather than being delayed until the end of the year.

---

## Maintenance

Once every quarter, independent of the quarterly focus above:

- Update older articles where the underlying tooling has changed
- Refresh framework and library references
- Improve diagrams that have drifted from the implementation
- Re-run benchmarks where results may no longer hold
- Revise engineering opinions as new evidence becomes available
- Confirm documentation and implementation remain synchronized

Engineering knowledge is expected to evolve. An article that is never revisited after publication is treated as a maintenance gap, not a finished asset.

---

## Anonymization Policy

The following are never published, under any circumstances:

- Client code
- Client architecture
- Internal prompts
- Internal metrics
- Screenshots of internal systems
- Proprietary workflows

Instead, the repository publishes:

- Generalized patterns
- Simplified architectures
- Synthetic examples
- Educational implementations
- Engineering reasoning that stands on its own without identifying its source

Any case study drawn from real production experience is rewritten with different numbers, a generalized architecture, and no identifying detail, before it is drafted — not adjusted afterward. This decision is made at the start of writing, not during a later editing pass.

---

## Success Metrics

Vanity metrics are not tracked as indicators of progress. The following are tracked instead:

- Articles published on the two-week schedule
- Articles that pass the publishing gate without exception
- Reproducible experiments completed
- Benchmarks completed and, where relevant, re-validated
- Improvements made to the reference implementation
- Repeat readers returning to new content
- Substantive engineering discussion generated by published work
- Overall repository quality as judged by internal review against these standards

Recruiter outreach and interview invitations are tracked as well, but are treated explicitly as lagging indicators. They are evidence that the underlying discipline has been sustained for long enough to be noticed externally — they are not expected to move in response to any single article, and their absence in early cycles is not a signal that the work is off track. GitHub stars are welcome when they occur but are not an objective of the work.

## Architecture & Presales Evaluation

All architecture reviews and customer-facing technical evaluations of this repository (or systems derived from it) must follow the evidence-first methodology defined in:

- [`prompts/architecture-presales-evaluation.md`](./prompts/architecture-presales-evaluation.md)

Key mandatory rules:

- Distinguish **what exists in the repository** from **what is only documented, intended, or hypothesized**.
- Never treat **NOT IN REPOSITORY** as **PROVEN ABSENT**.
- Never convert design intent, research articles, conceptual architectures, or illustrative benchmarks into production claims.
- Performance, security, reliability, and AI-quality claims require explicit evidence classification before they may be presented to a customer.

This methodology protects both engineering honesty and customer-facing safety. It does not change the scope or content of research articles.

---

## Deferred Until Later

The following ideas are intentionally postponed until the repository has matured through a full year of the cadence above:

- A standalone personal website
- Conference talks
- A newsletter
- Additional engineering themes beyond the two and a half defined above
- Book-length reading lists
- Broader AI engineering topics outside production Agentic AI

These are not rejected ideas. They are good ideas introduced too early, which is a distinct failure mode from a bad idea. Each one is reconsidered only once the repository already contains a substantial, consistent body of work that would make it worth building on.

---

## Guiding Principle

The publication cadence is a commitment, not a suggestion.

Every two-week cycle should produce one completed piece of work, even if the outcome is that the original hypothesis was wrong. If a cycle ends without something worth publishing, treat it as feedback on the scope of the experiment — not as permission to delay publication.

Narrow the next experiment.

Reduce the scope.

Ship the evidence you gathered.

Document what surprised you.

Then continue.

Consistency builds engineering credibility. Evidence builds engineering reputation. Both matter.