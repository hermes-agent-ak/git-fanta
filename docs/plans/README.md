# Implementierungspläne

Ein Plan pro Arbeitspaket, benannt `YYYY-MM-DD-thema.md`. Jeder Plan trägt einen
YAML-Frontmatter-Block mit `status`. **Diese Datei ist der Index — hier steht, was offen ist.**

Ein Plan ohne `status: open` ist **erledigt und darf nicht mehr ausgeführt werden.** Abgeschlossene
Pläne bleiben liegen, weil sie die Entwurfsentscheidungen festhalten, die spätere Änderungen nicht
rückgängig machen dürfen. Sie sind Nachschlagewerk, keine Aufgabenliste.

| Plan | Status | Umgesetzt in |
|---|---|---|
| [2026-07-28-git-fanta-ui-history-graph.md](2026-07-28-git-fanta-ui-history-graph.md) | abgeschlossen | `ag-tree-ui-01` → `c98b4aef` |
| [2026-07-29-history-commit-files.md](2026-07-29-history-commit-files.md) | abgeschlossen | `dev` → `86b9863d` |
| [2026-07-30-rename-to-git-fanta.md](2026-07-30-rename-to-git-fanta.md) | abgeschlossen | `renaming/opus5/minimax-M3` → `3083c9dd` |
| [2026-07-31-commit-file-diff-window.md](2026-07-31-commit-file-diff-window.md) | abgeschlossen | `tree-ui/diff-view/minimax-M3` → `c73ec4a2` |
| [2026-07-31-history-mouse-actions.md](2026-07-31-history-mouse-actions.md) | abgeschlossen | `tree-ui/mouse-actions/minimax-M3` → `e76b478a` |
| [2026-08-01-commit-description-panel.md](2026-08-01-commit-description-panel.md) | abgeschlossen | `tree-ui/description-panel/minimax-M3` → `16bd7e3a` |

## Wenn ein Plan fertig ist

Frontmatter ergänzen und die Zeile in dieser Tabelle umstellen:

```yaml
---
status: completed
completed_at: YYYY-MM-DD
plan_commit: <kurzer Hash des Commits, der den Plan hinzufügte>
implementation_branch: <branch>
implementation_head: <kurzer Hash des letzten Umsetzungs-Commits>
ci_run: <URL oder "nicht ausgefuehrt (lokal gruen)">
manual_verification: |
  - was tatsächlich von Hand geprüft wurde
---
```

`manual_verification` listet nur, was wirklich angesehen wurde. Was nur durch Tests abgedeckt ist,
gehört dort nicht hinein.
