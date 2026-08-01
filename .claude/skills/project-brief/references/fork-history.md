# What this fork changed, and the decisions behind it

git-fanta is a fork of git-cola and adds UI work around the commit history, plus the
rename that gave the fork its own name. Four work packages have shipped. Each has a plan document
in `docs/plans/` that records the reasoning; read the plan before changing the feature, because
several constraints in the code look arbitrary until you see why they were chosen.

Verify anything here against the tree before relying on it — this file is a map, not a mirror.

## 1. Inline commit history in the main window

Plan: `docs/plans/2026-07-28-git-fanta-ui-history-graph.md` (completed, frontmatter has the
implementation branch and CI run).

**What it delivered.** The main window has a History dock that is visible by default, showing an
inline commit graph over `ref='--all'`, 1000 commits, without WORKTREE/STAGE pseudo-commits. The
history UI that used to belong to the standalone DAG window was extracted into a reusable
`CommitHistoryWidget` (`cola/widgets/dag.py`), now shared by `MainView` and `GitDAG`.

**Decisions that later work must not undo:**

- **`cola/models/graph.py:build_graph()` is the single graph engine.** An earlier chunked
  variant dropped edges beyond ~2048 commits. The worker collects the full commit list and calls
  `build_graph()` exactly once; only the final result is applied to the view.
- **Each `RepoReader` owns its own `CommitFactory`.** A process-global commit cache collided
  between parallel reads.
- **Latest-desired-state loading.** Immutable `HistoryRequest`/`HistoryResult`, a run id, one
  active worker and exactly one coalesced pending request. Stale results are dropped rather than
  applied.
- **Failures preserve the last good history** and surface the return code plus the exact stderr
  non-modally. A successful *empty* history clears the visible state atomically.
- **The inline graph is palette-based and cache-free**, so light/dark themes work without
  invalidation logic. It is covered by semantic offscreen paint tests that run under both PyQt5
  and PyQt6 (`test/widgets_dag_history_test.py`, selected by `-k semantic_paint_smoke` in CI).
- **The standalone DAG window keeps everything it had** — its large `GraphView`, its Diff and
  Files docks, and its "Display Worktree Status" option.

`MainView` deliberately disconnects `model.updated` from `historywidget.model_updated`
(`cola/widgets/main.py`) and drives history reloads itself, and it hides history context-menu
actions that make no sense in the main window via `_MAIN_HISTORY_UNSUPPORTED_ACTIONS`.

## 2. Commit file panel next to the history table

Plan: `docs/plans/2026-07-29-history-commit-files.md`. Implemented across
`35633a02 → 86b9863d`, with follow-ups for layout and formatting.

**Shape.** The list of files changed in the selected commit is *not* a dock and not a tab. It is
the right pane of a horizontal splitter inside `CommitHistoryWidget`, so it cannot exist without
the history component. The precedent it follows is `cola/sequenceeditor.py`, which already lays
out the rebase tree and a `FileWidget` in exactly this way.

**Decisions that later work must not undo:**

- **Opt-in per host.** `CommitHistoryWidget(..., display_files=False)` by default; `MainView`
  passes `True`. The standalone DAG keeps its own `file_dock`, so its inline panel stays hidden.
  The parameter is **last** in the signature because tests construct the widget positionally.
- **No `widget_version` bump.** Both `MainView` and `GitDAG` are still at `widget_version = 2`.
  A splitter inside a dock is not part of `QMainWindow.saveState()`, so no layout migration is
  needed — and a bump would discard every user's saved geometry.
- **Panel state rides in the existing history state channel**: `display_files` and `files_sizes`
  in `CommitHistoryWidget.export_state()`, validated in `is_valid_state()`, applied in
  `apply_state()`. The `display_files` default on restore comes from the **action's current
  state**, i.e. from the host, which is why legacy states need no migration marker.
- **Debounce plus visibility guard.** A 100 ms single-shot timer coalesces rapid selection
  changes, and a hidden panel never runs git at all. The guard is a correctness requirement, not
  just an optimization: without it the DAG window would issue two `git show` calls per selection
  and break its "exactly once" assertion.
- **`FileWidget` stays synchronous.** Scheduling policy lives in the host
  (`_schedule_files` / `_load_pending_files` / `refresh_files` on `CommitHistoryWidget`),
  because a DAG test asserts synchronous population by name.
- **Status icons come from one git call.** `--raw` and `--numstat` are requested together, so
  status letters and +/- counts arrive without a second process. `parse_status_and_numstat()` in
  `cola/widgets/filelist.py` splits the two blocks; `icons.diff_status()` maps the letter to an
  existing asset and falls back to the file-type icon when the status is unknown.

`MainView` hides the file context-menu actions that would need host wiring, via
`_MAIN_HISTORY_UNSUPPORTED_FILE_ACTIONS` (`cola/widgets/main.py:65`), keeping only
"Launch Editor", which works standalone.

## 3. The rename to git-fanta

Plan: `docs/plans/2026-07-30-rename-to-git-fanta.md`. Implemented across `11e04304 → 54331885`.

**Scope.** Everything user-facing carries the fork name; the Python package does not.

| Renamed | Kept as `cola` |
|---|---|
| `bin/git-fanta`, `bin/git-fanta-sequence-editor`, the `git fanta` sub-command | the `cola/` package and every `import cola` |
| `pyproject.toml` `name = "git-fanta"` and the entry points | `[tool.setuptools] packages`, `cola/resources.py`'s `site-packages/cola` checks |
| `fanta.*` git-config keys (44 in `cola/models/prefs.py`, 34 more inline) | `icons.cola()` — see gotchas, renaming it breaks the toolbar silently |
| `GIT_FANTA_*` environment variables | `ColaApplication`, `ColaQApplication` |
| `~/.config/git-fanta`, `fanta-prepare-commit-msg` | upstream references (see below) |

**Decisions that later work must not undo:**

- **Nothing that points at the upstream project was rewritten.** `CHANGES.rst`, the ~40
  `github.com/git-cola/...` issue links in code comments, the remotes in `garden.yaml`, and
  `brew install git-cola` in the macOS CI job all refer to a real, still-existing project.
  `test/rename_guard_test.py` enforces both directions: no stray old product name, and the
  allow-listed upstream references still present.
- **Every user-facing rename has a backwards fallback**, so a pre-rename setup keeps working:
  `gitcfg._key_candidates()` probes `fanta.*` then `cola.*` (`cola/gitcfg.py:253`),
  `compat.getenv_with_legacy()` does the same for the env vars (`cola/compat.py:101`),
  `gitcmds.prepare_commit_message_hook()` still honours a `cola-prepare-commit-msg` hook, and
  `resources.migrate_config_home()` (`cola/resources.py:236`) copies (git-fanta was renamed from git-cola) `~/.config/git-cola` over
  once on first run.
- **`git fanta cola` still works.** The sub-command was renamed with an argparse alias
  (`cola/main.py:102`), so old scripts and shell history do not break.
- **The `.po` source references still say `cola/`,** because the package name did not change.
  Only the eight user-visible `msgid` strings were touched.

## 4. Double-click a commit file to see its diff

Plan: `docs/plans/2026-07-31-commit-file-diff-window.md`. Implemented across
`de79feca → c73ec4a2`.

**Single-clicking a file still does not show its diff** — the selection stays a selection.
**Double-clicking does**: `FileWidget.file_diff_requested` carries `(commits, path)` to the host,
which opens a reusable `CommitFileDiffWindow` (`cola/widgets/diff.py`).

**Decisions that later work must not undo:**

- **`set_commit_file()` seeds `oid`/`oid_start`/`oid_end` directly** instead of calling
  `CommitDiffWidget.commits_selected()`. That method starts a 100 ms debounce which fires *after*
  `files_selected()` and replaces the single-file diff with the whole-commit diff — measured:
  `filename=None`, two git calls instead of one. `test_set_commit_file_survives_the_debounce`
  guards it.
- **The window hangs off the host, not off `CommitHistoryWidget`.** `MainView` and `GitDAG` each
  own one `commit_file_diff_window` slot (`cola/widgets/main.py:145`, `cola/widgets/dag.py:2161`)
  and close it in their `closeEvent` so the geometry gets saved. The history widget may not own a
  `diffwidget` — `test_history_widget_owns_history_state_without_window_children` says so.
- **One window per host, reused.** `show_commit_file_diff(..., window=...)` returns the window it
  used; the host stores it. A second double-click reloads that window instead of opening another.
- **It is a `standard.Widget` with `Qt.Window`, not a `standard.Dialog`** — because `Browser`
  (`cola/widgets/browse.py:57`) is the project's pattern for a persisted, non-modal tool window,
  and `Dialog` brings an `accept()`/`reject()` result model plus a tendency toward modality that
  a viewer has no use for. **Not** because of state saving: both classes call `save_settings()`
  on close (`Dialog` routes through `closeEvent → reject()`), measured over both close paths.
- **`GitDAG` wires both of its file lists** — the `file_dock` one and the (hidden by default)
  inline panel of its `CommitHistoryWidget` — to the same window.
- **The rebase sequence editor is deliberately not wired.** `cola/sequenceeditor.py:174` holds a
  third `FileWidget` and does populate `FileWidget.commits`, so it emits `file_diff_requested`
  into nothing. A double-click there is a no-op by design.

## 5. Mouse actions and HEAD marking in the history

Plan: `docs/plans/2026-07-31-history-mouse-actions.md`.

**Double-clicking a commit switches branch.** `ViewerMixin.checkout_commit()` picks the action:
the tip of exactly one local branch is checked out by name, several branches go through the
existing `guicmds.checkout_branch()` dialog, the current branch's tip does nothing, and anything
else asks before detaching HEAD. `CommitTreeWidget` connects `itemDoubleClicked`, so it works in
the main window *and* in the DAG window's commit list.

**Decisions that later work must not undo:**

- **The `GraphView` is deliberately not wired.** It inherits `checkout_commit()` from
  `ViewerMixin` but has its own pan/drag mouse handling; a double-click there is a no-op by
  design.
- **`head_accent` is contrast-selected, not mixed.** The old
  `_mix_color(highlight, highlightedText, 0.52)` measured between 1.00 and 1.98 contrast over
  eight palettes — at 1.00 it *was* the background. `test_head_accent_stays_visible_against_row_
  and_node` holds the floor at 2.0.
- **The HEAD node got thicker, not bigger.** `HEAD_RING_RADIUS + HEAD_RING_WIDTH / 2 == 8` is a
  hard ceiling: the semantic paint test's tightest sample sits 9 px from the node center.
- **The current branch is marked with `chr(0x2605)` plus a 2 px chip border, never a new chip
  color.** `_distinct_chip_backgrounds()` returns exactly three colors, and
  `_TextRecordingPainter` records the chip *pen color* — changing it would break the adversarial
  contrast test.
- **A detached HEAD gets its own `HEAD` chip**, inserted by `GraphDelegate._row_labels()` only
  when no chip on that row was marked as the current branch. `commit.tags` alone cannot tell the
  two states apart — both read `['HEAD', 'heads/main']` on a branch tip.
- **`create_dock(..., title_indent=...)` defaults to 0**, so only the History dock is indented.

## 6. Commit description above the file list

Plan: `docs/plans/2026-08-01-commit-description-panel.md`.

The history's right-hand panel is a **vertical splitter**: the selected commit's message on top,
its changed files below. File names the message mentions are marked inside the text.

**Decisions that later work must not undo:**

- **The message is fetched per selection, not stored on `Commit`.** `LOGFMT`
  (`cola/models/dag.py:15`) stays subject-only: it is line-based, so a multi-line `%b` would break
  parsing for all 1000 commits and multiply their memory cost.
- **No second debounce.** The description rides the file panel's existing
  `_schedule_files` / `_files_timer` / `_load_pending_files` chain and its visibility guard.
- **The guards still ask `filewidget.isVisible()`** even though `display_files` now hides
  `details_splitter`. Hiding a parent splitter hides its children - measured, and the reason no
  guard had to change.
- **"Fuzzy" means path suffixes, not edit distance.** `commit_message_file_spans()` matches a path
  at every `/` boundary suffix, case-insensitively, never cutting into a surrounding token, longest
  candidate first. A basename *without* its extension is deliberately not a candidate - otherwise
  `main.py` would light up on the word "main".
- **The marking reuses `inline_graph_style()`**, so the file chips in the message look like the
  branch chips in the graph and inherit their contrast guarantee. That is also why the widget lives
  in `cola/widgets/dag.py`: `filelist.py` cannot import `dag.py` back.
- **The panel's text is exactly `%B`.** No author/date header - the columns already show that, and
  an exact text keeps the highlight offsets correct without translation.
- **`MonoTextEdit` starts with `NoWrap`**; `set_word_wrapping(True)` in the constructor is what
  makes the description readable.

## 7. Multi-commit selection lists the union of the touched files

Plan: `docs/plans/2026-07-31-history-multi-commit-file-list.md`.

Selecting several commits shows **every file those commits touch**, one row per file, with the
added and deleted lines summed. Before this, the multi-commit branch tried to diff the *range*
from the oldest to the newest selection and crashed with `UnboundLocalError` before showing
anything.

**Decisions that later work must not undo:**

- **Union, not range.** A range lists files from commits *between* two non-adjacent selections,
  hides changes that cancel out inside it, and shows nothing whenever the root commit is selected
  (`<root>~` does not resolve). All three measured.
- **One `git show` for the whole selection.** `git show` accepts several revisions and emits one
  raw+numstat block per revision, in the order given, in the same NUL-separated shape it uses for
  a single one. `parse_status_and_numstat` needed no change at all. One call also keeps
  `test_public_selection_reaches_all_standalone_consumers_synchronously` (which asserts exactly
  one `git.show` call) valid.
- **STAGE and WORKTREE are not revisions.** They keep their own `git diff-index` / `git
  diff-files` calls and their own newline separator. A selection therefore costs at most three
  git calls, no matter how many commits it holds.
- **Order is first appearance, not alphabetical.** That makes the single-commit case byte-for-byte
  what it was before: git's own order.
- **Binary files keep `-`.** `merge_numstat_rows()` refuses to invent a number for them, and a
  path that is binary in any one commit stays binary in the merged row.

## 8. Bug fixes after the multi-select work

Plan: `docs/plans/2026-07-31-history-bugfixes-1.md`.

Four unrelated defects found by hand-testing the history view.

**Decisions that later work must not undo:**

- **The file diff window never diffs a range.** It asks `gitcmds.commit_touching_path()` which of
  the selected commits last changed the path and diffs that single commit. A range renders empty
  whenever the change cancels out inside it or the oldest selection is the root commit, which is
  exactly what the union-based file list makes easy to hit.
- **Chip fills are nudged, not redesigned.** `readable_chip_fill()` only moves lightness, only
  when the fill fails a 2.5 contrast floor against the row it is painted on. Re-deriving the
  chips from the row background was measured and is worse; a 3.0 floor flattens all three.
- **A remote-only commit is checked out explicitly** with `-b <name> --track <remote>/<name>`.
  Never with plain `git checkout <name>`.
- **`MessageBox` sizes from `sizeHint()`**, floored at half `defs.dialog_w` so buttons stay
  readable and capped at `defs.dialog_w` so nothing grows.

## 9. Merge from the history context menu

Plan: `docs/plans/2026-08-01-history-merge-action.md`.

Right-clicking a history row whose branch has commits the current branch lacks offers
`Merge "<branch>" into "<current>"`, opening the standard merge dialog with that branch chosen.

**Decisions that later work must not undo:**

- **"Mergeable" is `git rev-list --count HEAD..<ref> > 0`,** not
  `git merge-base --is-ancestor`. The latter reports a diverged branch as unmergeable, which is
  wrong: a diverged branch is the ordinary merge case.
- **A ref that does not resolve is a "no", not an error.** git exits 128 there and the output is
  empty, so the status is checked and the text compared rather than parsed with `int()`.
- **One deterministic candidate per row.** Local branch first, then remote. Every ref at a commit
  merges identically, so the choice only decides the wording — but it must not vary.
- **Preselection sets the radio, the list selection and the field together.** The field alone was
  what the dialog did before, and it loses to the first click on the revision list. The field is
  written last, after the list item is selected, because selecting an item writes it back.
- **The Branches dock was left alone.** It still merges immediately without a dialog. Changing it
  is a separate decision.

## 10. Five history-view improvements

Plan: `docs/plans/2026-08-01-history-ui-improvements.md`.

A Hash column, an ISO date, roomier chips, a branch chooser for an ambiguous double-click, and
tags that are actually visible.

**Decisions that later work must not undo:**

- **The Hash column is last and is not part of the saved state.** `column_widths` was already
  truncated to two entries in `CommitHistoryWidget.export_state()`, so the new column needed no
  migration and no state assertion changed. `setStretchLastSection(False)` is required: Qt
  stretches the last section by default and would otherwise let the hash swallow the window.
- **The date is formatted by git, never parsed.** `Defaults.logdate` is
  `format:%Y-%m-%d %H:%M`; `get_date_for_current_time()` already routed a `format:` value through
  `DateFormat.is_custom()`, so the STAGE and WORKTREE rows matched without a change. Carrying a
  second date field on 1000 `Commit` objects was the alternative and was rejected.
- **`sizeHint` reserved `fontMetrics.height() + 4`, which is exactly the padded chip and no
  margin at all.** Measured over eight font sizes: from about 11 pt the chip was as tall as its
  own row, and `paint()` clips to `option.rect`, so the corners were cut off. `ROW_V_MARGIN = 2`
  is the fix, and it is a no-op at 8–9 pt where the `ROW_HEIGHT` floor already won.
- **Row height is asserted as a property, not a number.** The two tests that pinned it to `26`
  were only true on the machine that wrote `26` down; one of them was already failing on a 12 pt
  desktop font. They now assert that the row is at least as tall as the chip plus its margin.
- **The padding lives in two places that must agree**: `_draw_labels` draws the box,
  `_label_hit_test` recomputes it, and two tests compare the two.
- **`SelectBranchDialog` offers local branches only.** Mixing in the remote refs would make one OK
  button mean *switch branch* on some rows and *create a tracking branch* on others. The
  remote-only and multi-remote double-click paths are unchanged.
- **Four existing dialogs were checked before adding one** — `GitCheckoutBranchDialog`,
  `SelectRemoteBranch`, `SelectCommits` and `Switcher`. §2.4 of the plan records why each is the
  wrong shape.
- **A tag is marked three ways**: `chip_tag`, bold text and the `⚑` glyph. One signal is not
  enough — on a greyscale palette the four fills are forced apart by lightness alone and hue stops
  carrying meaning.
- **`chip_tag` is the palette highlight rotated half a turn** with a saturation and a value floor.
  Measured over thirteen palettes: four distinct fills on both row backgrounds, worst contrast
  2.50.
- **The bold weight needs the `QFont`, not just the metrics.** `QFontMetrics` does not expose the
  font it was built from, so `_draw_labels`, `_labels_width` and `_label_hit_test` all take an
  optional trailing `font`. The chip *height* keeps using the plain metrics — a bold font changes
  the advance, not the line height.
- **A new parameter on `_draw_labels` goes last.** One test calls it with nine positional
  arguments.

## 11. The paint path stopped rebuilding its colors, and the package became `fanta`

Plan: `docs/plans/2026-08-01-paint-performance-and-fanta-module.md`.

**Decisions that later work must not undo:**

- **`inline_graph_style()` is memoized on the palette, not cached with invalidation.** It cost
  5.1 ms and ran once per painted row, which put the history at about six frames per second.
  Keying on the five palette roles keeps the original "no invalidation logic" property: a theme
  change is a different key. Measured afterwards: 15 us per call, and a 30-row repaint went from
  156 ms to 6.0 ms.
- **The cache key is `(color.isValid(), color.rgba())`, and both halves are load-bearing.** An
  invalid `QColor` and opaque black report the same `rgba()`, and `_opaque_color()` treats them
  differently.
- **`InlineGraphStyle` being frozen is what makes sharing one instance safe.** Do not make it
  mutable.
- **The color math was not touched.** `_lane_colors`, `_distinct_chip_backgrounds` and
  `readable_chip_fill` keep their algorithms; only the entry points memoize. After that the
  profile is Qt's own `drawText` and `drawRoundedRect`.
- **`_prepare_labels`, `_row_labels` and `_tag_fonts` are deliberately not cached** — measured at
  3.5-12 us, together under 0.5 ms of a 6 ms repaint. `_tag_fonts` additionally returns a
  **mutable** `QFont`; caching that would break the "never mutate what you were handed" invariant
  the other three caches rely on.
- **The reader and the graph builder were profiled and left alone**: 64 ms for 1000 commits, 45 ms
  of which is the `git log` subprocess, on a worker thread.
- **The package rename is shallow on purpose.** Imports, module-path literals, packaging, build
  files, the three extensionless launchers in `bin/`, and the two `resources.py` literals that
  decide the installation prefix. Everything that merely *reads* like the old name stays: the
  `git fanta cola` alias, `icons.cola()` and the `'icon': 'cola'` entries that reach it through
  `getattr`, the `cola.*` config fallback, `ColaApplication`, `~/.cola`, and the `.po` source
  references.
- **`test/diffparse_test.py` still names the old package three times** because those lines describe
  `test/fixtures/diff.txt`, a captured diff. Rewriting them breaks the test; rewriting the fixture
  changes what the parser is tested against.
- **`icons.from_name()` takes an `icons:` name, `icons.icon()` takes a basename.** The file panel
  passed a bare basename to the first one, so Qt looked for `plus.svg` in the repository the user
  had opened and every status icon was invisible. `icons.icon()` is the prefixing helper; every
  other call site already used it or prefixed by hand.
- **Two tests register the icon search path on purpose** and restore it, which is the exception to
  "icons do not resolve in tests". They clear `icons.from_name.cache` at both ends, because a
  memoized icon built before the path existed stays broken afterwards.

## Where the fork's tests live

- `test/widgets_dag_history_test.py` — `CommitHistoryWidget`, `GitDAG`, state round-trips,
  the semantic paint smoke tests, and the structural invariant test that says what the reusable
  history widget may and may not own.
- `test/widgets_main_history_test.py` — `MainView` integration: dock visibility, state export,
  legacy windowstate restore, refresh-on-command behavior, the file panel in the main window.
- `test/widgets_history_filelist_test.py` — `FileWidget` characterization plus the
  `--raw --numstat` parser and the status-icon mapping.
- `test/widgets_commit_file_diff_test.py` — `CommitFileDiffWindow`, the single-file diff
  seeding, window reuse, and the debounce regression guard.
- `test/diff_debounce_test.py` — the debounce/supersede pattern in `CommitDiffWidget` that the
  file panel's scheduling was modeled on.
- `test/rename_guard_test.py` — the rename invariants: no stray old product name in the tracked
  sources or filenames, the allow-listed upstream references intact, `CHANGES.rst` untouched, no
  leftover `'cola.<key>'` config literals, and the coupling between `pyproject.toml`'s `name` and
  `cola/version.py`.
- `test/env_rename_test.py`, `test/config_home_migration_test.py`,
  `test/prepare_commit_msg_hook_test.py` — one file per backwards fallback introduced by the
  rename. If you remove a fallback, these are the tests that are supposed to stop you.
- `test/widgets_dag_history_test.py` enthält zusätzlich die Tabellentests für
  `commit_message_file_spans()` und die Format-Tests des Beschreibungsfelds.
- `test/widgets_history_filelist_test.py` additionally holds the table test for
  `merge_numstat_rows()` and the multi-commit selection tests against a real repository
  (fixture `history_repo`).
- `test/widgets_history_checkout_test.py` — die Checkout-Regel des Doppelklicks: Branch-Spitze,
- `test/widgets_merge_preselect_test.py` covers the merge dialog's preselection; the menu entry
  itself is covered in `test/widgets_history_checkout_test.py`.
  Mehrdeutigkeit, aktueller Branch, abgelöster HEAD, Pseudo-Commits.
