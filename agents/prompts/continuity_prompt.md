# Continuity Ledger contract

The CLI agent MUST implement the following artifact contract in Continuity Ledger (compaction-safe) style.
Maintain a single Continuity Ledger for this workspace in [CONTINUITY.md](../artifacts/CONTINUITY.md). The ledger is the
canonical session briefing designed to survive stateful context compaction; do not rely on earlier chat text unless it’s
reflected in the ledger.

Ledger artifacts versioning storage:

- Use per-version folders: `artifacts/{iteration_id}/FACTS.diff`
- Append-only registry with small state summary per <version_id>: `artifacts/registry.json`

## How the ledger works

- At the start of every assistant turn: read CONTINUITY.md, update it to reflect the latest
  goal/constraints/decisions/state, then proceed with the work.
- Update CONTINUITY.md again whenever any of these change: goal, constraints/assumptions, key decisions, progress
  state (Done/Now/Next), or important tool outcomes.
- Keep it short and stable: facts only, no transcripts. Prefer bullets. Mark uncertainty as UNCONFIRMED (never guess).
- If you notice missing recall or a compaction/summary event: refresh/rebuild the ledger from visible context, mark
  gaps AGENTS.md ask up to 1–3 targeted questions, then continue.
- CONTINUITY.md is for long-running continuity across compaction (the “what/why/current state”), not a step-by-step task
  list.
- Keep them consistent: when the plan or state changes, update the ledger at the intent/progress level (not every
  micro-step).

## How versioning works

Use a separate “ledger versioning” mechanism when you need to change established facts/decisions in a way that should be
auditable over time (as opposed to routine progress updates). If some part of `CONTINUITY.md` needs changes in a
versioning context, record the change as a facts diff artifact:

1. Create a new per-version folder: `artifacts/{iteration_id}/`
2. Write a single file: `artifacts/{iteration_id}/PARTS.diff` where `PARTS.diff` is Git diff format file to show
   difference between new and old version of changed CONTINUITY.md parts.
3. Maintain an append-only registry entry per `{iteration_id}` in `artifacts/{iteration_id}/parts.json`. Each array
   entry should include JSON object with:
    - `part_name` "Goal", "Constraints/Assumptions", "Facts", "Key decisions", "Open questions", "Working set" with key
      decision about change.
    - `summary` (1–3 lines) is a short, human-readable summary of what changed in the ledger and why. Use bullet points.
      Reference the affected ledger section(s) (e.g., “Key decisions”, “Constraints/Assumptions”).
      Include the reason and any supporting evidence pointers (file paths, artifact paths, run ids).

## In replies

- Begin with a brief “Ledger Snapshot” (Goal + Now/Next + Open Questions). Print the full ledger only when it materially
  changes or when the user asks.

## CONTINUITY.md format (keep headings)

- Goal (including success criteria):
- Constraints/Assumptions:
- Facts:
- Key decisions:
- Open questions (UNCONFIRMED if needed):
- Working set (relative file paths / ids / commands):

## parts.json (JSON format)

```json
[
  {
    "part_name": "Goal to session state is added",
    "summary": "Changed to stateless session state."
  },
  {
    "part_name": "Assumption to use tool skill is added",
    "summary": "Changed to Use tool skills for `curl.exe` and `psql.exe`"
  }
]
```

## PARTS.diff (Git diff format)

```diff
diff --git a/CONTINUITY.md b/CONTINUITY.md
--- a/CONTINUITY.md
+++ b/CONTINUITY.md
@@
 - Goal (including success criteria):
-
+- Establish session state and await user task for Evolver repo while following AGENTS constraints.
+  - Constraints/Assumptions:
+    - Use tool skills for `curl.exe` and `psql.exe` when needed (per AGENTS).
+    - Network allowed only to localhost as specified by OpenEvolve prompt.