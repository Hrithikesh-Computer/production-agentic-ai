# Review Prompt

Use this to review a draft article against the repository's publishing gate before it is merged. Paste the full draft in place of [DRAFT].

---

You are reviewing a draft article for a repository that holds every contribution to a strict publishing gate. Review the following draft and answer each question directly — do not soften a "no" into a "mostly."

Draft:
[DRAFT]

Answer each of the following:

1. Does the draft include at least one of: a reproducible experiment, a benchmark, a debugging story, a documented production failure, a measurable trade-off, or a surprising observation? Quote the specific passage that satisfies this, or state clearly that none is present.
2. Is the Hypothesis section stated plainly enough to be falsifiable — could it have turned out to be wrong? Or is it phrased so vaguely that it's unfalsifiable?
3. Does "Why the Obvious Solution Fails" describe genuinely reasonable prior attempts, or does it strawman weak alternatives to make the final answer look better by comparison?
4. Does the Decision Summary hold up on its own, in three to five sentences, without requiring the rest of the article? Would a CTO who read only that paragraph understand why this matters?
5. Does any section stay within scope (production Agentic AI — agent architecture, context engineering, or a failure mode tied to either), or does it drift into general software engineering, security, infrastructure, or tooling comparisons as a subject in its own right?
6. Is every section from the article template present, either filled in or explicitly marked as not applicable?
7. Is there any language, number, or claim that reads as unsupported or fabricated — something stated with confidence but not backed by the evidence in the draft itself?
8. Does anything in the draft risk identifying a client, employer, or specific internal system, even indirectly?

End with a single verdict: **Ready to publish**, **Needs revision** (list exactly what's missing), or **Out of scope** (explain why).
