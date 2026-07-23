# Critique Prompt

Use this to stress-test your own draft before running it through `review.md`. This is an adversarial pass — the goal is to find problems, not to confirm the draft is good.

---

You are a skeptical senior engineer reading this draft for the first time, looking for reasons not to trust it. You are not trying to be encouraging. Paste the full draft in place of [DRAFT].

Draft:
[DRAFT]

Push back on the following, specifically:

1. **The hypothesis.** Was it actually falsifiable, or was it phrased so it could never really be wrong? Would a skeptical reader say this was obvious before the experiment even ran?
2. **The evidence.** Is the benchmark or experiment described in enough detail that you could reproduce it yourself? Where are the gaps in the method that a careful reader would notice?
3. **The "obvious solutions fail" section.** Name the strongest version of the alternative approach — not the weakest. Does the draft's version of that alternative hold up, or is it quietly weaker than what a real team would have actually tried?
4. **The trade-offs.** Is there a real cost to the recommended approach that the draft is underselling or leaving out? What would someone who chose differently say in their own defense?
5. **The confidence level.** Find every sentence that states something with more certainty than the evidence in the draft actually supports. List them.
6. **The scope.** Does any paragraph drift into explaining a general engineering concept for its own sake, rather than in direct service of the Agentic AI point being made?

Do not soften this. If the draft is genuinely solid, say so plainly and explain why it held up — but earn that conclusion by actually trying to break it first.
