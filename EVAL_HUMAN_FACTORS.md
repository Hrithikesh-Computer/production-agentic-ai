# Lens 6, 7, 8: Human Factors

## Lens 6: Philosophy — score 3/5

The repo is more disciplined than many AI/engineering repos because it explicitly states the boundary between research and execution. That is a strong sign of epistemic honesty. The risk is that the broader architecture writing sometimes acts as though the product is larger than the code it actually executes.

### Evidence

- [README.md](README.md) states that the repository is intentionally not a production AI platform.
- [ROADMAP.md](ROADMAP.md) explains the distinction between research, conceptual architecture, and implementation.
- The benchmark layer in [benchmarks/README.md](benchmarks/README.md) is honest about being local and controlled rather than production telemetry.

### Top 3 value/integrity risks

1. Scope drift: the written system can be broader than the implemented slice.
2. Product-language overreach: research narratives can look like customer promises.
3. Knowledge concentration: the repository is rich with conceptual material and may rely on the reader knowing what is design vs. reality.

## Lens 7: Psychology — score 3/5

The repo is not intentionally manipulative or dark-patterny; it is simply dense. That density is the real issue. A new reader must hold a lot of information in working memory to determine what is code, what is concept, and what is future work.

### Evidence from repo structure

- [README.md](README.md), [ROADMAP.md](ROADMAP.md), and the multiple article folders all contribute to a large body of context.
- The local implementation is compact, but the surrounding documentation is rich and more extensive than the runtime.

### Top 3 human-factor risks

1. Cognitive overload: a first-time reader has to parse article, architecture, benchmark, and implementation layers.
2. Trust issue: the repo may feel more mature than it is if the reader does not track the boundary.
3. Team-level risk: a future maintainer may over-interpret conceptual architecture as an implementation plan.

## Lens 8: Neurology and Cognitive Load — score 3/5

This repo is more manageable than a typical large app because the code itself is not visually complex; the problem is the document load and the layered structure. The code is modular, but the reader's mental overhead is much higher than the code's actual size would suggest.

### Heuristic assessment

- working memory load: moderate to high
- attention load: moderate because the docs and diagrams compete with the code
- response time: not relevant to a static repo, but the code path is fast and responsive in local runs
- accessibility: no UI to test, so this is not a UI accessibility problem; the repo is not a web app
- cognitive ergonomics: the code is readable in small chunks, but the broader repo requires mental switching

### Top 3 barriers

1. Document density: many articles and diagrams create a learning curve.
2. Mixed layers: conceptual architecture sits beside code without always being labeled as such.
3. Scope ambiguity: readers do not always know when they are reading a future-state design rather than an implemented contract.

## Overall human-factors verdict

The repo is more intellectually honest than it is easy to navigate. It can be useful to the right reader, but it will feel more mature than it is unless the boundary is explained repeatedly and clearly.
