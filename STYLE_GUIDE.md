# Style Guide

This document defines writing and formatting conventions. It governs *how* things are written; `ROADMAP.md` governs *what* gets written and why. If the two ever appear to conflict, `ROADMAP.md` wins on scope and standards, and this document wins on formatting and phrasing.

This is the last foundational document this repository needs. Once it's in place, the priority is publishing the first article — not adding further process documents.

---

## Writing Principles

- **State the conclusion before the reasoning.** The Decision Summary exists so a reader never has to hunt for the point. Don't bury it in the Architecture or Trade-offs section instead.
- **Write toward a specific decision, not a survey of a category.** An article compares alternatives in order to argue for one of them, not to list them neutrally. If a piece doesn't reach a Decision, it isn't finished.
- **Prefer the concrete over the general.** "Latency increased from 340ms to 1.2s under 50 concurrent requests" is a sentence this repository wants. "Performance degrades under load" is not — it's true of everything and teaches nothing.
- **Name the trade-off, don't hide it.** Every architecture in this repository costs something. If an article can't state what its recommended approach gives up, it hasn't been thought through fully enough to publish.
- **Write like you're explaining a real decision to a peer, not producing marketing copy.** No unsupported superlatives ("revolutionary," "game-changing," "seamless"). No rhetorical questions used as section openers. No hype about a tool or framework — evaluate it the same way you'd evaluate any other engineering choice.
- **Show the failure, don't just gesture at it.** "This can fail in production" is not a Failure Modes section. What failed, under what condition, how it was detected, and what changed as a result — is.
- **Say "I don't know" or "this wasn't tested" explicitly** rather than implying certainty the evidence doesn't support. A gap that's named is more credible than a gap that's papered over.

---

## Markdown Conventions

- One `#` (H1) per file, used only for the title.
- Section headings use `##` (H2); do not skip heading levels (no `##` followed directly by `####`).
- Use `-` for unordered lists, not `*` or `+`, for consistency across files.
- Use numbered lists only when order or sequence genuinely matters (a procedure, a ranked comparison) — not for lists that are actually unordered.
- Bold is reserved for a single key term or phrase per paragraph, not entire sentences.
- Italics are used for asides, template guidance text (as in `templates/article-template.md`), and the first use of a term being defined — not for general emphasis.
- Avoid nested blockquotes. A single `>` is used only for direct quotation of an external source or a genuinely load-bearing one-line principle (as used sparingly in `ROADMAP.md`).
- No emojis, anywhere, in any file in this repository.
- Horizontal rules (`---`) separate major sections in long documents (as in this file and `ROADMAP.md`), not every paragraph.

---

## Heading Hierarchy

Every article uses the exact heading set and order defined in `templates/article-template.md`, with no additions, removals, or renamed sections. Subheadings within a section are permitted (`###`) when a section genuinely has internally distinct parts — for example, splitting Architecture into a description of the current design and a description of an alternative considered — but should be used sparingly. An article with more than two or three `###` subheadings inside a single section is usually a sign the section is trying to cover more than one idea and should be reconsidered.

---

## Diagram Conventions

- All diagrams use Mermaid, checked into `diagrams/` as `.mmd` or embedded directly in the article's Markdown — never a static image (`.png`, `.jpg`) of a diagram that could instead be version-controlled as text.
- Diagram file names match the article they belong to: an article at `01-agent-architecture/router-pattern.md` has a corresponding diagram at `diagrams/router-pattern.mmd` (or `router-pattern-sequence.mmd`, `router-pattern-state.mmd` if more than one diagram type is needed).
- Every diagram is referenced from the article body at the point it's relevant, not collected in a single "diagrams" section at the end.
- Failure points illustrated in a diagram are marked distinctly (a different node style or explicit label) rather than left for the reader to infer.
- Diagrams are updated in the same pull request as any implementation change that would make them inaccurate. A diagram that no longer matches the code is a defect, not a formatting issue — see `ROADMAP.md`.

---

## Code Block Conventions

- Every code block is tagged with its language for syntax highlighting (` ```python `, ` ```bash `, ` ```mermaid `) — never a bare ` ``` `.
- Code shown inline in an article is a minimal, working excerpt that illustrates the specific point being made — not the full contents of a file. The full implementation lives in `production-agent-reference` and is linked to, not pasted in full.
- Every non-trivial code excerpt has a one-line comment or preceding sentence explaining what it demonstrates, not just what it does.
- Shell commands intended to be run are shown as complete, copyable sequences (as in the setup commands in this repository), not fragments requiring the reader to infer missing steps.
- Placeholder values in code or commands use brackets (`[VALUE]`) consistently, matching the convention already used in `prompts/`.

---

## Citation Style

- External claims (a paper's finding, a framework's documented behavior, a public benchmark) are cited inline with a Markdown link on first mention: `as shown in [the original paper](URL)`, not a bare URL or a numbered footnote system.
- The Further Reading section at the end of each article collects every source cited in the body, plus any additional background reading, as a flat list of Markdown links with a short description of what each source adds.
- Claims about this repository's own experiments or benchmarks are never "cited" — they're stated directly and linked to the relevant Experiment or Benchmark section, since the repository is the primary source.
- Do not cite a source for a claim you have not actually verified against that source. If a claim is common knowledge in the field and doesn't trace to a specific source, state it without a citation rather than attaching one that doesn't really support it.

---

## File Naming

- All files and folders use lowercase, hyphen-separated names: `router-pattern.md`, not `RouterPattern.md` or `router_pattern.md`.
- Article filenames describe the topic, not the theme it belongs to (the folder already provides that context): `02-context-and-memory/context-budgeting.md`, not `02-context-and-memory/context-engineering-context-budgeting.md`.
- ADRs are numbered sequentially with a zero-padded three-digit prefix and a short slug: `adr-001-structured-contracts.md`. Numbers are never reused, even if an ADR is later superseded — a superseded ADR stays in place and links to the one that replaced it.
- Reference implementation modules mirror the slug of the article that motivates them where practical, so the connection between article and code is discoverable without a lookup table.
- Diagram files follow the convention described above under Diagram Conventions.
- Top-level governance files (`README.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `STYLE_GUIDE.md`, `LICENSE`) are the only files in the repository written in uppercase, matching common open-source convention.

---

## Terminology

Consistency here is what keeps the repository reading as one coherent body of work rather than a collection of individually written posts.

| Use | Instead of |
|---|---|
| Agentic AI | AI agents, autonomous agents, agentic systems *(unless specifically distinguishing agentic AI from a narrower or different concept in context)* |
| production system | real-world system, live system |
| context window | prompt window, token window |
| context budgeting | token budgeting *(unless the article is specifically discussing token-level accounting as distinct from broader context management)* |
| failure mode | edge case *(a failure mode is a way a system breaks; an edge case is an input — don't use them interchangeably)* |
| trade-off | downside, limitation *(trade-off implies something was gained in exchange; use it when that's actually true, not as a euphemism for a pure weakness)* |
| reference implementation | demo, sample code, proof of concept |
| benchmark | test *(a benchmark is a measured comparison against a defined workload; a test just confirms behavior — don't conflate them)* |

When introducing a term not covered here for the first time in a given article, define it briefly on first use and then use that same term consistently for the remainder of the piece — don't alternate between synonyms for variety. Variety in word choice is a fiction-writing value, not an engineering-writing one; the goal here is that the same concept always has the same name.

---

## When This Document and an Article Disagree

If a published article predates a change to this style guide, it is brought into alignment during its next scheduled maintenance pass (see `ROADMAP.md`), not immediately rewritten on its own. This guide is applied going forward and applied retroactively only as part of already-planned maintenance — not as a reason to interrupt the publication cadence to fix formatting in old work.