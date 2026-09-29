# Diagram Prompt

Use this to generate a Mermaid diagram for an article. Fill in the bracketed values before use.

---

You are creating a Mermaid diagram for a production Agentic AI engineering article. The diagram must accurately represent the system described below — do not simplify away detail that changes the reader's understanding of the trade-off being discussed.

System or flow to diagram: [DESCRIPTION]
Diagram type needed: [architecture / sequence / state / data flow]
Key components: [LIST]
Key failure point being illustrated, if any: [FAILURE POINT]

Requirements:

- Identify which components are implemented in the repository and which are conceptual or future architecture. Draw the current executable path separately from production integration when both matter; an article's architecture is not proof that the code exists.
- Output valid Mermaid syntax only, ready to paste into a `.md` file and into `diagrams/`.
- Keep it as simple as it can be while remaining accurate — this is a teaching diagram, not a complete system inventory.
- If illustrating a failure mode, mark the failure point clearly (e.g., a distinct node style, label, or annotation) rather than leaving the reader to infer where it occurs.
- Match the diagram to the specific article it belongs to — do not produce a generic, reusable version that doesn't reflect this system's actual behavior.
- Node and edge labels should use plain engineering language, not vague terms like "processing" or "magic happens here."

Generate the diagram now.
