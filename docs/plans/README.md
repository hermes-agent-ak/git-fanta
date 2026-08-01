# Implementation plans

One plan per work package, named `YYYY-MM-DD-topic.md`. Every plan carries a YAML frontmatter
block with a `status`. **This file is the index — it says what is still open.**

A plan whose `status` is not `open` is **finished and must not be executed again.** Completed plans
stay where they are, because they record the design decisions that later changes must not undo.
They are reference material, not a task list.

| Plan | Status | Implemented in |
|---|---|---|
| [2026-07-28-git-fanta-ui-history-graph.md](2026-07-28-git-fanta-ui-history-graph.md) | completed | `ag-tree-ui-01` → `c98b4aef` |
| [2026-07-29-history-commit-files.md](2026-07-29-history-commit-files.md) | completed | `dev` → `86b9863d` |
| [2026-07-30-rename-to-git-fanta.md](2026-07-30-rename-to-git-fanta.md) | completed | `renaming/opus5/minimax-M3` → `3083c9dd` |
| [2026-07-31-commit-file-diff-window.md](2026-07-31-commit-file-diff-window.md) | completed | `tree-ui/diff-view/minimax-M3` → `c73ec4a2` |
| [2026-07-31-history-mouse-actions.md](2026-07-31-history-mouse-actions.md) | completed | `tree-ui/mouse-actions/minimax-M3` → `e76b478a` |
| [2026-08-01-commit-description-panel.md](2026-08-01-commit-description-panel.md) | completed | `tree-ui/description-panel/minimax-M3` → `16bd7e3a` |
| [2026-07-31-history-multi-commit-file-list.md](2026-07-31-history-multi-commit-file-list.md) | completed | `tree-ui/multi-select/minimax-M3` → `c8cca254` |
| [2026-07-31-history-bugfixes-1.md](2026-07-31-history-bugfixes-1.md) | completed | `tree-ui/bugfixes-1/minimax-M3` → `02958207` |
| [2026-08-01-history-merge-action.md](2026-08-01-history-merge-action.md) | completed | `tree-ui/merge-action/minimax-M3` → `95df2ee5` |
| [2026-08-01-history-ui-improvements.md](2026-08-01-history-ui-improvements.md) | completed | `tree-ui/ui-improve/minimax-M3` → `282eb7ff` |
| [2026-08-01-sorting-hot-paths.md](2026-08-01-sorting-hot-paths.md) | **open** | — |
| [2026-08-01-paint-performance-and-fanta-module.md](2026-08-01-paint-performance-and-fanta-module.md) | **open** | — |

## When a plan is finished

Add the frontmatter and move the row in the table above:

```yaml
---
status: completed
completed_at: YYYY-MM-DD
plan_commit: <short hash of the commit that added the plan>
implementation_branch: <branch>
implementation_head: <short hash of the last implementation commit>
ci_run: <URL or "not run (green locally)">
manual_verification: |
  - what was actually checked by hand
---
```

`manual_verification` lists only what was really looked at. Anything covered by tests alone does
not belong there.
