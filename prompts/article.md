# Article Prompt

Use this to draft a new article against `templates/article-template.md`. Fill in the bracketed values before use.

---

You are helping draft an engineering article for a repository focused strictly on production Agentic AI systems — specifically agent architecture and context engineering, with failure modes woven through both.

Topic: [TOPIC]
Hypothesis going in: [HYPOTHESIS]
Evidence already gathered (experiment results, benchmark numbers, production failure, or debugging story): [EVIDENCE]

Requirements:

- Follow this exact section order: Decision Summary, Problem, Motivation, Hypothesis, Background, Why the Obvious Solution Fails, Architecture, Trade-offs, Failure Modes, Reference Implementation, Experiment, Benchmark, Observations, Decision, Interview Questions, Further Reading.
- The Decision Summary is three to five sentences, written for a CTO or engineering manager who will read nothing else. State the problem, the recommendation, the business impact, and the cost of getting it wrong. No jargon, no code.
- "Why the Obvious Solution Fails" must describe approaches that seemed reasonable at the time, not strawmen invented to make the final answer look better.
- Do not publish or present this as finished unless it is grounded in the evidence provided above. Do not fabricate a benchmark number, an experiment result, or a production incident. If evidence is missing for a section, say so explicitly rather than inventing plausible-sounding detail.
- Stay strictly within scope: production Agentic AI. If the topic requires explaining a general software engineering concept (security, Kubernetes, Kafka, cloud platforms, vector databases, LLMOps, MLOps, distributed systems, general architecture), reference it only insofar as it explains an Agentic AI decision — do not let it become the subject of the article.
- Write like a senior engineer explaining a real decision to another senior engineer, not like marketing copy. No hype, no unsupported superlatives.
- Include Mermaid diagram placeholders (`[DIAGRAM: description]`) wherever a diagram belongs; do not generate ASCII art in place of a real diagram.

Draft the article now, section by section, using the Decision Summary as the last section you finalize even though it appears first.
