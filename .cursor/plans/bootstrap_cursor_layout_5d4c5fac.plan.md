---
name: Bootstrap cursor layout
overview: "Add a repo-root Cursor bootstrap: the official `.cursor` folders, a short root `AGENTS.md`, and one always-on rule that treats the sample app as reference only."
todos:
  - id: dirs
    content: Create .cursor/rules, skills, agents, and hooks with .gitkeep in the empty folders
    status: completed
  - id: rule
    content: Add always-on .cursor/rules/project.mdc (sample is reference only)
    status: completed
  - id: agents-md
    content: Add a short root AGENTS.md with the same boundary
    status: completed
isProject: false
---

# Bootstrap Cursor layout

The repo root currently has only [`sample-old-version-delete-when-finished-using/`](sample-old-version-delete-when-finished-using). Add the Cursor project layout beside it. No application code, no edits inside the sample.

## Layout

```text
AGENTS.md
.cursor/
  rules/project.mdc
  skills/.gitkeep
  agents/.gitkeep
  hooks/.gitkeep
```

Empty `skills/`, `agents/`, and `hooks/` get a `.gitkeep` so Git keeps the folders. No `hooks.json`, placeholder skills, or extra rules.

## Always-on rule

[` .cursor/rules/project.mdc`](.cursor/rules/project.mdc) uses `alwaysApply: true` and no globs. Keep it under 50 lines. It will say:

- This repo is a new Voice Diary implementation.
- [`sample-old-version-delete-when-finished-using/`](sample-old-version-delete-when-finished-using) is a read-only reference for behavior and constraints.
- New code goes at the repo root, outside that folder.
- Do not copy the sample layout or files in as the implementation.
- Do not edit the sample unless asked.
- Do not commit secrets; sample env and credential files stay reference-only.

## AGENTS.md

[`AGENTS.md`](AGENTS.md) at the repo root repeats that same boundary in a few lines, so tools that read `AGENTS.md` get the same instruction as the Cursor rule. No second source of longer project conventions.
