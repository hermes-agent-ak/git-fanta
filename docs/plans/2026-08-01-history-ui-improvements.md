---
status: open
---

# Five history-view improvements: hash column, ISO date, chip padding, branch chooser, prominent tags

**Created:** 2026-08-01
**Branch:** Commit the tasks onto whatever branch is checked out at the start. **Never onto
`main`** — the pattern for feature work is `tree-ui/<agent>/<model>/<topic>`. Check before Task 1:
`git rev-parse --abbrev-ref HEAD`. If it says `main`, create a branch first. This plan does **not**
create one.
**Affects:** `cola/models/prefs.py`, `cola/widgets/dag.py`, `test/dag_test.py`,
`test/widgets_dag_history_test.py`, `test/widgets_history_checkout_test.py`, plus three
documentation files in the final task.

---

## 0. How to read this plan

This plan is written so that it can be executed **without prior knowledge and without making any
decisions of your own**.

- **Do the tasks strictly in order 0 → 7.** Skip nothing. Each task leaves the suite green.
- **One task = one commit.** The commit message is written out verbatim at the end of each task.
  Use it as it stands.
- **Commit only. Never push.** No task in this plan runs `git push`, and none should. The branch
  stays local; whoever reviews the work decides when it leaves the machine. Do not open a pull
  request either.
- **Every task has RED → GREEN → VERIFICATION.** Where a RED step names an expected error, the
  actual output must match it. If it does not: **stop and report**, do not continue.
- **Line numbers are orientation, not truth.** Every edit is preceded by a `grep` that finds the
  anchor. Use the `grep`, not the line number.
- **Copy the code blocks verbatim.** Every block in this plan was written by applying it to this
  repository and running the suite. Do not "improve" it while typing it in.
- If a command fails and the plan names no way out: **stop and report.**

**Language.** Everything written into the repository is **English**: code, comments, docstrings,
test names, commit messages, documentation. Some files still contain German from before
2026-07-31 — do not match them, and do not translate them as a side effect of this plan. The one
exception is `docs/plans/README.md`, which Task 7 translates on purpose.

**Working directory.** All commands run in the **root of the repository** — where `pyproject.toml`
and `garden.yaml` live. Every path in this plan is **relative to that directory**; the plan
contains no absolute paths and needs none.

**Tool substitution — settle this once in Task 0, then apply it everywhere.**

| Written in the plan | Replace with, if that does not run |
|---|---|
| `python3 -B -m pytest …` | `env3/bin/python -B -m pytest …`, as soon as `env3/` exists |
| `garden fmt` | `cercis cola test` followed by `isort --force-single-line-imports --py=39 --no-lines-before=STDLIB cola test` |
| `garden check/fmt` | `cercis --check cola test` |

> **Important:** if Task 0 creates an `env3/`, then `env3/bin/python` applies to **every** further
> `pytest` call in this plan. A `python3 -m pytest` that aborts with `No module named pytest` is
> **not** a RED, it is the wrong substitution.

Standard test command:

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test
```

---

## 1. What is being built

Five independent improvements to the history view in the main window (and, because they share the
same widget, to the standalone DAG window).

1. **A Hash column.** The history shows `Summary | Author | Date, Time` and never the object ID.
   A fourth column at the right end shows the abbreviated hash.
2. **An ISO date, minute precision.** The Date, Time column shows
   `Sat Aug 1 12:11:20 2026 +0200` today. It will show `2026-08-01 12:11`.
3. **More padding inside the branch chips, and a row that has room for them.** The chip box is
   exactly as tall as the text, so a descender (`g`, `p`, `y`) touches the bottom border. Two more
   pixels on every side — and the row grows with the chip instead of clipping it.
4. **A branch chooser for an ambiguous double-click.** Double-clicking a commit that carries two
   local branch heads opens the generic *Checkout Branch* dialog, which offers **every** branch in
   the repository. It will open a small dialog that offers **exactly the branches on that commit**.
5. **Prominent tags.** A tag chip is painted in the same color as the `HEAD` chip and in the same
   weight as a branch, so it disappears among the branches. It gets a chip color of its own, a
   bold label and a tag glyph — what GitKraken, Fork and Sourcetree all do in some form.

### Settled decisions

| Question | Decision |
|---|---|
| Where does the Hash column go? | **Last**, right of Date, Time. That is where Sourcetree and Fork put it, and it keeps `SUMMARY = 0` — the graph delegate is installed on column 0 and three item-data roles hang off it. |
| How long is the abbreviated hash? | `prefs.abbrev(context)` — the existing `core.abbrev` setting, default 12. The same helper `_confirm_detached_checkout()` already uses. Read **once per widget**, not per row. |
| What does the Hash column show for STAGE / WORKTREE? | **Nothing.** They are pseudo-commits; `'STAGE'[:12]` would read like a real, very short hash. |
| Which column absorbs the window's slack? | **Date, Time**, exactly as today. `QHeaderView` stretches the *last* section by default, so `setStretchLastSection(False)` is required or the Hash column would swallow the window. |
| Is the Hash column width saved? | **No.** `CommitHistoryWidget.export_state()` already truncates `column_widths` to the first two entries on purpose. Leaving that alone means **no state migration and no changed state assertions**. The Hash column gets a measured width at construction time instead. |
| How is the ISO date produced? | Through the setting that already exists: `fanta.logdate`, whose **default** becomes `format:%Y-%m-%d %H:%M`. git formats the date; nothing parses a date string. A user who explicitly configured another format keeps it. |
| Why not format the date in the widget? | It would mean carrying a second date field on every one of the 1000 `Commit` objects, changing `LOGFMT` and `Commit.parse()`, and it would make the existing *Log Date Format* preference dead for the one view that uses it. |
| How much padding? | `LABEL_TEXT_OFFSET` 2 → 4 horizontally and a new `LABEL_V_PADDING = 2` vertically. "2 px more on every side", as asked. |
| Does the row get taller? | **Only where it has to.** `sizeHint` reserved `fontMetrics.height() + 4`, which is exactly the height of the padded chip — no margin at all. A new `ROW_V_MARGIN = 2` guarantees 2 px above and below the chip at every font size. Measured: at 8–9 pt nothing changes, because the `ROW_HEIGHT = 26` floor was already larger; from 10 pt upwards the row grows by 2–4 px. |
| Why not just leave the row alone? | Measured over eight font sizes: from `fontMetrics.height() >= 22` (≈11 pt) the chip is exactly as tall as its row, and `paint()` clips to `option.rect`, so the rounded corners are cut off and the chip overflows the top by one pixel. That is what the reviewer saw in the rendered screenshot. |
| Which branches does the new dialog offer? | The **local** branches on that commit — the same list `checkout_commit()` already has in `commit.branches`. Remote-only and multi-remote rows keep the behaviour they have today (see §3). |
| Is a new widget class needed for it? | **Yes.** §2.4 lists the four existing dialogs that were checked and why each is the wrong shape. |
| What makes a tag prominent? | Three signals, because a single one degrades on some palettes: a fourth chip color derived from the palette highlight rotated half a turn on the hue wheel, **bold** label text, and a leading `⚑` glyph. |
| Why a glyph as well as a color? | On a greyscale or collapsed palette the four chip colors are forced apart by lightness alone, and hue stops carrying meaning. The glyph and the weight still do. The current-branch star (`★`) is the precedent, and its hit-area test proves the mechanism. |

## 2. Root causes and ground truth — all measured

### 2.1 The columns

`CommitTreeWidgetItem` (`cola/widgets/dag.py:1680`) defines `SUMMARY = 0`, `AUTHOR = 1`,
`DATE = 2` and sets three texts. `CommitTreeWidget.__init__` (`:1703`) names three header labels
and gives `DATE` `QHeaderView.Stretch`. Measured on a freshly built tree in this repository:

| | value |
|---|---|
| `header().stretchLastSection()` | `True` (Qt's default for a `QTreeView`) |
| `CommitHistoryWidget.export_state()['log']['column_widths']` | truncated to `[:2]` at `cola/widgets/dag.py:2463` |
| `CommitTreeWidget.apply_state()` | applies `column_widths[:2]` at `:1757` |

So a fourth column is invisible to the saved state in both directions, and needs no migration.

### 2.2 The date

`RepoReader.get()` (`cola/models/dag.py:322`) passes `--date=%s % prefs.logdate(context)` to
`git log`, and `LOGFMT` reads the result with `%ad`. `prefs.logdate` is read in exactly two places
(`cola/models/dag.py:325` and `:445`) and written in one (`cola/widgets/prefs.py:276`); its default
is `DateFormat.DEFAULT`. Measured in a scratch repository:

| `fanta.logdate` | `%ad` renders as |
|---|---|
| `default` (today) | `Sat Aug 1 12:11:20 2026 +0200` |
| `format:%Y-%m-%d %H:%M` (new default) | `2026-08-01 12:11` |

Two further facts, both measured:

- **`--date=format:%Y-%m-%d %H:%M` keeps the author's own time zone.** `TZ=America/New_York` and
  `TZ=UTC` produced the identical string. That matches what `%ad` has always done.
- **`get_date_for_current_time()` already handles it.** Its `DateFormat.is_custom(logdate)` branch
  (`cola/models/dag.py:467`) runs `strftime('%Y-%m-%d %H:%M')`, so the STAGE and WORKTREE
  pseudo-commits format identically **without any change to that function**.

### 2.3 The chips

`GraphDelegate._draw_labels()` (`:1501`) builds the chip box as

```python
text_rect = QtCore.QRectF(current_x, y - text_height / 2, text_width, text_height)
box_rect = text_rect.adjusted(-x_offset, -y_offset, x_offset, y_offset)
```

with `x_offset = self.LABEL_TEXT_OFFSET` (2) and a hard-coded `y_offset = 0`. A zero vertical
offset means the box top and bottom sit exactly on the text's ascent and descent lines, which is
the reported collision. `_label_hit_test()` (`:1627`) recomputes the same box and must be changed
in lockstep — two tests compare the drawn rectangle against the hit area
(`test_24pt_visible_chip_and_hit_area_have_identical_boundaries`,
`test_marked_chip_and_hit_area_have_identical_boundaries`).

Measured after the change, with the offscreen default font (`fontMetrics().height() == 24`):

| | before | after |
|---|---|---|
| chip height | 24 | 28 |
| chip width for `main` | text + 4 | text + 8 |
| `sizeHint().height()` | `max(26, 24 + 4)` = 28 | `max(26, 28 + 2*2)` = 32 |

The row height matters more than it looks. `sizeHint` reserved `fontMetrics.height() + 4`, which is
**exactly** the height of the padded chip — the row had no margin left over. Measured across font
sizes with the project's own default font:

| point size | `fontMetrics.height()` | chip | row without `ROW_V_MARGIN` | slack per side | row with it |
|---|---|---|---|---|---|
| 8 | 16 | 20 | 26 | 3.0 | 26 |
| 9 | 18 | 22 | 26 | 2.0 | 26 |
| 10 | 20 | 24 | 26 | 1.0 | 28 |
| 11 | 22 | 26 | 26 | **0.0** | 30 |
| 12 | 24 | 28 | 28 | **0.0** | 32 |
| 18 | 35 | 39 | 39 | **0.0** | 43 |
| 24 | 46 | 50 | 50 | **0.0** | 54 |

At zero slack `paint()`'s `setClipRect(option.rect)` cuts the rounded corners and the chip
overflows the top by one pixel (`QRect.center()` rounds down). `ROW_V_MARGIN = 2` makes the margin
2 px on every side at every size, and changes **nothing** at 8–9 pt, where the `ROW_HEIGHT = 26`
floor already won.

Nothing else in the application reads `ROW_HEIGHT`: `grep -rn ROW_HEIGHT cola/ test/` returns
`sizeHint` and the semantic paint test's row rectangles, which use the constant itself.
`TreeMixin` sets `setUniformRowHeights(True)` (`cola/widgets/standard.py:366`), so Qt takes the
height from the first row — every history row uses the same font, so they are identical anyway.

### 2.4 The ambiguous double-click, and the search for an existing component

`ViewerMixin.checkout_commit()` (`:340`) sends the ambiguous case to
`guicmds.checkout_branch(context, default=branches[0])`, which opens
`completion.GitCheckoutBranchDialog` — a line edit whose completer is
`GitCheckoutBranchCompletionModel`, i.e. *all* local branches, *all* potential branches, *all*
remote branches and *all* tags (`cola/widgets/completion.py:628`). Four existing components were
checked before deciding to add one:

| Candidate | Where | Why it does not fit |
|---|---|---|
| `completion.GitCheckoutBranchDialog` | `cola/widgets/completion.py:926` | Its content comes from a completion model bound at class-creation time by `bind_lineedit()`; `GitDialog.get()` constructs `cls(context, title, text, parent, icon=icon)` and has nowhere to pass a list. A free-text field is also the wrong affordance for a choice between two known names. |
| `branch.SelectRemoteBranch` | `cola/widgets/branch.py:926` | The closest shape (Dialog + single-selection list + OK/Close) but hard-wired to `context.model.remote_branches` and to a `GitRemoteBranchLineEdit`, with slash-selection helpers and an upstream-branch concept that mean nothing here. |
| `selectcommits.SelectCommits` | `cola/widgets/selectcommits.py:42` | Carries a `DiffTextEdit`, a search box and a revision field, calls `gitcmds.commit_diff()` on every selection change, and returns commit IDs. |
| `switcher.Switcher` | `cola/widgets/switcher.py:48` | A non-modal quick switcher over a shared item model; it has no accepted/rejected result to read. |

`qtutils.prompt()` and `qtutils.prompt_n()` were also checked: both are text-input dialogs.

What *is* reused: `standard.Dialog`, `qtutils.set_items()`, `qtutils.selected_item()`,
`qtutils.ok_button()`, `qtutils.close_button()`, `qtutils.default_size()` and `icons.branch()`.
The new class is ~50 lines of wiring around them.

### 2.5 The tag chips

The brush is chosen in `_draw_labels()` by ref prefix. Today:

| ref | chip color |
|---|---|
| `HEAD` **and** `tags/…` | `chip_remote` |
| `heads/…` | `chip_head` |
| everything else, including `remotes/…` | `chip_other` |

So a tag is painted exactly like the detached-`HEAD` chip, and its label is drawn in the row font
like every branch. Measured over the light palette used in the paint tests, the three chip fills
are `#f2f4f7`, `#a6bcdb` and `#638cc4` — three shades of the same blue, because all three are
mixed from the palette highlight.

The fourth color proposed in Task 6 is the highlight with its hue rotated by 0.5, floors of 0.55
on saturation and 0.45 on value, mixed 18% towards the base. Measured over **13 palettes** — the
two realistic ones from the paint tests, the three demo palettes, the greyscale demo palette, the
five adversarial ones (all-black, all-mid-grey, all-white, fully transparent, fully invalid), the
achromatic one and the one from the offscreen node test — with the fills passed through
`readable_chip_fills()` against both the base row and the selected row:

| | result |
|---|---|
| four distinct colors, every palette, both backgrounds | **13/13** |
| worst contrast against the row | **2.50** (floor is 2.50) |
| tag hue vs. branch hue, light palette | `0.096` (amber) vs `0.595` (blue) |
| tag hue on a fully greyscale palette | `0.5` (teal) while every other chip stays grey |

## 3. Non-goals

- **No new date parsing.** git formats the date; the application never reads one back.
- **No change to which column stretches**, and no change to `resizeColumnToContents(SUMMARY)`
  after the graph loads. That call can still push the Date column down to its minimum on a narrow
  dock — measured, and it does that today too, with a date string that is 29 characters instead of
  16. This plan makes that situation better, not worse, and does not otherwise touch it.
- **No `widget_version` bump.** Nothing about a column lives in `QMainWindow.saveState()`.
- **No change to the state schema.** `column_widths` stays truncated to two entries.
- **No renaming of `chip_remote`.** After this plan it paints only the `HEAD` chip, which makes
  its name worse than it already was. Renaming it touches five test call sites for no behavioural
  gain; §7 records the new mapping in `references/gotchas.md` instead.
- **No new chip for remote branches.** They keep landing in `chip_other`.
- **The two existing inline abbreviations are left alone.** `_confirm_detached_checkout()`
  (`cola/widgets/dag.py:93`) and `ViewerMixin.with_oid_short()` (`:174`) both slice
  `oid[: prefs.abbrev(context)]` by hand. Neither can be reached with a pseudo-commit — the
  first is called after `checkout_commit()` has already returned for STAGE and WORKTREE, and the
  second only ever sees a clicked object ID — so routing them through `short_oid()` would change
  nothing except the diff size.
- **The standalone DAG window's *graphics view* is not touched.** Its node labels are painted by
  `Label.paint()` (`cola/widgets/dag.py:3456`) from three **hard-coded** class colors —
  `head_color = Qt.green`, `other_color = Qt.white`, `remote_color = Qt.yellow` (`:3403-3405`) —
  with no palette, no `InlineGraphStyle` and no shared code with the delegate. Tags there are
  already yellow against green branches, so they are not the reported problem; making that widget
  palette-aware is a separate work package. Everything in this plan applies to the **inline**
  graph, which is what the main window shows and what the DAG window's commit list uses.
- **No change to the remote-only and multi-remote double-click paths.** A commit carrying one
  remote branch still creates a tracking branch; a commit carrying two still refuses to guess.
  Mixing remote refs into the new dialog would make one OK button mean *switch branch* on some
  rows and *create a new local branch* on others.
- **No submenu, no context-menu entry** for the branch choice. It is reached by double-click only,
  exactly like today.
- **No translation catalog update.** The new `msgid`s (`Hash`, the dialog's label and title) fall
  back to English, which is what every string added by the previous four plans does.
- **`test/git_test.py` is not fixed.** See Task 0.

## 4. Traps — all empirically verified

| # | Trap | Evidence |
|---|---|---|
| **F1** | **The suite is not green on a clean checkout in this environment.** Five tests fail before any change: the four in `test/git_test.py` and `test_graph_delegate_offscreen_nodes_selection_lanes_and_size`. The latter asserts `hint.height() == 26`, which depends on the desktop font — this machine's default is 12 pt Noto Sans, giving `fontMetrics().height() == 24` and therefore 28. **Do not "fix" `test/git_test.py`.** The height assertion is different: Task 3 changes the very formula it pins, so Task 3 replaces it with a font-independent one — and from Task 3 onward the baseline is **four** failures, not five. | Measured on `dc150fc3` with a clean tree: `5 failed, 755 passed`; after Task 3: `4 failed` |
| **F2** | **A modal dialog reached from a test hangs the whole run forever**, with no error and no timeout. Replacing `guicmds.checkout_branch` with the new dialog without updating `test_several_branches_at_one_commit_open_the_checkout_dialog` first makes pytest stop after 6 dots and never return. Task 5 therefore rewrites that test **in the RED step**, before the production change. | Measured: the run had to be killed; `pytest -q` had printed `......` and hung |
| **F3** | **`QFontMetrics` cannot hand back the font it was built from.** `hasattr(metrics, 'font')` is `False` under PyQt5. Bold tag labels therefore need the `QFont` itself passed alongside the metrics into `_draw_labels`, `_labels_width` and `_label_hit_test`, or the painted chip and the measured width disagree. | Measured: `'QFontMetrics' object has no attribute 'font'` |
| **F4** | **A bold font does not change the line height, only the advance.** `QFontMetrics(bold).height()` equals `QFontMetrics(plain).height()`; the advance for `v1.2.3` grew 47 → 49. So the chip *height* must keep using the plain metrics — otherwise chips in one row stop lining up. | Measured under PyQt5 |
| **F5** | **`QHeaderView` stretches the last section by default.** `header().stretchLastSection()` is `True` on a fresh `QTreeWidget`. Adding a fourth column without `setStretchLastSection(False)` makes the Hash column take all the slack and squeezes Date to nothing. | Measured |
| **F6** | **The drawn chip and the hit area are compared by two tests.** `test_24pt_visible_chip_and_hit_area_have_identical_boundaries` probes `chip.top()`, `chip.bottom()` and 0.01 px outside them; `test_marked_chip_and_hit_area_have_identical_boundaries` probes the left and right edges. Any padding change must land in `_draw_labels` **and** `_label_hit_test`. | `test/widgets_dag_history_test.py:1144`, `:3675` |
| **F7** | **`test_selected_inline_summary_and_each_chip_have_contrasting_text` compares the painted chip backgrounds against an exact list** built from `(chip_other, chip_remote, chip_head)`, and asserts the drawn label texts by value. Both break the moment tags get their own color and their own glyph. | `test/widgets_dag_history_test.py:1281-1291`; measured failure: `At index 1 diff` |
| **F8** | **`_draw_labels` is called positionally with 9 arguments in one test**, and the two trailing arguments are passed in the opposite order to their parameter names. Any new parameter must go **last**, and the existing call must not be touched. | `test/widgets_dag_history_test.py:1216-1226` |
| **F9** | **`_prepare_labels()` drops `'HEAD'`,** and `_row_labels()` re-inserts a `HEAD` chip only when no chip on the row was marked as the current branch. The tag marker must therefore be added with an `elif` chain that leaves the `marked` flag alone — a tag can never be the current-branch ref, because that requires the `heads/` prefix. | `cola/widgets/dag.py:941`, `:1337`; `references/gotchas.md` |
| **F10** | **`app_context.settings` is a raw `Mock`, and a `Mock` is truthy.** `SelectBranchDialog` avoids the whole problem by calling `init_state(None, …)`, the way `selectcommits.SelectCommits` does. Do not pass `context.settings` to it. | `references/gotchas.md`; `cola/widgets/selectcommits.py:98` |
| **F11** | **`prefs.abbrev(context)` needs a real `cfg`.** The `app_context` fixture provides one, so reading it in `CommitTreeWidget.__init__` is safe in tests. A bare `Mock()` context would make `int(Mock)` raise. Every test in this repository that builds a `CommitTreeWidget` uses `app_context`. | `test/helper.py:92-96`; verified by grep over `test/` |
| **F12** | **`guicmds` becomes unused in `test/widgets_history_checkout_test.py`** once the checkout-dialog patch goes away, but stays used in `cola/widgets/dag.py` (`ViewerMixin.checkout_branch`, the context-menu action). Remove the test import; keep the production one. | `grep -n guicmds` on both files |
| **F13** | **`pytest.ini` sets `--doctest-modules`.** A `>>>` in a new docstring becomes a test. None of the docstrings in this plan contain one. | `pytest.ini` |
| **F14** | **CI runs ruff on two test files only** — `test/widgets_dag_history_test.py` and `test/widgets_main_history_test.py`. This plan edits the first of them, so an unused or misplaced import there is a CI failure, not a style opinion. The second is not touched. | `.github/workflows/ci.yml:51-54` |
| **F17** | **Two tests pin the row height to a literal.** `test_graph_delegate_offscreen_nodes_selection_lanes_and_size` asserts `hint.height() == 26` and `test_24pt_visible_chip_and_hit_area_have_identical_boundaries` asserts `hint.height() == max(26, metrics.height() + 4)`. Both encode the formula Task 3 replaces, and the first one is already red on any machine whose desktop font gives `fontMetrics().height() > 22`. Task 3 rewrites both to assert the property instead of the number. | Measured: `assert 32 == 26` and `assert 54 == 50` after the formula change |
| **F16** | **`_row_labels()` has a second caller in the test suite.** `test/widgets_main_history_test.py:1658` asserts that the row of a freshly checked-out branch renders as `['★ topic']`. The tag marker is added under an `elif` for `tags/` refs only, so that assertion is unaffected — verified green after Task 6. Do not "helpfully" update it. | `test/widgets_main_history_test.py:1656-1661` |
| **F15** | **Astral-plane emoji cannot even be probed with `QFontMetrics.inFont()`**, which raises `ValueError: string of length 1 expected` for `chr(0x1F3F7)`. `chr(0x2691)` (`⚑`) is in the BMP and reported present, like the `★` already in use. | Measured |

## 5. What already exists and is reused (do not rebuild)

| Exists | Where | Role in this plan |
|---|---|---|
| `DateFormat.FORMAT` / `is_custom()` / `get_custom_format()` | `cola/models/prefs.py:76-97` | The custom-format machinery the new default rides on. No new code path. |
| `get_date_for_current_time()` | `cola/models/dag.py:442` | **Already** formats the pseudo-commit date through `is_custom`. Untouched. |
| `prefs.abbrev(context)` | `cola/models/prefs.py:195` | The abbreviation length. No new setting. |
| `qtutils.fontmetrics_width(metrics, text)` | `cola/qtutils.py:1621` | The project's own width helper, with its `horizontalAdvance` fallback. `filelist._resize_columns()` (`cola/widgets/filelist.py:159`) sizes its columns exactly this way; the two new width helpers follow it. |
| `readable_chip_fills(fills, background, floor)` | `cola/widgets/dag.py:1157` | Generic over the tuple it is handed; four fills need no change to it. |
| `_distinct_chip_backgrounds()` | `cola/widgets/dag.py:1184` | Only its fallback hue list grows from three shifts to four. |
| `_mix_color`, `_opaque_color`, `_best_contrast` | `cola/widgets/dag.py:1001-1050` | The color helpers `_tag_chip_color()` is built from. |
| `CURRENT_BRANCH_MARKER` and its handling in `_row_labels()` | `cola/widgets/dag.py:1287`, `:1337` | The **template** for the tag marker: put the glyph in `display_text`, and every width, chip and hit-area calculation picks it up for free. |
| `standard.Dialog`, `qtutils.set_items`, `qtutils.selected_item`, `qtutils.ok_button`, `qtutils.close_button`, `qtutils.default_size`, `icons.branch()` | `cola/widgets/standard.py:592`, `cola/qtutils.py` | Everything `SelectBranchDialog` is assembled from. |
| `app_context` fixture | `test/helper.py:85` | A real temporary git repository for every test here. |
| `_commit`, `_graph_result`, `_tree`, `_palette`, `_contrast`, `_draw_row_labels`, `_TextRecordingPainter`, `_adversarial_chip_palettes` | `test/widgets_dag_history_test.py:95`, `:107`, `:116`, `:510`, `:527`, `:3604`, `:1088`, `:1193` | **Already in the file.** Reuse them; the only change to any of them is one recorded field in `_TextRecordingPainter` (Task 6). |
| `qapp`, `managed_qobject`, `_git`, `_fake_commit`, `_never_confirm` | `test/widgets_history_checkout_test.py:28`, `:39`, `:57`, `:76`, `:98` | **Already in the file** Task 5 extends. |
| `helper.commit_files()` | `test/helper.py:67` | Makes the fixture repository have a commit, which `RepoReader` needs. |

---

# TASKS

## Task 0 — Make sure the tests run, and record the baseline

> **Blocking. No commit.**

```bash
git rev-parse --abbrev-ref HEAD
python3 -m pytest --version 2>&1 | head -1
ls -d env3 2>/dev/null && env3/bin/python -m pytest --version 2>&1 | head -1
command -v garden cercis isort pyupgrade mypy ruff
python3 -c "import qtpy; print('qtpy', qtpy.API_NAME, qtpy.QT_VERSION)"
```

If the branch is `main`, create a feature branch before Task 1 and stay on it.

If **no** interpreter has `pytest`, try one of the two routes:

```bash
garden dev/virtualenv && garden dev
```

```bash
python3 -m venv --system-site-packages env3 && env3/bin/python -m ensurepip --upgrade && env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

If that fails too: **STOP and report.**

`garden`, `pyupgrade`, `mypy` and `ruff` may all be missing. That is expected and fine — CI runs
them. `cercis` and `isort` **must** be there; without them, stop and report.

### Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected, exactly:**

```
FAILED test/git_test.py::test_stdout - assert 69 == 0
FAILED test/git_test.py::test_stderr - assert 0 == 69
FAILED test/git_test.py::test_stdout_and_stderr - assert 0 == 69
FAILED test/git_test.py::test_it_doesnt_deadlock - assert 0 == 69
FAILED test/widgets_dag_history_test.py::test_graph_delegate_offscreen_nodes_selection_lanes_and_size
5 failed, 755 passed
```

**Note the numbers.** These five are the baseline (trap **F1**). From here on, "green" means
*these five and no others*. If your machine shows a different set, write it down and use **that**
as your baseline instead — but if any test outside `test/git_test.py` and
`test_graph_delegate_offscreen_nodes_selection_lanes_and_size` fails, **stop and report**.

The whole plan was executed on this repository at `dc150fc3`. The pass count after each task on
that machine, for orientation — your absolute numbers may differ, the **deltas** should not:

| After task | new tests | `passed` | `failed` |
|---|---|---|---|
| 0 (baseline) | — | 755 | 5 |
| 1 — ISO date | +4 | 759 | 5 |
| 2 — Hash column | +10 | 769 | 5 |
| 3 — Chip padding and row margin | +5 | 775 | **4** |
| 4 — Branch chooser | +5 | 780 | 4 |
| 5 — Tag chip color | +8 | 788 | 4 |
| 6 — Tag marker and bold | +3 | 791 | 4 |
| 7 — Documentation | 0 | 791 | 4 |

> **One more thing about the offscreen platform.** Over roughly a dozen full-suite runs while this
> plan was being written, one run died in a Qt teardown segfault inside `QWidget::event` with no
> failing test — and the identical command passed on the next try. Re-running the heaviest files
> five times in a row produced no repeat. If you hit it once, re-run; if it repeats at the same
> test, **stop and report**.

Task 3 gains six passes for five new tests: it also makes
`test_graph_delegate_offscreen_nodes_selection_lanes_and_size` font-independent, which turns the
fifth baseline failure into a pass. From Task 3 onward, "green" means the **four**
`test/git_test.py` failures and nothing else.

---

## Task 1 — Show the date as an ISO timestamp down to the minute

**Goal:** the history's Date, Time column reads `2026-08-01 12:11`.

### Step 1.1 (RED) — Write the tests

`test/dag_test.py` starts with `# ruff: noqa: I001`, so its import order is deliberate. Anchor:

```bash
grep -n "^from cola.models import dag$" test/dag_test.py
```

**Expected:** exactly one hit. Replace that single line with these two:

```python
from cola.models import dag
from cola.models import prefs
```

Anchor for the standard-library import:

```bash
grep -n "^import argparse$" test/dag_test.py
```

**Expected:** exactly one hit. Insert **directly below it**:

```python
import re
```

Append to the **end** of `test/dag_test.py`:

```python
_ISO_MINUTE = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}'


def test_the_default_log_date_is_iso_down_to_the_minute(app_context):
    """The Date, Time column asked for is '2026-08-01 12:11' and nothing finer."""
    assert prefs.Defaults.logdate == prefs.DateFormat.ISO_MINUTE
    assert prefs.logdate(app_context) == 'format:%Y-%m-%d %H:%M'


def test_the_default_log_date_can_be_chosen_in_the_preferences(app_context):
    """A default the combo box does not list would be unselectable."""
    assert prefs.DateFormat.ISO_MINUTE in prefs.date_formats()


def test_the_history_reads_dates_in_that_format(app_context):
    """End to end: git formats the date, nothing in the application parses one."""
    commit_files()
    app_context.model.update_status()
    reader = dag.RepoReader(app_context, dag.DAG('HEAD', 10))

    commits = list(reader.get())

    assert commits
    for commit in commits:
        assert re.fullmatch(_ISO_MINUTE, commit.authdate), commit.authdate


def test_the_pseudo_commit_date_uses_the_same_format(app_context):
    """STAGE and WORKTREE are formatted in Python and must not drift apart."""
    authdate = dag.get_date_for_current_time(app_context)

    assert re.fullmatch(_ISO_MINUTE, authdate), authdate
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/dag_test.py 2>&1 | tail -12
```

**Expected:** four failures. The first two report

```
AttributeError: type object 'DateFormat' has no attribute 'ISO_MINUTE'
```

and the last two report a date that does not match, e.g.
`AssertionError: assert None ... Sat Aug 1 12:11:20 2026 +0200`.

Confirm beforehand: `grep -c ISO_MINUTE cola/models/prefs.py` → `0`.

### Step 1.2 (GREEN) — Add the format and make it the default

**Anchor 1:**

```bash
grep -n "^    ISO_STRICT = 'iso8601-strict'$" cola/models/prefs.py
```

**Expected:** exactly one hit. Insert **directly below it**:

```python
    ISO_MINUTE = 'format:%Y-%m-%d %H:%M'
```

**Anchor 2:**

```bash
grep -n "^        DateFormat.DEFAULT,$" cola/models/prefs.py
```

**Expected:** exactly one hit, inside `date_formats()`. Insert **directly above it** (so the
default is the first entry of the combo box):

```python
        DateFormat.ISO_MINUTE,
```

**Anchor 3:**

```bash
grep -n "^    logdate = DateFormat.DEFAULT$" cola/models/prefs.py
```

**Expected:** exactly one hit, inside `class Defaults`. Replace that line with:

```python
    logdate = DateFormat.ISO_MINUTE
```

> **Nothing else changes.** `get_date_for_current_time()` already routes a `format:` value through
> `DateFormat.is_custom()`; `RepoReader` already passes `prefs.logdate(context)` to `--date=`. The
> argument list is built as a Python list and handed to `core.run_command`, so the space inside
> `format:%Y-%m-%d %H:%M` never reaches a shell.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/dag_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** `test/dag_test.py` fully green; the whole suite at baseline + 4 passed, with the same
five baseline failures and no others.

### Commit

```bash
git add -A && git commit -m "feat: show history dates as ISO timestamps down to the minute

The Date, Time column showed git's default format, 'Sat Aug 1 12:11:20
2026 +0200'. It now shows '2026-08-01 12:11'.

The change is the default of the existing fanta.logdate setting, so git
keeps doing the formatting and nothing in the application parses a date
back. A user who configured another format keeps it, and the new one is
offered in the Preferences combo box like every other."
```

---

## Task 2 — Add the Hash column

**Goal:** a fourth column at the right end of the history showing the abbreviated object ID.

### Step 2.1 (RED) — Write the tests

Add three imports to `test/widgets_dag_history_test.py`. Anchor:

```bash
grep -n "^from cola.widgets.dag import inline_graph_style$" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit. The `from cola.widgets.dag import …` block is sorted, so each of
these three lines goes in its alphabetical place:

| Line to add | Goes directly above |
|---|---|
| `from cola.widgets.dag import date_column_width` | `from cola.widgets.dag import inline_graph_style` |
| `from cola.widgets.dag import oid_column_width` | `from cola.widgets.dag import readable_chip_fill` |
| `from cola.widgets.dag import short_oid` | `from cola.widgets.main import MainView` |

If the ordering comes out wrong, `garden fmt` fixes it in the Verification step; ruff would
otherwise fail this file in CI (trap **F14**).

Append to the **end** of `test/widgets_dag_history_test.py`:

```python
@pytest.mark.parametrize(
    ('scenario', 'oid', 'expected'),
    (
        ('an object ID is abbreviated', 'a' * 40, 'aaaaaaaa'),
        ('an ID shorter than the limit is kept', 'abc', 'abc'),
        ('STAGE is not an object ID', dag.STAGE, ''),
        ('WORKTREE is not an object ID', dag.WORKTREE, ''),
        ('an empty ID', '', ''),
        ('no ID at all', None, ''),
    ),
)
def test_short_oid_abbreviates_only_real_object_ids(scenario, oid, expected):
    """The pseudo-commits must not look like very short hashes."""
    assert short_oid(oid, 8) == expected, scenario


def test_the_history_shows_the_abbreviated_hash_in_its_own_column(
    qapp, app_context, managed_qobject
):
    """The reported gap: the history never showed the commit hash."""
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'a' * 40)
    tree = _tree(app_context, managed_qobject)

    tree.add_commits([commit], _graph_result([commit]))

    item = tree.topLevelItem(0)
    assert tree.columnCount() == 4
    assert tree.headerItem().text(CommitTreeWidgetItem.OID) == 'Hash'
    assert item.text(CommitTreeWidgetItem.OID) == 'a' * tree.oid_length
    assert item.text(CommitTreeWidgetItem.SUMMARY) == commit.summary
    assert item.text(CommitTreeWidgetItem.AUTHOR) == commit.author
    assert item.text(CommitTreeWidgetItem.DATE) == commit.authdate


@pytest.mark.parametrize('oid', (dag.STAGE, dag.WORKTREE))
def test_the_hash_column_stays_empty_for_the_pseudo_commits(
    qapp, app_context, managed_qobject, oid
):
    """A row that is not a commit has no hash to show."""
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, oid)
    tree = _tree(app_context, managed_qobject)

    tree.add_commits([commit], _graph_result([commit]))

    assert tree.topLevelItem(0).text(CommitTreeWidgetItem.OID) == ''


def test_the_date_column_keeps_absorbing_the_slack(
    qapp, app_context, managed_qobject
):
    """The hash column must not become the one that grows with the window."""
    tree = _tree(app_context, managed_qobject)

    assert tree.header().stretchLastSection() is False
    assert tree.header().sectionResizeMode(CommitTreeWidgetItem.DATE) == (
        QtWidgets.QHeaderView.Stretch
    )
```

Now replace the two width assertions of the existing column test. Anchor:

```bash
grep -n "        tree.header().width() \* 0.70, abs=2" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit, inside
`test_default_column_ratio_prioritizes_summary_without_overwriting_saved_widths`. Replace this
block —

```python
    assert tree.columnWidth(CommitTreeWidgetItem.SUMMARY) == pytest.approx(
        tree.header().width() * 0.70, abs=2
    )
    assert tree.columnWidth(CommitTreeWidgetItem.AUTHOR) == pytest.approx(
        tree.header().width() * 0.15, abs=2
    )
```

— with this one:

```python
    assert tree.columnWidth(CommitTreeWidgetItem.OID) == oid_column_width(
        tree, tree.oid_length
    )
    assert tree.columnWidth(CommitTreeWidgetItem.DATE) >= date_column_width(tree)
    assert tree.columnWidth(CommitTreeWidgetItem.SUMMARY) > tree.columnWidth(
        CommitTreeWidgetItem.AUTHOR
    )
    assert sum(tree.columnWidth(column) for column in range(4)) == tree.header().width()
    assert tree.columnWidth(CommitTreeWidgetItem.AUTHOR) == pytest.approx(
        tree.header().width() * 0.15, abs=2
    )
```

> The summary is no longer a fixed fraction of the window: the two columns whose text has a known
> shape are measured, and the summary gets what is left. A ratio assertion could not survive that
> and would say less than "every column fits its content".

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -12
```

**Expected:** a collection error,

```
ImportError: cannot import name 'date_column_width' from 'cola.widgets.dag'
```

Confirm beforehand: `grep -c "def short_oid" cola/widgets/dag.py` → `0`.

### Step 2.2 (GREEN) — The pure helpers

**Anchor:**

```bash
grep -n "^class CommitTreeWidgetItem(QtWidgets.QTreeWidgetItem):$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Insert **directly above it**, keeping one blank line before the
class and two blank lines between the new definitions:

```python
COLUMN_PADDING = 24
"""Slack added to a measured column width so the text never touches the edge"""


def short_oid(oid, length):
    """Return the abbreviated object ID shown in the history's Hash column.

    STAGE and WORKTREE are pseudo-commits, not object IDs, so their rows stay
    blank instead of showing a truncated placeholder name.
    """
    if not oid or oid in (dag.STAGE, dag.WORKTREE):
        return ''
    return oid[:length]


def oid_column_width(widget, length):
    """Return a width that fits an abbreviated object ID plus padding."""
    metrics = widget.fontMetrics()
    return qtutils.fontmetrics_width(metrics, '0' * length) + COLUMN_PADDING


def date_column_width(widget):
    """Return a width that fits the date the history shows, plus padding.

    The sample is the ISO date git is asked for by default. A different
    fanta.logdate can be wider or narrower; this is the initial width of a
    column that stretches and that the user can drag, not a promise.
    """
    metrics = widget.fontMetrics()
    return qtutils.fontmetrics_width(metrics, '0000-00-00 00:00') + COLUMN_PADDING


```

### Step 2.3 (GREEN) — The fourth column on the item

**Anchor:**

```bash
grep -n "^    DATE = 2$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace the whole item class body — from `    SUMMARY = 0` down to
and including `        self.setText(self.DATE, commit.authdate)` — with:

```python
    SUMMARY = 0
    AUTHOR = 1
    DATE = 2
    OID = 3

    def __init__(self, commit, parent=None, oid_length=prefs.Defaults.abbrev):
        QtWidgets.QTreeWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(self.SUMMARY, commit.summary)
        self.setText(self.AUTHOR, commit.author)
        self.setText(self.DATE, commit.authdate)
        self.setText(self.OID, short_oid(commit.oid, oid_length))
```

> `oid_length` is **last** in the signature. `test/widgets_history_checkout_test.py` constructs
> `CommitTreeWidgetItem(_fake_commit(...))` positionally, and `parent` has to keep its place.

### Step 2.4 (GREEN) — The header, the stretch and the initial widths

**Anchor:**

```bash
grep -n "        self.setHeaderLabels(\[N_('Summary'), N_('Author'), N_('Date, Time')\])" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace the block that starts two lines above it — from
`        self.setSelectionMode(` down to and including the closing `        )` of
`setSectionResizeMode`, i.e.

```python
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setHeaderLabels([N_('Summary'), N_('Author'), N_('Date, Time')])
        self.header().setSectionResizeMode(
            CommitTreeWidgetItem.DATE, QtWidgets.QHeaderView.Stretch
        )
```

— with:

```python
        self.context = context
        self.oid_length = prefs.abbrev(context)

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setHeaderLabels([
            N_('Summary'),
            N_('Author'),
            N_('Date, Time'),
            N_('Hash'),
        ])
        # The Hash column is last and keeps a measured width, so the date column
        # has to be the one that absorbs the slack. Qt stretches the last section
        # by default, which would fight that.
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(
            CommitTreeWidgetItem.DATE, QtWidgets.QHeaderView.Stretch
        )
        self.setColumnWidth(
            CommitTreeWidgetItem.OID, oid_column_width(self, self.oid_length)
        )
```

`self.context` is now assigned at the top, so the **old** assignment three lines further down has
to go. Anchor:

```bash
grep -n "^        self.graph_delegate = GraphDelegate(self)$" cola/widgets/dag.py
```

**Expected:** exactly one hit. The line **directly below it** must read `        self.context = context`.
Delete that one line — the assignment moved to the top of the constructor. Verify with:

```bash
grep -n -A 1 "^        self.graph_delegate = GraphDelegate(self)$" cola/widgets/dag.py
```

**Expected:** the line after it is now `        self.oidmap = {}`. (Do **not** count
`self.context = context` across the file: six other classes in `cola/widgets/dag.py` have the same
line and none of them are being touched.)

### Step 2.5 (GREEN) — The initial column widths

**Anchor:**

```bash
grep -n "            summary_width = int(width \* 0.70)" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `showEvent`. Replace these two lines —

```python
            summary_width = int(width * 0.70)
            author_width = int(width * 0.15)
```

— with:

```python
            author_width = int(width * 0.15)
            # The date and hash columns hold text of a known shape, so they are
            # measured rather than given a share of the window. The summary
            # takes everything that is left; the floor keeps it from collapsing
            # in a narrow window.
            fixed_width = (
                author_width
                + date_column_width(self)
                + oid_column_width(self, self.oid_length)
            )
            summary_width = max(int(width * 0.35), width - fixed_width)
```

### Step 2.6 (GREEN) — Pass the length to every row

**Anchor:**

```bash
grep -n "            item = CommitTreeWidgetItem(commit)$" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `add_commits`. Replace that line with:

```python
            item = CommitTreeWidgetItem(commit, oid_length=self.oid_length)
```

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -5
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** baseline + 10 passed (759 → 769 on the reference machine), still exactly the five
baseline failures (Task 3 is what removes the fifth).

### Commit

```bash
git add -A && git commit -m "feat: show the commit hash in the history

The history listed summary, author and date and never the object ID. A
fourth column at the right end shows it, abbreviated to core.abbrev.

It is last because that is where the column is least in the way, and
because the summary has to stay column 0 - the graph delegate and three
item-data roles hang off that index. Qt stretches the last section by
default, so the date column has to be told to keep doing it. The state
schema is untouched: column_widths was already truncated to the first
two entries, so the new column needs no migration."
```

---

## Task 3 — Give the branch chips room to breathe, and the row room for them

**Goal:** two more pixels of padding on every side of a chip, so descenders stop touching the
border — and a row that is always taller than the chip it holds.

### Step 3.1 (RED) — Write the tests

Append to the **end** of `test/widgets_dag_history_test.py`:

```python
def test_the_chip_keeps_a_margin_around_its_text(qapp, app_context, managed_qobject):
    """The reported defect: a descender such as 'g' touched the chip border."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/g-branch']
    tree = _tree(app_context, managed_qobject)
    metrics = QtGui.QFontMetrics(tree.font())

    painter = _draw_row_labels(tree, commit, palette)

    chip = painter.rounded_rects[0]
    assert GraphDelegate.LABEL_V_PADDING >= 2
    assert GraphDelegate.LABEL_TEXT_OFFSET >= 4
    assert chip.height() == metrics.height() + 2 * GraphDelegate.LABEL_V_PADDING
    assert chip.width() == (
        metrics.horizontalAdvance('g-branch') + 2 * GraphDelegate.LABEL_TEXT_OFFSET
    )


@pytest.mark.parametrize('point_size', (9, 12, 18, 24))
def test_the_row_leaves_a_margin_around_the_chip_it_holds(
    point_size, qapp, app_context, managed_qobject
):
    """At 11 pt and up the chip used to be exactly as tall as its own row.

    paint() clips to option.rect, so a chip that fills the row loses its
    rounded corners and overflows the top by a pixel.
    """
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/g-branch']
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    option = QtWidgets.QStyleOptionViewItem()
    option.font = QtGui.QFont(tree.font())
    option.font.setPointSize(point_size)
    option.fontMetrics = QtGui.QFontMetrics(option.font)

    hint = tree.graph_delegate.sizeHint(
        option, tree.indexFromItem(tree.topLevelItem(0), 0)
    )

    chip_height = option.fontMetrics.height() + 2 * GraphDelegate.LABEL_V_PADDING
    assert GraphDelegate.ROW_V_MARGIN >= 2
    assert hint.height() >= chip_height + 2 * GraphDelegate.ROW_V_MARGIN
```

Two existing tests pin the old height formula to a number and have to move with it (trap **F17**).
Anchor:

```bash
grep -n "    assert hint.height() == 26" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit, inside
`test_graph_delegate_offscreen_nodes_selection_lanes_and_size`. Replace these two lines —

```python
    assert hint.height() == 26
    assert 24 <= hint.height() <= 28
```

— with:

```python
    # The row height follows the desktop font, so pinning it to a number only
    # holds on the machine that wrote the number down. What has to hold
    # everywhere is that a chip fits inside its row with a margin left over.
    chip_height = option.fontMetrics.height() + 2 * GraphDelegate.LABEL_V_PADDING
    assert hint.height() >= GraphDelegate.ROW_HEIGHT
    assert hint.height() >= chip_height + 2 * GraphDelegate.ROW_V_MARGIN
```

Anchor:

```bash
grep -n "    assert hint.height() == max(26, metrics.height() + 4)" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit, inside
`test_24pt_visible_chip_and_hit_area_have_identical_boundaries`. Replace that line with:

```python
    chip_height = metrics.height() + 2 * GraphDelegate.LABEL_V_PADDING
    assert hint.height() >= chip_height + 2 * GraphDelegate.ROW_V_MARGIN
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k "margin_around_its_text or margin_around_the_chip or offscreen_nodes or 24pt_visible_chip" 2>&1 | tail -10
```

**Expected:** all seven fail with

```
AttributeError: type object 'GraphDelegate' has no attribute 'LABEL_V_PADDING'
```

or, for the two rewritten ones,

```
AttributeError: type object 'GraphDelegate' has no attribute 'ROW_V_MARGIN'
```

### Step 3.2 (GREEN) — The three constants

**Anchor:**

```bash
grep -n "^    LABEL_TEXT_OFFSET = 2$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace that line with:

```python
    LABEL_TEXT_OFFSET = 4
    LABEL_V_PADDING = 2
    ROW_V_MARGIN = 2
```

### Step 3.3 (GREEN) — Use the vertical padding when drawing

**Anchor:**

```bash
grep -n "^        y_offset = 0$" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `_draw_labels`. Replace that line with:

```python
        y_offset = self.LABEL_V_PADDING
```

### Step 3.4 (GREEN) — Use it in the hit test as well

**Anchor:**

```bash
grep -n "^        x_offset = self.LABEL_TEXT_OFFSET$" cola/widgets/dag.py
```

**Expected:** **two** hits — one in `_draw_labels`, one in `_label_hit_test`. Tell them apart by
the line **below** each: the one in `_draw_labels` is already followed by
`        y_offset = self.LABEL_V_PADDING` (Step 3.3), the one in `_label_hit_test` is followed by
`        current_x = rect.left() + self._graph_width(row, prev_row) + 8`. Take the **second** one
and insert **directly below it**:

```python
        y_offset = self.LABEL_V_PADDING
```

Then, in the same method, anchor:

```bash
grep -n "            box_top = mid_y - text_height / 2$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace these two lines —

```python
            box_top = mid_y - text_height / 2
            box_bottom = mid_y + text_height / 2
```

— with:

```python
            box_top = mid_y - text_height / 2 - y_offset
            box_bottom = mid_y + text_height / 2 + y_offset
```

> Trap **F6**: two existing tests probe the drawn rectangle's top and bottom edges against the hit
> area. They pass only if both sides change together.

### Step 3.5 (GREEN) — Say where the reserved row height goes

**Anchor:**

```bash
grep -n "        height = max(self.ROW_HEIGHT, option.fontMetrics.height() + 4)" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `sizeHint`. Replace that line with:

```python
        # A chip is the text plus its vertical padding on both sides, and the
        # row keeps a margin above and below it. Without that margin a large
        # desktop font makes the chip exactly as tall as its row, and the
        # rounded corners are clipped away.
        chip_height = option.fontMetrics.height() + 2 * self.LABEL_V_PADDING
        height = max(self.ROW_HEIGHT, chip_height + 2 * self.ROW_V_MARGIN)
```

> The old expression was `max(ROW_HEIGHT, fontMetrics.height() + 4)`, and `4` happens to be
> exactly the padding the chip now takes — the row had **no** margin left. See the measured table
> in §2.3: at 8–9 pt this changes nothing at all, because the `ROW_HEIGHT` floor already won; from
> 10 pt upwards the row grows by 2–4 px so the chip stops being clipped.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -5
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** 769 → **775 passed and 4 failed** (769 + 5 new tests, plus
`test_graph_delegate_offscreen_nodes_selection_lanes_and_size` turning from the fifth baseline
failure into a pass). From here on the baseline is the four `test/git_test.py` failures.

`test_24pt_visible_chip_and_hit_area_have_identical_boundaries` and
`test_marked_chip_and_hit_area_have_identical_boundaries` must **pass** — they are the proof that
the hit area grew with the chip.

### Commit

```bash
git add -A && git commit -m "fix: keep the chip border away from the text and inside its row

The chip box was exactly as tall as the text it holds, so a descender in
a name like 'g-branch' ran into the bottom border. Every side gains two
pixels.

That alone would have made things worse: sizeHint reserved
fontMetrics.height() + 4, which is exactly the height of the padded chip.
Measured across eight font sizes, from about 11 pt the chip was as tall
as its own row, and paint() clips to option.rect - the rounded corners
were cut off and the chip overflowed the top by a pixel. ROW_V_MARGIN
guarantees two pixels above and below at any size, and changes nothing at
8 and 9 pt, where the ROW_HEIGHT floor already won.

Two tests pinned the old formula to a number. One of them was already
failing on any machine whose desktop font is larger than the one that
wrote the number down; both now assert the property that has to hold -
the row is at least as tall as the chip plus its margin."
```

---

## Task 4 — A dialog that offers only the branches on the double-clicked commit

**Goal:** double-clicking a commit that carries two local branch heads offers exactly those two.

> **Trap F2 — read this before touching anything.** The existing test
> `test_several_branches_at_one_commit_open_the_checkout_dialog` patches
> `guicmds.checkout_branch`. If the production code starts calling a real modal dialog while that
> test still patches the old function, `pytest` **hangs forever** with no output and no timeout.
> Step 4.1 rewrites the test **first**, deliberately.

### Step 4.1 (RED) — Rewrite the ambiguity test and add the new ones

`test/widgets_history_checkout_test.py`. Anchor:

```bash
grep -n "^from cola import guicmds$" test/widgets_history_checkout_test.py
```

**Expected:** exactly one hit. **Delete that line** — after this task nothing in the file uses it
(trap **F12**).

Anchor:

```bash
grep -n "    \"\"\"Mehrdeutig heisst: der vorhandene Auswahldialog entscheidet.\"\"\"" test/widgets_history_checkout_test.py
```

**Expected:** exactly one hit. Replace the whole function it belongs to — from
`def test_several_branches_at_one_commit_open_the_checkout_dialog(` down to and including its last
line `    assert confirmed == []` — with:

```python
def test_several_branches_at_one_commit_offer_exactly_those_branches(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Ambiguous means: ask, and offer only what is actually on that commit."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    _git('branch', 'alpha', 'topic')
    checkout_context.model.update_status()
    offered = []
    monkeypatch.setattr(
        dagwidget,
        'select_branch_at_commit',
        lambda branches, parent=None: offered.append(list(branches)) or 'alpha',
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(topic_oid, branches=['alpha', 'topic']))

    assert offered == [['alpha', 'topic']]
    assert _git('rev-parse', '--abbrev-ref', 'HEAD') == 'alpha'
    assert confirmed == []


def test_cancelling_the_branch_choice_checks_nothing_out(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """A cancelled dialog must leave HEAD exactly where it was."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    _git('branch', 'alpha', 'topic')
    checkout_context.model.update_status()
    head_before = _git('rev-parse', 'HEAD')
    monkeypatch.setattr(
        dagwidget, 'select_branch_at_commit', lambda branches, parent=None: ''
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(topic_oid, branches=['alpha', 'topic']))

    assert _git('rev-parse', 'HEAD') == head_before
    assert _git('rev-parse', '--abbrev-ref', 'HEAD') == 'main'
    assert confirmed == []
```

Append to the **end** of `test/widgets_history_checkout_test.py`:

```python
def _branch_dialog(managed_qobject, branches):
    """Build the dialog without ever entering its event loop (trap F2)."""
    return managed_qobject(dagwidget.SelectBranchDialog(branches))


def test_the_branch_dialog_lists_exactly_the_branches_it_was_given(
    qapp, managed_qobject
):
    """No completer, no other refs: the row already said which branches count."""
    dialog = _branch_dialog(managed_qobject, ['alpha', 'topic'])

    shown = [
        dialog.branch_list.item(row).text() for row in range(dialog.branch_list.count())
    ]

    assert shown == ['alpha', 'topic']
    assert dialog.value() == 'alpha'
    assert dialog.checkout_button.isEnabled()


def test_the_branch_dialog_returns_the_selected_branch(qapp, managed_qobject):
    dialog = _branch_dialog(managed_qobject, ['alpha', 'topic'])

    dialog.branch_list.setCurrentRow(1)

    assert dialog.value() == 'topic'


def test_the_branch_dialog_cannot_be_accepted_without_a_selection(
    qapp, managed_qobject
):
    dialog = _branch_dialog(managed_qobject, ['alpha', 'topic'])

    dialog.branch_list.clearSelection()

    assert dialog.value() == ''
    assert not dialog.checkout_button.isEnabled()


def test_an_empty_branch_list_opens_no_dialog_at_all(qapp, monkeypatch):
    """A window with nothing to offer must never appear."""
    built = []

    def fail(*args, **kwargs):
        built.append(args)
        raise AssertionError('the dialog must not be constructed')

    monkeypatch.setattr(dagwidget, 'SelectBranchDialog', fail)

    assert dagwidget.select_branch_at_commit([]) == ''
    assert built == []
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen timeout 300 python3 -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py 2>&1 | tail -12
```

**Expected:** six failures reporting

```
AttributeError: <module 'cola.widgets.dag' ...> does not have the attribute 'select_branch_at_commit'
```

and

```
AttributeError: module 'cola.widgets.dag' has no attribute 'SelectBranchDialog'
```

The run must **finish**. If it hangs, the old test was not replaced — go back to the top of this
step.

### Step 4.2 (GREEN) — The dialog

**Anchor:**

```bash
grep -n "^class ViewerMixin:$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Insert **directly above it** (two blank lines before
`class ViewerMixin:` afterwards):

```python
class SelectBranchDialog(standard.Dialog):
    """Choose one of the branch heads that sit on a single commit.

    The Checkout Branch dialog offers every branch in the repository, which is
    the wrong question after a double-click on one row: the row already says
    which branches are meant. This one lists exactly those and nothing else.
    """

    def __init__(self, branches, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.setWindowTitle(N_('Checkout Branch'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
        self._branches = list(branches)

        self.label = QtWidgets.QLabel(
            N_('Several branches point at this commit. Choose the one to check out.')
        )
        self.label.setWordWrap(True)

        self.branch_list = QtWidgets.QListWidget()
        self.branch_list.setAlternatingRowColors(True)
        self.branch_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        qtutils.set_items(self.branch_list, self._branches)
        if self._branches:
            self.branch_list.setCurrentRow(0)

        self.close_button = qtutils.close_button()
        self.checkout_button = qtutils.ok_button(
            N_('Checkout'), icon=icons.branch(), enabled=bool(self._branches)
        )

        button_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            qtutils.STRETCH,
            self.close_button,
            self.checkout_button,
        )
        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.label,
            self.branch_list,
            button_layout,
        )
        self.setLayout(self.main_layout)

        self.branch_list.itemSelectionChanged.connect(self._selection_changed)
        self.branch_list.itemDoubleClicked.connect(self._item_double_clicked)
        qtutils.connect_button(self.checkout_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        # No settings: this dialog has no geometry worth remembering, and the
        # test context's settings object is a Mock that init_state would choke
        # on. selectcommits.SelectCommits does the same.
        self.init_state(None, self.resize_widget, parent)

    def resize_widget(self, parent):
        """Set the initial size of the widget"""
        width, height = qtutils.default_size(parent, 420, 280)
        self.resize(width, height)

    def value(self):
        """Return the selected branch name, or an empty string"""
        return qtutils.selected_item(self.branch_list, self._branches) or ''

    def _selection_changed(self):
        self.checkout_button.setEnabled(bool(self.value()))

    def _item_double_clicked(self, _item):
        if self.value():
            self.accept()


def select_branch_at_commit(branches, parent=None):
    """Ask which of the branch heads on one commit to check out.

    Returns the chosen branch name, or an empty string when the dialog was
    cancelled or there was nothing to choose from.
    """
    branches = list(branches)
    if not branches:
        return ''
    dialog = SelectBranchDialog(branches, parent=parent)
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return ''
    return dialog.value()


```

### Step 4.3 (GREEN) — Route the ambiguous double-click to it

**Anchor:**

```bash
grep -n "            guicmds.checkout_branch(context, default=branches\[0\])" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `checkout_commit`. Replace that single line with:

```python
            branch = select_branch_at_commit(branches, parent=qtutils.active_window())
            if branch:
                cmds.do(cmds.CheckoutBranch, context, branch)
```

> Keep the `return` on the line below. **Do not remove the `guicmds` import** from
> `cola/widgets/dag.py`: `ViewerMixin.checkout_branch()`, the context-menu action, still uses it.
> Confirm with `grep -c guicmds cola/widgets/dag.py` → `2`.

Now update the docstring of `checkout_commit` so it stops describing the old dialog. Anchor:

```bash
grep -n "        branches at the same commit are ambiguous and go through the existing" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace these two lines —

```python
        branches at the same commit are ambiguous and go through the existing
        Checkout Branch dialog. Anything else would detach HEAD, which is a state
```

— with:

```python
        branches at the same commit are ambiguous, so they are offered for
        selection - only those, never every branch in the repository. Anything
        else would detach HEAD, which is a state
```

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen timeout 300 python3 -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py 2>&1 | tail -5
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** baseline + 5 passed (775 → 780 on the reference machine — five tests are new, the
sixth replaced an existing one), still exactly the four baseline failures, and the run finishes in
about a minute. If any run hangs: **stop and report** — a modal dialog is being entered.

### Commit

```bash
git add -A && git commit -m "feat: offer only the branches that are on the double-clicked commit

Double-clicking a commit with two branch heads opened the generic
Checkout Branch dialog, whose completer lists every local branch, every
potential branch, every remote branch and every tag. The row had already
said which branches are meant.

SelectBranchDialog is a small modal list of exactly those branches. Four
existing dialogs were checked first: GitCheckoutBranchDialog binds its
completion model at class-creation time and has nowhere to take a list,
SelectRemoteBranch is wired to the remote branches, SelectCommits carries
a diff view and returns commit IDs, and Switcher has no accepted result.

The remote-only and multi-remote paths are unchanged: mixing them in
would make one button mean 'switch branch' on some rows and 'create a
tracking branch' on others."
```

---

## Task 5 — Give tags a chip color of their own

**Goal:** a tag no longer shares the `HEAD` chip color.

### Step 5.1 (RED) — Write the tests

Append to the **end** of `test/widgets_dag_history_test.py`:

```python
def _chip_fills(style):
    return (style.chip_other, style.chip_remote, style.chip_tag, style.chip_head)


@pytest.mark.parametrize(
    'palette',
    [
        _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff'),
        _palette('#202328', '#e8eaed', '#17191d', '#292d33', '#6ea8fe', '#101216'),
    ],
    ids=('light', 'dark'),
)
def test_a_tag_does_not_share_a_chip_color_with_anything(qapp, palette):
    """A tag used to be painted exactly like the detached HEAD chip."""
    style = inline_graph_style(palette)

    fills = _chip_fills(style)

    assert len({fill.rgba() for fill in fills}) == 4
    assert style.chip_tag.getHsvF()[0] != style.chip_head.getHsvF()[0]


@pytest.mark.parametrize('palette', _adversarial_chip_palettes())
def test_four_chip_colors_stay_distinct_and_readable_on_any_row(qapp, palette):
    """Adding a fourth color must not collapse the set on a hostile palette."""
    style = inline_graph_style(palette)
    fills = _chip_fills(style)

    for background in (
        _opaque_color(palette.highlight().color()),
        _opaque_color(palette.base().color()),
    ):
        adapted = readable_chip_fills(fills, background)
        assert len({color.rgba() for color in adapted}) == 4
        for color in adapted:
            assert _color_contrast(color, background) >= 2.5


def test_each_ref_kind_gets_its_own_chip_color(qapp, app_context, managed_qobject):
    """other -> fallback, HEAD -> its own, tags/ -> the tag color, heads/ -> branch."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    style = inline_graph_style(palette)
    tree = _tree(app_context, managed_qobject)
    painter = _TextRecordingPainter()

    tree.graph_delegate._draw_labels(
        painter,
        13,
        ['other', 'HEAD', 'tags/v1', 'heads/main'],
        GraphDelegate.LANE_WIDTH + 8,
        QtGui.QFontMetrics(tree.font()),
        None,
        style,
    )

    backgrounds = [background for _pen, background in painter.rounded_styles]
    assert backgrounds == [
        style.chip_remote,
        style.chip_other,
        style.chip_tag,
        style.chip_head,
    ]
```

> The expected order is **not** the order of the input list: `_prepare_labels()` emits the
> ungrouped refs first (`HEAD` is re-inserted at the front by `_row_labels()` because no chip on
> this row is the current branch, then `other`, then `tags/v1`) and the grouped branches last.

Now fix the one existing test that compares the chip backgrounds against an exact list (trap
**F7**). Anchor:

```bash
grep -n "        (style.chip_other, style.chip_remote, style.chip_head)," test/widgets_dag_history_test.py
```

**Expected:** exactly one hit, inside
`test_selected_inline_summary_and_each_chip_have_contrasting_text`. Replace this block —

```python
    expected_chips = readable_chip_fills(
        (style.chip_other, style.chip_remote, style.chip_head),
        expected_background,
    )
    assert [background for _pen, background in painter.rounded_styles] == list(
        expected_chips
    )
```

— with:

```python
    expected_chips = readable_chip_fills(
        (style.chip_other, style.chip_remote, style.chip_tag, style.chip_head),
        expected_background,
    )
    # 'other' is the fallback chip, 'tags/v1' the tag chip, 'heads/main' the
    # local branch chip. chip_remote paints HEAD, which this row does not carry.
    assert [background for _pen, background in painter.rounded_styles] == [
        expected_chips[0],
        expected_chips[2],
        expected_chips[3],
    ]
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -10
```

**Expected:** the new tests and the two parameterisations of
`test_selected_inline_summary_and_each_chip_have_contrasting_text` fail with

```
AttributeError: 'InlineGraphStyle' object has no attribute 'chip_tag'
```

### Step 5.2 (GREEN) — The field

**Anchor:**

```bash
grep -n "^    chip_head: QtGui.QColor$" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `class InlineGraphStyle`. Insert **directly above it**:

```python
    chip_tag: QtGui.QColor
```

### Step 5.3 (GREEN) — A fourth fallback hue, and the tag color

**Anchor:**

```bash
grep -n "        for shift in (0.0, 0.34, 0.67)" cola/widgets/dag.py
```

**Expected:** exactly one hit, at the end of `_distinct_chip_backgrounds`. Replace that line with:

```python
        for shift in (0.0, 0.25, 0.5, 0.75)
```

> That function returns a fallback set only when the palette collapsed the semantic colors onto
> each other; it has to produce as many colors as it was handed, which is now four.

**Anchor:**

```bash
grep -n "^def inline_graph_style(palette):$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Insert **directly above it** (two blank lines before
`def inline_graph_style`, two after the previous definition):

```python
def _tag_chip_color(highlight, base):
    """Return the chip color tags are painted with.

    Every other chip is mixed from the palette highlight, so a tag drawn in one
    of them disappears among the branches. Rotating the highlight's hue half a
    turn keeps the color palette-derived and puts the tag on the opposite side
    of the wheel; the saturation and value floors keep a greyscale palette from
    producing a fourth grey.
    """
    hue, saturation, value, _alpha = _opaque_color(highlight).getHsvF()
    if hue < 0.0:
        hue = 0.0
    rotated = QtGui.QColor.fromHsvF(
        (hue + 0.5) % 1.0, max(0.55, saturation), max(0.45, value), 1.0
    )
    return _mix_color(rotated, _opaque_color(base), 0.18)


```

### Step 5.4 (GREEN) — Build it, and hand it out

**Anchor:**

```bash
grep -n "^    chip_other, chip_remote, chip_head = _distinct_chip_backgrounds($" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace the whole call — from that line down to and including
`    )` — with:

```python
    chip_other, chip_remote, chip_tag, chip_head = _distinct_chip_backgrounds(
        (
            _mix_color(base, alternate, 0.72),
            _mix_color(alternate, highlight, 0.38),
            _tag_chip_color(highlight, base),
            _mix_color(highlight, base, 0.24),
        ),
        (base, alternate, highlight, text, highlighted_text),
    )
```

**Anchor:**

```bash
grep -n "        chip_text_candidates, (chip_other, chip_remote, chip_head)" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace that line with:

```python
        chip_text_candidates, (chip_other, chip_remote, chip_tag, chip_head)
```

**Anchor:**

```bash
grep -n "^        chip_head=chip_head,$" cola/widgets/dag.py
```

**Expected:** exactly one hit, in the `InlineGraphStyle(...)` construction. Insert **directly
above it**:

```python
        chip_tag=chip_tag,
```

### Step 5.5 (GREEN) — Paint tags with it

**Anchor:**

```bash
grep -n "            chip_fills = (style.chip_other, style.chip_remote, style.chip_head)" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `_draw_labels`. Replace that line with:

```python
            chip_fills = (
                style.chip_other,
                style.chip_remote,
                style.chip_tag,
                style.chip_head,
            )
```

**Anchor:**

```bash
grep -n "                if tag == _HEAD_REF or tag.startswith(_TAGS_PREFIX):" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace these four lines —

```python
                if tag == _HEAD_REF or tag.startswith(_TAGS_PREFIX):
                    brush = chip_fills[1]
                elif tag.startswith(_HEADS_PREFIX):
                    brush = chip_fills[2]
```

— with:

```python
                if tag.startswith(_TAGS_PREFIX):
                    brush = chip_fills[2]
                elif tag == _HEAD_REF:
                    brush = chip_fills[1]
                elif tag.startswith(_HEADS_PREFIX):
                    brush = chip_fills[3]
```

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -5
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** baseline + 8 passed (780 → 788 on the reference machine), still exactly the four
baseline failures.

### Commit

```bash
git add -A && git commit -m "feat: paint tags in a chip color of their own

A tag was drawn in the same chip color as the detached HEAD marker, and
all three chip colors are mixed from the palette highlight - on the light
palette they measured as three shades of one blue. A tag disappeared
among the branches.

The fourth color is the palette highlight with its hue rotated half a
turn, with a saturation and a value floor so a greyscale theme still
produces a colored tag instead of a fourth grey. Measured over thirteen
palettes, including the adversarial ones: four distinct fills on both the
plain and the selected row, worst contrast 2.50 against the row.

chip_remote now paints only the HEAD chip. Its name was already wrong -
remote branches land in chip_other - and renaming it is a separate
change."
```

---

## Task 6 — Make a tag unmistakable: bold label and a tag glyph

**Goal:** a tag chip carries `⚑` and its label is drawn bold, at the correct width.

### Step 6.1 (RED) — Record the font, then assert on it

`_TextRecordingPainter` swallows `setFont`. Anchor:

```bash
grep -n "^        self.ellipses = \[\]$" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit, in `_TextRecordingPainter.__init__`. Insert **directly below it**:

```python
        self.font = None
        self.text_fonts = []
```

Anchor:

```bash
grep -n "^    def setFont(self, \*_args):$" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit. Replace these two lines —

```python
    def setFont(self, *_args):
        pass
```

— with:

```python
    def setFont(self, font):
        self.font = QtGui.QFont(font)
```

Anchor:

```bash
grep -n "^        self.text_colors.append((str(args\[-1\]), self.pen.color()))$" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit, in `drawText`. Insert **directly below it**:

```python
        self.text_fonts.append(QtGui.QFont(self.font) if self.font else None)
```

Append to the **end** of `test/widgets_dag_history_test.py`:

```python
def test_a_tag_chip_is_marked_and_drawn_bold(qapp, app_context, managed_qobject):
    """Color alone degrades on a greyscale theme; the glyph and weight do not."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    style = inline_graph_style(palette)
    tree = _tree(app_context, managed_qobject)
    font = QtGui.QFont(tree.font())
    painter = _TextRecordingPainter()

    tree.graph_delegate._draw_labels(
        painter,
        13,
        ['tags/v1.0', 'heads/main'],
        GraphDelegate.LANE_WIDTH + 8,
        QtGui.QFontMetrics(font),
        None,
        style,
        None,
        None,
        font,
    )

    assert GraphDelegate.TAG_MARKER == chr(0x2691) + ' '
    assert [text for text, _color in painter.text_colors] == [
        GraphDelegate.TAG_MARKER + 'v1.0',
        'main',
    ]
    assert [label_font.bold() for label_font in painter.text_fonts] == [True, False]


def test_a_branch_named_like_a_tag_is_not_marked(qapp, app_context, managed_qobject):
    """The marker follows the ref prefix, never the name."""
    palette = _palette('#f4f5f7', '#202124', '#ffffff', '#edf0f4', '#3268b2', '#ffffff')
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['heads/v1.0']
    tree = _tree(app_context, managed_qobject)

    painter = _draw_row_labels(tree, commit, palette)

    assert [text for text, _color in painter.text_colors] == ['v1.0']


def test_the_bold_tag_chip_and_its_hit_area_have_identical_boundaries(
    qapp, app_context, managed_qobject
):
    """The bold advance has to reach the chip width and the hit test alike."""
    factory = dag.CommitFactory()
    commit = _commit(app_context, factory, 'commit')
    commit.tags = ['tags/v1.0.0']
    tree = _tree(app_context, managed_qobject)
    tree.add_commits([commit], _graph_result([commit]))
    item = tree.topLevelItem(0)
    index = tree.indexFromItem(item, 0)
    font = QtGui.QFont(tree.font())
    font.setPointSize(18)
    metrics = QtGui.QFontMetrics(font)
    bold_font = QtGui.QFont(font)
    bold_font.setBold(True)
    option = QtWidgets.QStyleOptionViewItem()
    option.font = font
    option.fontMetrics = metrics
    hint = tree.graph_delegate.sizeHint(option, index)
    rect = QtCore.QRectF(0, 0, hint.width(), hint.height())
    painter = _TextRecordingPainter()

    tree.graph_delegate._draw_labels(
        painter,
        rect.center().y(),
        commit.tags,
        GraphDelegate.LANE_WIDTH + 8,
        metrics,
        item,
        inline_graph_style(tree.palette()),
        None,
        None,
        font,
    )

    chip = painter.rounded_rects[0]
    marked = GraphDelegate.TAG_MARKER + 'v1.0.0'
    assert QtGui.QFontMetrics(bold_font).horizontalAdvance(marked) > (
        metrics.horizontalAdvance(marked)
    )
    assert chip.width() == (
        QtGui.QFontMetrics(bold_font).horizontalAdvance(marked)
        + 2 * GraphDelegate.LABEL_TEXT_OFFSET
    )
    for x in (chip.left() + 1, chip.right() - 1):
        assert (
            tree.graph_delegate._label_hit_test(
                QtCore.QPointF(x, rect.center().y()), rect, metrics, index, item, font
            )[0]
            == 0
        )
    assert (
        tree.graph_delegate._label_hit_test(
            QtCore.QPointF(chip.right() + 2, rect.center().y()),
            rect,
            metrics,
            index,
            item,
            font,
        )[0]
        == -1
    )
```

Finally, the existing selected-row test asserts the drawn label texts by value and must learn
about the marker (trap **F7**). Anchor:

```bash
grep -n "    assert set(text_colors) >= {'other', 'v1', 'main', 'commit commit'}" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit. Replace that line with:

```python
    tag_text = GraphDelegate.TAG_MARKER + 'v1'
    assert set(text_colors) >= {'other', tag_text, 'main', 'commit commit'}
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -10
```

**Expected:** four failures on top of the baseline one — the two parameterisations of
`test_selected_inline_summary_and_each_chip_have_contrasting_text` and
`test_a_tag_chip_is_marked_and_drawn_bold` report

```
AttributeError: type object 'GraphDelegate' has no attribute 'TAG_MARKER'
```

and `test_the_bold_tag_chip_and_its_hit_area_have_identical_boundaries` reports

```
TypeError: GraphDelegate._draw_labels() takes from 7 to 10 positional arguments but 11 were given
```

`test_a_branch_named_like_a_tag_is_not_marked` **passes already** — it is a guard against marking
the wrong ref, and it must stay green in both directions.

### Step 6.2 (GREEN) — The marker constant

**Anchor:**

```bash
grep -n "^    CURRENT_BRANCH_BORDER = 2$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Insert **directly below it**:

```python
    # Modern clients give tags their own color and a tag glyph. The flag is the
    # widest-supported BMP glyph that reads as a marker; astral-plane emoji are
    # missing from too many desktop fonts.
    TAG_MARKER = chr(0x2691) + ' '
```

### Step 6.3 (GREEN) — Put the marker in the label text

**Anchor:**

```bash
grep -n "            if self._is_current_branch_ref(ref):" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `_row_labels`. Replace these six lines —

```python
            if self._is_current_branch_ref(ref):
                marked = True
                marker = self.CURRENT_BRANCH_MARKER
                display_text = marker + display_text
                if condensed_text is not None:
                    condensed_text = marker + condensed_text
```

— with:

```python
            marker = ''
            if ref.startswith(_TAGS_PREFIX):
                marker = self.TAG_MARKER
            elif self._is_current_branch_ref(ref):
                marked = True
                marker = self.CURRENT_BRANCH_MARKER
            if marker:
                display_text = marker + display_text
                if condensed_text is not None:
                    condensed_text = marker + condensed_text
```

> The `elif` is load-bearing (trap **F9**): `marked` decides whether a separate `HEAD` chip is
> inserted, and a tag ref can never be the current-branch ref. Putting the tag test in the same
> chain keeps `marked` untouched by tags.

### Step 6.4 (GREEN) — Carry the font next to the metrics

**Anchor:**

```bash
grep -n "^    def _get_spacing(self, condensed_text: str | None) -> int:$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Insert **directly above it**:

```python
    @staticmethod
    def _tag_fonts(font):
        """Return the bold (font, metrics) tags are drawn with, or (None, None).

        QFontMetrics cannot hand back the font it was built from, so the font
        has to travel next to it. A caller without one gets the row font for
        every chip, which keeps painting and hit testing consistent with each
        other even though the tags are then not bold.
        """
        if font is None:
            return None, None
        bold_font = QtGui.QFont(font)
        bold_font.setBold(True)
        return bold_font, QtGui.QFontMetrics(bold_font)

```

### Step 6.5 (GREEN) — Draw the tag label bold

**Anchor:**

```bash
grep -n "^        row_background: QtGui.QColor | None = None,$" cola/widgets/dag.py
```

**Expected:** exactly one hit, in the signature of `_draw_labels`. Insert **directly below it**:

```python
        font: QtGui.QFont | None = None,
```

> New parameters go **last** (trap **F8**): one existing test passes nine positional arguments.

**Anchor:**

```bash
grep -n "^        for i, (tag, display_text, condensed_text) in enumerate(self._row_labels(tags)):$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Insert **directly above it**:

```python
        bold_font, bold_metrics = self._tag_fonts(font)

```

and **directly below it**:

```python
            is_tag = tag.startswith(_TAGS_PREFIX)
            label_metrics = bold_metrics if is_tag and bold_metrics else font_metrics
```

Now replace the three prefix tests inside that loop so they reuse `is_tag`. Anchor:

```bash
grep -n "                if tag.startswith(_TAGS_PREFIX):" cola/widgets/dag.py
```

**Expected:** exactly one hit (Task 5 produced it). Replace that single line with:

```python
                if is_tag:
```

Select the painter's font. Anchor:

```bash
grep -n "^                painter.setBrush(brush)$" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `_draw_labels`. Insert **directly below it**:

```python
                if bold_font is not None:
                    painter.setFont(bold_font if is_tag else font)
```

Measure with the right metrics. Anchor:

```bash
grep -n "                condensed_text, display_text, font_metrics, item, i" cola/widgets/dag.py
```

**Expected:** **two** hits — one in `_draw_labels`, one in `_label_hit_test`. Replace the
**first** one (the one inside `_draw_labels`, above the line `            text_height =`) with:

```python
                condensed_text, display_text, label_metrics, item, i
```

### Step 6.6 (GREEN) — The width calculation and the hit test

**Anchor:**

```bash
grep -n "^    def _labels_width(self, font_metrics: QtGui.QFontMetrics, tags: list\[str\]):$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace that line **and the two below it** —

```python
    def _labels_width(self, font_metrics: QtGui.QFontMetrics, tags: list[str]):
        """Calculate total width needed for all labels."""
        return self._draw_labels(None, 0, tags, 0, font_metrics, None)
```

— with:

```python
    def _labels_width(
        self,
        font_metrics: QtGui.QFontMetrics,
        tags: list[str],
        font: QtGui.QFont | None = None,
    ):
        """Calculate total width needed for all labels."""
        return self._draw_labels(None, 0, tags, 0, font_metrics, None, font=font)
```

**Anchor:**

```bash
grep -n "            labels_width = self._labels_width(option.fontMetrics, commit.tags)" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `sizeHint`. Replace that line with:

```python
            labels_width = self._labels_width(
                option.fontMetrics, commit.tags, option.font
            )
```

**Anchor:**

```bash
grep -n "^    ) -> tuple\[int, bool\]:$" cola/widgets/dag.py
```

**Expected:** exactly one hit — the closing line of `_label_hit_test`'s signature. Insert
**directly above it**:

```python
        font: QtGui.QFont | None = None,
```

**Anchor:**

```bash
grep -n "^    ) -> None:$" cola/widgets/dag.py
```

**Expected:** exactly one hit — the closing line of `update_label_hover`'s signature. Insert
**directly above it**:

```python
        font: QtGui.QFont | None = None,
```

After both edits, verify:

```bash
grep -c "^        font: QtGui.QFont | None = None,$" cola/widgets/dag.py
```

**Expected:** `4` — `_draw_labels` from Step 6.5, `_labels_width` from the start of this step,
plus these two.

**Anchor:**

```bash
grep -n "^        for i, (_, display_text, condensed_text) in enumerate($" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `_label_hit_test`. Replace that line with:

```python
        _bold_font, bold_metrics = self._tag_fonts(font)
        for i, (ref, display_text, condensed_text) in enumerate(
```

and insert **directly below** the `        ):` line that closes that `enumerate(` call:

```python
            is_tag = ref.startswith(_TAGS_PREFIX)
            label_metrics = bold_metrics if is_tag and bold_metrics else font_metrics
```

**Anchor:**

```bash
grep -n "                condensed_text, display_text, font_metrics, item, i" cola/widgets/dag.py
```

**Expected:** now exactly **one** hit, inside `_label_hit_test`. Replace it with:

```python
                condensed_text, display_text, label_metrics, item, i
```

**Anchor:**

```bash
grep -n "            pos, rect, font_metrics, index, item$" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `update_label_hover`. Replace that line with:

```python
            pos, rect, font_metrics, index, item, font
```

### Step 6.7 (GREEN) — Hand the font in from the two call sites

**Anchor:**

```bash
grep -n "                else option.palette.base().color(),$" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `paint`. Insert **directly below it**:

```python
                option.font,
```

**Anchor:**

```bash
grep -n "            pos, rect, self.fontMetrics(), index, item$" cola/widgets/dag.py
```

**Expected:** exactly one hit, inside `CommitTreeWidget.mouseMoveEvent`. Replace that line with:

```python
            pos, rect, self.fontMetrics(), index, item, self.font()
```

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -5
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** baseline + 3 passed (788 → 791 on the reference machine), still exactly the four
baseline failures. In particular
`test_24pt_visible_chip_and_hit_area_have_identical_boundaries`,
`test_marked_chip_and_hit_area_have_identical_boundaries`, `test_head_chip_widens_the_size_hint`
and `test_detached_head_on_a_branch_tip_shows_head_before_the_branch` must all still pass.

### Commit

```bash
git add -A && git commit -m "feat: mark tags with a glyph and bold text in the graph

Color alone is not enough: on a greyscale or collapsed palette the four
chip fills are forced apart by lightness, and hue stops carrying meaning.
A tag chip therefore also carries a flag glyph and a bold label - the
combination GitKraken, Fork and Sourcetree all use in some form.

The glyph rides in display_text, the way the current-branch star already
does, so every width, chip and hit-area calculation picks it up. The bold
weight cannot: QFontMetrics does not expose the font it was built from,
so the QFont travels next to the metrics into _draw_labels, _labels_width
and _label_hit_test. The chip height keeps using the plain metrics,
because a bold font changes the advance and not the line height."
```

---

## Task 7 — Write down what was decided

> **Documentation only.** No production code, no tests.

### Step 7.1 — `docs/plans/README.md`

That file is still German. Per the repository's language rule it gets corrected when touched, so
replace its **entire** contents with:

````markdown
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
| [2026-08-01-history-ui-improvements.md](2026-08-01-history-ui-improvements.md) | completed | *fill in the branch* → *fill in the last commit* |

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
````

Replace the two placeholders in the last table row with the real branch name
(`git rev-parse --abbrev-ref HEAD`) and the short hash of the Task 6 commit (`git rev-parse --short HEAD`).

### Step 7.2 — The frontmatter of this plan

Replace the frontmatter of `docs/plans/2026-08-01-history-ui-improvements.md` — currently the three
lines `---`, `status: open`, `---` — with:

```yaml
---
status: completed
completed_at: 2026-08-01
plan_commit: <short hash of the commit that added this plan>
implementation_branch: <branch>
implementation_head: <short hash of the Task 6 commit>
ci_run: not run (green locally)
manual_verification: |
  - <what you actually looked at, or "not possible in a headless environment">
---
```

`plan_commit` is found with `git log --oneline --diff-filter=A -- docs/plans/2026-08-01-history-ui-improvements.md`.

### Step 7.3 — `.claude/skills/project-brief/references/fork-history.md`

Anchor:

```bash
grep -n "^## Where the fork's tests live$" .claude/skills/project-brief/references/fork-history.md
```

**Expected:** exactly one hit. Insert **directly above it**:

```markdown
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

```

### Step 7.4 — `.claude/skills/project-brief/references/gotchas.md`

Anchor:

```bash
grep -n "^\*\*The inline graph's chip color names are misleading.\*\*" .claude/skills/project-brief/references/gotchas.md
```

**Expected:** exactly one hit. Replace these **three** lines, verbatim —

```markdown
**The inline graph's chip color names are misleading.** `chip_head` paints **local** branches
(`heads/…`), `chip_other` is the fallback that **remote** branches land in, and `chip_remote`
paints `HEAD` and tags. See `cola/widgets/dag.py` where the brush is chosen.
```

— with:

```markdown
**The inline graph's chip color names are misleading.** `chip_head` paints **local** branches
(`heads/…`), `chip_other` is the fallback that **remote** branches land in, `chip_tag` paints
tags, and `chip_remote` paints nothing but the `HEAD` chip. See `cola/widgets/dag.py` where the
brush is chosen. There are **four** chip colors; `_distinct_chip_backgrounds()` and
`readable_chip_fills()` both have to keep producing four distinct ones.
```

Then append to the end of the **Qt widget behavior** section — anchor:

```bash
grep -n "^\*\*A \`QSyntaxHighlighter\`'s formats are invisible to \`QTextCursor.charFormat()\`.\*\*" .claude/skills/project-brief/references/gotchas.md
```

**Expected:** exactly one hit. Insert **directly above it**:

```markdown
**`QFontMetrics` has no `font()` accessor.** Measured under PyQt5: `hasattr(metrics, 'font')` is
`False`. Anything that needs a *variant* of the font a metrics object describes must be handed the
`QFont` as well. A bold font changes the advance and **not** the line height, so mixed-weight
labels in one row still line up.

**`QHeaderView` stretches the last section by default.** `header().stretchLastSection()` is `True`
on a fresh `QTreeWidget`. Giving a middle section `QHeaderView.Stretch` does not switch that off,
and the two then fight over the slack.

**A modal dialog reached from a test hangs pytest forever** — no error, no timeout, just a run
that never finishes. Anything in the production path that can call `exec_()` must be patched out
in every test that can reach it.

```

### Step 7.5 — `.claude/skills/project-brief/SKILL.md`

Anchor:

```bash
grep -n "and the merge action in$" .claude/skills/project-brief/SKILL.md
```

**Expected:** exactly one hit. The line **below** it reads `the history context menu.`. Replace
that one line with:

```markdown
the history context menu, and five history-view improvements: a hash column, an ISO date, roomier
chips, a branch chooser for an ambiguous double-click, and prominent tags.
```

Then anchor:

```bash
grep -n "^Seven work packages have shipped:" .claude/skills/project-brief/SKILL.md
```

**Expected:** exactly one hit. Replace `Seven work packages have shipped:` with
`Ten work packages have shipped:` on that line, leaving the rest of the line untouched.

### Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
git status --short
```

**Expected:** the same four baseline failures; only documentation files modified.

### Commit

```bash
git add -A && git commit -m "docs: document the five history-view improvements

Records the decisions the five changes rest on: why the hash column needs
no state migration, why the date is formatted by git and never parsed,
why 2 * LABEL_V_PADDING is the literal that sizeHint always reserved, why
the branch chooser is a new class and which four dialogs were checked
first, and why a tag needs three signals rather than a color alone.

docs/plans/README.md was still German and is translated, as the language
rule requires for a file that is being touched."
```

---

# After the last task

```bash
git log --oneline -7
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
garden check/fmt
```

Seven commits, the four `test/git_test.py` failures and nothing else, formatting clean.

**Do not push and do not open a pull request.** Report what was done, what the final test output
was, and anything you had to deviate from.

## Manual check, if a display is available

1. `garden run` (or `python3 -m cola`) in any repository that has a tag and two branches on one
   commit.
2. The history shows four columns; the rightmost holds a 12-character hash, the STAGE and
   WORKTREE rows leave it empty.
3. The Date, Time column reads `2026-08-01 12:11` — no seconds, no time zone, no weekday.
4. A branch whose name contains a `g`, `p` or `y` has visible space between the letter and the
   bottom of its chip, and the chip itself has visible space above and below it inside its row.
5. A tag row shows `⚑ v1.0.0` in bold, in a color no branch chip uses.
6. Double-clicking a commit that carries two local branches opens a small window listing exactly
   those two; picking one switches to it, and Close changes nothing.
7. Everything above also holds in the **commit list** of the standalone DAG window
   (`View → DAG…`), because both hosts share `CommitHistoryWidget`. Its large **graphics view**
   keeps its own hard-coded green/white/yellow labels — that is the non-goal in §3, not a bug.
