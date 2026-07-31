# Implementation plans

One plan per work package, named `YYYY-MM-DD-topic.md`. Every plan carries a YAML frontmatter
block with `status`. **This file is the index — it records what is still open.**

Plans, like everything else written in this repository, are **in English**. The conversation that
produces them is often German; the documents are not. Plans written before 2026-07-31 are still
German — they are corrected when touched, not rewritten wholesale.

A plan without `status: open` is **done and must not be executed again.** Completed plans stay in
place because they record the design decisions that later changes must not undo. They are
reference material, not a task list.

| Plan | Status | Implemented in |
|---|---|---|
| [2026-07-28-git-fanta-ui-history-graph.md](2026-07-28-git-fanta-ui-history-graph.md) | completed | `ag-tree-ui-01` → `c98b4aef` |
| [2026-07-29-history-commit-files.md](2026-07-29-history-commit-files.md) | completed | `dev` → `86b9863d` |
| [2026-07-30-rename-to-git-fanta.md](2026-07-30-rename-to-git-fanta.md) | completed | `renaming/opus5/minimax-M3` → `3083c9dd` |
| [2026-07-31-commit-file-diff-window.md](2026-07-31-commit-file-diff-window.md) | completed | `tree-ui/diff-view/minimax-M3` → `c73ec4a2` |
| [2026-07-31-history-mouse-actions.md](2026-07-31-history-mouse-actions.md) | completed | `tree-ui/mouse-actions/minimax-M3` → `e76b478a` |
| [2026-07-31-history-multi-commit-file-list.md](2026-07-31-history-multi-commit-file-list.md) | **open** | — |
| [2026-08-01-commit-description-panel.md](2026-08-01-commit-description-panel.md) | **open** | — |

## When a plan is finished

Add the frontmatter and move the row in the table above from **open** to **completed**:

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
