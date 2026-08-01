---
status: completed
completed_at: 2026-08-01
plan_commit: 19501943
implementation_branch: cola-module/performance/plan
implementation_head: f27dd5bc
ci_run: not run (green locally)
manual_verification: |
  - not possible in a headless environment
---

# The history repaints 26x faster, the file icons come back, and the package becomes `fanta`

**Created:** 2026-08-01
**Branch:** commit onto whatever branch is checked out when you start. **Never onto `main`** —
check with `git rev-parse --abbrev-ref HEAD` before Task 1 and create a feature branch first if it
says `main`. This plan does not switch branches.
**Baseline:** written and measured against `562b1338`, i.e. **after** the five history-view
improvements of `docs/plans/2026-08-01-history-ui-improvements.md` landed. Every anchor below was
re-verified against that tree.
**Affects:** `cola/widgets/dag.py` for the performance work, one line in `cola/widgets/filelist.py`
for the icon fix, then a repository-wide rename of the Python package directory `cola/` to
`fanta/`, touching 259 moved files and 56 edited ones.

---

## 0. How to read this plan

This plan is written so that it can be executed **without prior knowledge and without making any
decisions of your own**.

- **Do the tasks strictly in order 0 → 5.** Skip nothing. Each task leaves the suite green.
- **One task = one commit.** The commit message is written out verbatim at the end of each task.
  Use it as it stands.
- **Commit only. Never push.** No task in this plan runs `git push`, and none should. Do not open
  a pull request either.
- **Every task has RED → GREEN → VERIFICATION.** Where a RED step names an expected error, the
  actual output must match it. If it does not: **stop and report**, do not continue.
- **Line numbers are orientation, not truth.** Every edit is preceded by a `grep` that finds the
  anchor. Use the `grep`, not the line number.
- **Copy the code blocks verbatim.** Every block below was applied to this repository and the
  suite was run afterwards. Do not "improve" it while typing it in.
- **Never run `git clean -x`.** It deletes untracked and ignored files, and that includes `env3/`
  and anything you have not committed yet. Where this plan needs a directory removed it names it.
- If a command fails and the plan names no way out: **stop and report.**

**Language.** Everything written into the repository is **English**: code, comments, docstrings,
test names, commit messages, documentation. Several files still contain German from before
2026-07-31 — do not match them, and do not translate them as a side effect of this plan.

**Working directory.** All commands run in the **root of the repository** — where `pyproject.toml`
and `garden.yaml` live. Every path in this plan is **relative to that directory**; the plan
contains no absolute paths and needs none.

**Tool substitution — settle this once in Task 0, then apply it everywhere.**

| Written in the plan | Replace with, if that does not run |
|---|---|
| `python3 -B -m pytest …` | `env3/bin/python -B -m pytest …`, as soon as `env3/` exists |
| `garden fmt` | `cercis bin bin/git-* <pkg> test extras/sphinxtogithub` followed by `isort --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* <pkg> test extras/sphinxtogithub` |
| `garden check/fmt` | `cercis --check bin bin/git-* <pkg> test extras/sphinxtogithub` |

`<pkg>` is `cola` up to and including Task 3, and `fanta` from Task 4 onward.

Standard test command — **the package directory is part of it**, so it changes in Task 4:

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test     # Tasks 0-3
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test    # Tasks 4-5
```

---

## 1. What is being built

### 1.1 The performance work

Scrolling the commit history repaints at about **6 frames per second**. Measured, not estimated:
painting 30 visible rows through `GraphDelegate.paint()` takes **156 ms**.

The cause is a single line. `GraphDelegate.paint()` (`cola/widgets/dag.py:1613`) opens with

```python
style = inline_graph_style(option.palette)
```

and `inline_graph_style()` costs **5.1 milliseconds per call**. It is called **once per row, on
every repaint**, and a second time per text block by `CommitMessageHighlighter.highlightBlock()`.

The function is **pure**: it reads five palette roles and returns a frozen dataclass. Two more
functions on the same path are pure in the same way and are called per row and per chip. All three
get memoized on the identity of the colors they were given. Measured afterwards:

| scenario | before | after |
|---|---|---|
| `inline_graph_style(palette)` | 5111 µs | **15 µs** |
| 30 rows repainted, typical repository | 156 ms (6 fps) | **6.0 ms (167 fps)** |
| 30 rows repainted, every row carrying three chips | 190 ms (5 fps) | **20 ms (49 fps)** |

### 1.2 The rename


The Python package is renamed from `cola` to `fanta`, so that `import fanta` is how the code is
called. The scope is deliberately **shallow**: the import name, the packaging metadata, the build
and launcher files, and the handful of literals that are *functionally* the package path.

Everything else that merely contains the word "cola" is **left alone** — see §3.

### 1.3 The missing file-status icons

Every run prints `qt.svg: Cannot open file '<the opened repository>/plus.svg'`, and every
file-status icon in the history's file panel is invisible. One line is responsible
(`cola/widgets/filelist.py:252`): it hands a bare basename to `icons.from_name()`, whose docstring
asks for `"icons:basename.svg"`. Without the prefix Qt resolves the name against the process
working directory — the repository the user opened — instead of the icon search path.

### Settled decisions

| Question | Decision |
|---|---|
| Cache or restructure the color code? | **Cache.** The functions are already correct, already tested against thirteen palettes, and pure. Rewriting the color math would risk the contrast guarantees for no extra speed: after memoization the profile is dominated by Qt's own `drawText` and `drawRoundedRect`. |
| Does the cache reintroduce the invalidation problem the fork deliberately avoided? | **No.** The cache is keyed on the five palette roles the function reads. A theme change produces a different key and therefore a different style, with no invalidation call anywhere. That *is* "palette-based, no invalidation logic" — it just stops recomputing the identical answer 30 times per repaint. |
| What goes into the cache key? | `(color.isValid(), color.rgba())` per role. **Both parts are required**: measured, an invalid `QColor` and opaque black both report `rgba() == 0xff000000`, and `_opaque_color()` treats them differently. |
| How is the cache bounded? | It is cleared when it exceeds a limit. A real application sees one or two palettes; the limit exists so a test that builds many palettes cannot grow it without bound. Clearing is safe — the worst case is a recomputation. |
| Thread safety? | Not needed. Both call sites are Qt paint paths, i.e. the GUI thread. Even so, a dict `get`/`set` cannot corrupt anything under the GIL; a race would recompute at worst. |
| Anything else worth optimizing? | **No, and that was checked.** §2.3 lists what was profiled and ruled out with numbers. |
| Does the package rename keep a `cola` compatibility shim? | **No.** It is an internal package with no external consumers; a shim would be dead weight. The *user-facing* `git fanta cola` sub-command alias is a different thing and stays. |
| How deep does the rename go? | Imports, module-path string literals, packaging metadata, build files, launchers, and the four literals that are really the install path. Comments, docstrings, class names, config keys and catalog references stay — §3. |
| Why is the rename one commit and not five? | A rename is atomic by nature: after moving the directory, the suite is red until the last reference is rewritten. Splitting it would mean committing a red tree. |
| Which icon call is wrong? | `icons.from_name(basename)` in `cola/widgets/filelist.py:252`. Every other call site in the code base either prefixes the name itself (`qtutils.create_treeitem` does `icons.name_from_basename(icon_name)`) or goes through `icons.icon()`. The fix is to use `icons.icon()`, which *is* `from_name(name_from_basename(basename))`. |
| Is the user's `ellipsis.svg` / `star.svg` / `git-branch.svg` warning the same bug? | **No, and this plan does not claim to fix those.** Those three resolve correctly — verified: `icons.ellipsis()`, `icons.star()` and `icons.branch()` all render from a foreign working directory. Their warnings named a fully resolved path under `cola/icons/`, which means the search path was working and the files were briefly absent; the package directory was being moved at the time. The reproducible defect is the file panel, and that one is fixed here. |
| Performance first or rename first? | **Performance first.** Doing it the other way round would make every anchor in Tasks 1 and 2 point into `fanta/`, and the measurements were taken against `cola/`. |

## 2. Ground truth — all measured

### 2.1 Where the paint time goes

Measured on a repository with 1200 commits, painting the 30 visible rows five times through the
real delegate and a real `QPainter`:

```
paint of 30 rows: 156.1 ms  ->  6.4 fps if repainted continuously

   ncalls  tottime  cumtime  function
    24596    0.070    0.111  cola/widgets/dag.py(_color_luminance)
    10184    0.070    0.081  cola/widgets/dag.py(_opaque_color)
    12298    0.019    0.139  cola/widgets/dag.py(_color_contrast)
       30    0.013    0.257  cola/widgets/dag.py(_lane_colors)
```

Thirty calls to `_lane_colors` for thirty rows: once per row, and each one builds roughly 150
candidate colors and runs `_best_contrast` over them. Broken down by function:

| function | per call |
|---|---|
| `inline_graph_style(palette)` | 5111 µs |
| of which `_lane_colors(palette)` | 4711 µs |
| `readable_chip_fills(4 fills, background)` | 426 µs |
| `_prepare_labels(4 refs)` | 7.9 µs |
| `_row_labels(4 refs)` | 11.5 µs |
| `GraphDelegate._tag_fonts(font)` | 3.5 µs |

`_prepare_labels` and `_row_labels` are called on every mouse move as well. At 8–12 µs they cost
0.35 ms of a 6 ms repaint, and they are **not** touched by this plan. Neither is `_tag_fonts` —
see §2.3.

### 2.2 After the change

```
30 rows, realistic, both caches            6.0 ms  -> 167 fps   (was 156.1 ms /  6 fps)
30 rows, every row three chips, both       20.3 ms ->  49 fps   (was 190.2 ms /  5 fps)
inline_graph_style, cached                 15 us             (was 5111 us)
```

The residual profile of the worst case is `drawText`, `drawRoundedRect` and `horizontalAdvance` —
Qt drawing 90 chips and their labels, which is the floor.

### 2.3 What was profiled and left alone

| Candidate | Measurement | Verdict |
|---|---|---|
| `RepoReader.get()` for 1000 commits | **64 ms**, of which 45 ms is the `git log` subprocess and ~12 ms is `Commit.parse` | Nothing to win, and it runs on a worker thread |
| `graph.build_graph()` for 1000 commits | **5–12 ms** | `active_lanes.index()` inside the loop is O(lanes), and lanes stay below ~20 |
| `gitcfg.GitConfig.get()` | already has `cached=True` by default | Already cached |
| git calls inside loops | the two hits (`cola/gitcmds.py:1028`, `:1037`) iterate two fixed basenames | Not a loop over data |
| Startup plus a full refresh, profiled end to end | nothing from this project above 53 ms, and that is `ColaApplication.__init__` running once | No second hot spot |
| `GraphDelegate._tag_fonts()`, added by the history-view work, builds a `QFont` and a `QFontMetrics` on every `_draw_labels` and `_label_hit_test` call | **3.5 µs** — 0.1 ms of a 6 ms repaint, 1.7% | **Deliberately not cached.** The saving is inside the noise, and a cached `QFont` would be a *mutable* shared object: anything that later called `setBold()` or `setPointSize()` on it would corrupt every other caller. The style and color caches are safe precisely because what they hand out is immutable or never mutated (§2.5) — a `QFont` cache would not have that property |

### 2.4 The rename, measured

The prototype moved 259 files and edited 56. After it, the suite showed **no new failures**. The
non-obvious parts:

| Fact | Evidence |
|---|---|
| `bin/git-fanta`, `bin/git-dag` and `bin/git-fanta-sequence-editor` are Python but have **no `.py` extension**, so a sweep over `*.py` misses them | Measured: all three died with `ModuleNotFoundError: No module named 'cola'` until they were rewritten by name |
| `cola/resources.py` decides the installation prefix by `_package.endswith(os.path.join('site-packages', 'cola'))` and `('pkgs', 'cola')` | `cola/resources.py:27`, `:34`. After the directory move both branches stop matching and an installed release falls into the "source tree" branch with the wrong prefix |
| `test/diffparse_test.py` asserts on the **content of a fixture**, and that content contains `from cola import gitcmds` | Measured: a blanket rewrite made `test_diff` fail with `- from fanta import gitcmds` / `+ from cola import gitcmds`. `test/fixtures/diff.txt` is the source of truth and is **not** rewritten |
| `test/rename_guard_test.py` refers to `cola/` paths in twelve places, including two `REPO_ROOT / 'cola' / …` reads | `test/rename_guard_test.py:47`, `:57-61`, `:151`, `:161`, `:175`, `:206` |
| `cola/main.py:102` registers the sub-command with `aliases=('cola',)` | That is the user-facing `git fanta cola` alias from the 2026-07-30 rename plan, and it stays |
| `cola/widgets/toolbarcmds.py:283`, `:285` pass `'icon': 'cola'`, resolved with `getattr(icons, name)` | `cola/widgets/toolbar.py:254`. Renaming `icons.cola()` removes the toolbar icon **silently** — see `references/gotchas.md` |
| `garden.yaml` has variables named `cola-app` and `cola-app-resources` | They are garden variable names for the macOS bundle, not the package |
| The longer name pushes one line past 88 columns | Measured: `test/widgets_main_history_test.py:483` needs a `garden fmt` afterwards |

### 2.5 Why a shared color object cannot be corrupted

A memoized function hands the *same object* to every caller, so the obvious risk is that someone
mutates it. Three things were checked, and all three hold:

| Check | Result |
|---|---|
| Does anything the caches return alias an object the **caller** owns? | **No.** `readable_chip_fill()` rebinds `fill = _opaque_color(fill)` before its early return, and `_opaque_color()` always constructs a new `QColor`. `_compute_best_contrast()` likewise only returns one of its own copies. Verified by running the early-return path: `out[0] is fills[0]` → `False` |
| Does painting mutate any color the caches hold? | **No.** After 60 paints, selected and unselected, every color in the cached `InlineGraphStyle` and every entry of a cached fills tuple had an unchanged `rgba()` |
| Do the call sites copy before use? | **Yes.** `_draw_labels` wraps the text color in `QtGui.QPen(chip_text)` and hands the fill to `painter.setBrush(brush)`, which constructs a `QBrush`. A grep for `setRed`/`setGreen`/`setBlue`/`setAlpha`/`setRgb`/`setHsv` on any returned color finds nothing in `cola/widgets/dag.py` |

**The invariant to keep:** never mutate a `QColor` you received from `inline_graph_style()`,
`readable_chip_fills()` or `_best_contrast()` — copy it first, the way `_draw_labels` already does.
That is also why `_tag_fonts()` is **not** cached (§2.3): a `QFont` is mutable and is exactly the
kind of object that would break this rule.

### 2.6 The icon defect, measured

```
$ python3 -m cola --repo /tmp/scratch
qt.svg: Cannot open file '/tmp/scratch/plus.svg', because: No such file or directory
```

`plus.svg` **exists** — in `cola/icons/`. It is looked up in the wrong place:

| call | renders? |
|---|---|
| `icons.from_name('plus.svg')` — what `filelist.py:252` does today | **No** |
| `icons.icon('plus.svg')` — what every other call site does | **Yes** |

It affects every code `diff_status_basename()` can return, not only `A`. With the fix, measured
from a foreign working directory:

| status | basename | renders |
|---|---|---|
| `A` | `plus.svg` | yes |
| `D` | `circle-slash-red.svg` | yes |
| `M`, `T` | `modified.svg` | yes |
| `R`, `C` | `git-compare.svg` | yes |
| unknown | `file-code.svg` (filename-derived) | yes |

After the fix a full application start emits **zero** `qt.svg` warnings — measured by counting
them over a 5-second run of the real entry point.

**Why it went unnoticed:** `icons.install()` is only ever called from `cola/app.py`, so in the
test suite no icon resolves at all and `QIcon.isNull()` is useless as an assertion — that is a
documented gotcha in this repository. The two tests in Task 3 are the first that register the
search path on purpose, and they put it back afterwards.

## 3. Non-goals

- **No rewrite of the color math.** `_lane_colors`, `readable_chip_fill` and
  `_distinct_chip_backgrounds` keep their algorithms byte for byte. Only the entry points gain a
  cache.
- **No cache for `_prepare_labels` / `_row_labels`.** Measured at 8–13 µs; a cache would cost more
  in key building than it saves.
- **No change to the history reader, the graph builder or the config layer.** §2.3 has the numbers.
- **No `cola` compatibility package** after the rename.
- **No change to `icons.from_name()` itself.** Making it tolerate a bare basename would hide the
  next occurrence of the same mistake; the docstring already states the contract and one call site
  violated it.
- **No audit of the other 66 icon assets.** Only the file-panel path is fixed, because only it is
  broken: every other basename in `cola/icons.py` reaches Qt through `icons.icon()`.
- **These stay exactly as they are** and are not part of "the important things":
  - the `cola` alias of the `git fanta` sub-command (`cola/main.py:102`) and its test
  - `icons.cola()` and the two `'icon': 'cola'` literals that resolve to it
  - the `cola.*` git-config key fallback in `gitcfg._key_candidates()` and the `~/.cola` legacy
    path in `settings.py`
  - `ColaApplication` / `ColaQApplication` class names
  - the `#: cola/...` source references inside `cola/i18n/*.po`, and `CHANGES.rst`
  - every comment and docstring that merely says "cola" in prose
  - every `github.com/git-cola/...` upstream reference
- **No `widget_version` bump, no state-schema change, no UI change.** Nothing a user can see moves.
- **`test/git_test.py` is not fixed.** See Task 0.

## 4. Traps — all empirically verified

| # | Trap | Evidence |
|---|---|---|
| **F1** | **The suite is not green on a clean checkout in this environment.** Four tests fail before any change, all in `test/git_test.py`, and all unrelated to this work. **Do not "fix" them.** They are the baseline. | Measured on `562b1338` with a clean tree: `4 failed, 794 passed` |
| **F2** | **An invalid `QColor` and opaque black report the same `rgba()`.** `QColor().rgba()` and `QColor(0,0,0).rgba()` are both `0xff000000`, and `_opaque_color()` synthesizes mid-grey for the invalid one. A cache key built from `rgba()` alone would hand the black palette's style to an invalid palette. The key must carry `isValid()` too. | Measured: `invalid.rgba() == black.rgba()` is `True`; with the key in place the two styles are distinct (`#808080` vs `#000000`) |
| **F3** | **`test_inline_graph_style_is_palette_derived_distinct_and_repeatable` asserts `first is not second`.** Re-checked against the current tree, including the tests the history-view work added: that is still the **only** assertion in the whole suite that memoization breaks, and it breaks in both parametrisations. It was written to say "cache-free"; the contract it should say now is "keyed on the palette". | Measured: exactly two failures, `assert InlineGraphStyle(...) is not InlineGraphStyle(...)` |
| **F4** | **`_best_contrast` is called with a `dict.values()` view** in `_lane_colors`, not only with tuples. A key builder must iterate it without consuming it — a view is re-iterable, a generator would not be. No call site passes a generator; verified by reading all six. | `cola/widgets/dag.py:1097` and five tuple call sites |
| **F5** | **`InlineGraphStyle` is a frozen dataclass**, so handing the same instance to several callers is safe: `first.normal_fill = …` already raises `AttributeError`, and a test asserts it. Sharing instances is what makes the cache correct. | `cola/widgets/dag.py:982` (`@dataclass(frozen=True)`); `test/widgets_dag_history_test.py:553` |
| **F6** | **The three `bin/` launchers have no `.py` extension.** `git ls-files '*.py'` does not match `bin/git-fanta`, `bin/git-dag` or `bin/git-fanta-sequence-editor`, so any sweep must name them. `bin/_activate_fanta.py` does have the extension and is caught. | Measured: `bin/git-fanta --help` died with `ModuleNotFoundError: No module named 'cola'` |
| **F7** | **`cola/resources.py` computes the installation prefix from the package directory name.** The two `endswith` checks are code, not comments, and are missed by a sweep that only rewrites imports. | `cola/resources.py:27`, `:34` |
| **F8** | **`test/diffparse_test.py` asserts on fixture content that contains `from cola import gitcmds`.** Rewriting the assertion without rewriting `test/fixtures/diff.txt` makes the test fail; rewriting the fixture would change what the parser is being tested against. **Rewrite only that file's own two import lines.** | Measured failure: `assert '@@ -6,10 +6,21 @@ from fanta import gitcmds' == '… from cola import gitcmds'` |
| **F9** | **`test/rename_guard_test.py` describes the repository to itself.** It has `cola/` in `EXEMPT_PREFIXES`, in five `PROTECTED_REFERENCES` entries, in the `startswith(('cola/', 'bin/'))` filter, in the `garden.yaml` assertion, in an error message and in two `REPO_ROOT / 'cola' / …` paths. All are self-references to the package directory and all move. | `test/rename_guard_test.py:47`, `:57-61`, `:151`, `:161`, `:175`, `:206` |
| **F10** | **`test_product_name_is_git_fanta` scans every tracked text file for `git-cola`, `git_cola`, `Git Cola`, `git cola`.** It does **not** look at the bare word `cola`, so the package rename does not trip it — but a careless "replace cola everywhere" would destroy the allow-listed upstream references it also guards. | `test/rename_guard_test.py:50`, `:110-124` |
| **F11** | **`fanta` is two characters longer than `cola`.** One line crosses the 88-column limit after the sweep. `garden fmt` fixes it; `garden check/fmt` is what notices. | Measured: `test/widgets_main_history_test.py:483` |
| **F12** | **`pytest.ini` sets `--doctest-modules`,** and the test command names the package directory. `pytest … cola test` collects nothing after the move and silently drops every doctest. The command becomes `pytest … fanta test`, in `garden.yaml` too. | `pytest.ini:3`; `garden.yaml:160` |
| **F13** | **`python3 -m fanta` only works from a directory where the package is importable.** The smoke checks in this plan run from the repository root. | Measured: from another directory, `No module named fanta` |
| **F15** | **`QIcon` resolves its file lazily and caches the failure.** An icon built before the `icons:` search path exists stays broken *after* the path is registered — measured: `pixmap(16, 16).isNull()` is still `True`. `icons.from_name` is memoized on top of that, so one early lookup poisons every later user of the same name. The tests in Task 3 therefore clear `icons.from_name.cache` before **and** after they run. | Measured with `QtCore.QDir.setSearchPaths('icons', [])`, then building the icon, then restoring the path |
| **F16** | **`QIcon.isNull()` is not the check.** `QIcon('anything-at-all.svg')` is **not** null; only an icon built from an empty string is. The question "does this icon actually render" is `icon.pixmap(16, 16).isNull()`. | Measured; also stated in `references/gotchas.md` |
| **F14** | **`git mv cola fanta` moves the package *into* `fanta/` when that directory already exists**, prints nothing and exits 0. A `fanta/` left over from an aborted attempt survives `git clean -fd`, because it holds only ignored `__pycache__` directories. | Measured: `git status` then showed `R cola/__init__.py -> fanta/cola/__init__.py` |

## 5. What already exists and is reused (do not rebuild)

| Exists | Where | Role in this plan |
|---|---|---|
| `_opaque_color`, `_color_contrast`, `_color_luminance`, `_mix_color` | `cola/widgets/dag.py:1001-1050` | Untouched. The cache sits in front of the functions that call them. |
| `_lane_colors`, `_distinct_chip_backgrounds`, `readable_chip_fill` | `cola/widgets/dag.py:1053`, `:1184`, `:1107` | Untouched. |
| `InlineGraphStyle`, frozen | `cola/widgets/dag.py:982` | Already immutable, which is why one instance can be shared. |
| `CommitTreeWidget.changeEvent` → `viewport().update()` | `cola/widgets/dag.py:1779` | **Already** the theme-change path. With a keyed cache it needs no addition: the new palette is a new key. |
| `_palette`, `_contrast`, `_adversarial_chip_palettes` | `test/widgets_dag_history_test.py:510`, `:527`, `:1193` | The palettes the new cache tests are written against. |
| `git mv` | — | Records the directory move as renames, so the history of every file survives. |
| `test/rename_guard_test.py` | whole file | **Already** enforces the product-name invariants. Task 3 updates its self-references; it does not gain new rules. |

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

The branch must be `cola-module/performance/plan`. If it is not: **stop and report** — this plan
does not switch branches.

If **no** interpreter has `pytest`, try one of the two routes:

```bash
garden dev/virtualenv && garden dev
```

```bash
python3 -m venv --system-site-packages env3 && env3/bin/python -m ensurepip --upgrade && env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

If that fails too: **STOP and report.** `garden`, `pyupgrade`, `mypy` and `ruff` may all be
missing; that is expected and fine. `cercis` and `isort` **must** be there.

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
4 failed, 794 passed
```

**Note the numbers.** These four are the baseline (trap **F1**). If your machine shows a different
set, write it down and use **that** — but if anything outside `test/git_test.py` fails,
**stop and report**.

The pass count after each task on the reference machine — your absolute numbers may differ, the
**deltas** should not:

| After task | new tests | `passed` | `failed` |
|---|---|---|---|
| 0 (baseline) | — | 794 | 4 |
| 1 — style cache | +4 | 798 | 4 |
| 2 — color caches | +4 | 802 | 4 |
| 3 — file-status icons | +8 | 810 | 4 |
| 4 — the rename | 0 | 810 | 4 |
| 5 — documentation | 0 | 810 | 4 |

---

## Task 1 — Stop rebuilding the whole color scheme once per painted row

**Goal:** `inline_graph_style()` returns a memoized result, keyed on the palette it reads.

### Step 1.1 (RED) — Write the tests

Add two imports to `test/widgets_dag_history_test.py`. The file carries `# ruff: noqa: I001` and
its import block is sorted, so position matters.

**Anchor 1:**

```bash
grep -n "^from cola.widgets import standard$" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit. Insert **directly above it** (`dag` sorts before `standard`):

```python
from cola.widgets import dag as dagwidget
```

**Anchor 2:**

```bash
grep -n "^from cola.widgets.dag import _opaque_color$" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit. Insert **directly below it**:

```python
from cola.widgets.dag import _palette_key
```

Append to the **end** of `test/widgets_dag_history_test.py`:

```python
def _cache_palette(base, alternate, text, highlight, highlighted_text):
    palette = QtGui.QPalette()
    for role, color in (
        (QtGui.QPalette.Base, base),
        (QtGui.QPalette.AlternateBase, alternate),
        (QtGui.QPalette.Text, text),
        (QtGui.QPalette.Highlight, highlight),
        (QtGui.QPalette.HighlightedText, highlighted_text),
    ):
        palette.setColor(role, QtGui.QColor(color))
    return palette


def test_an_equal_palette_reuses_the_same_style(qapp):
    """The style was rebuilt once per painted row and cost 5.8 ms each time."""
    palette = _cache_palette('#ffffff', '#edf0f4', '#202124', '#3268b2', '#ffffff')

    first = inline_graph_style(palette)
    second = inline_graph_style(QtGui.QPalette(palette))

    assert first is second


def test_a_changed_palette_produces_a_different_style(qapp):
    """The key is the palette itself, so a theme change needs no invalidation."""
    palette = _cache_palette('#ffffff', '#edf0f4', '#202124', '#3268b2', '#ffffff')
    original = inline_graph_style(palette)
    changed = QtGui.QPalette(palette)
    changed.setColor(QtGui.QPalette.Highlight, QtGui.QColor('#a23872'))

    updated = inline_graph_style(changed)

    assert updated is not original
    assert updated != original
    assert inline_graph_style(palette) is original


def test_an_invalid_color_does_not_share_a_key_with_black(qapp):
    """Measured: QColor() and QColor(0, 0, 0) report the same rgba() (trap F2)."""
    invalid = QtGui.QColor()
    black = QtGui.QColor(0, 0, 0)
    assert invalid.rgba() == black.rgba()
    invalid_palette = _cache_palette(*[invalid] * 5)
    black_palette = _cache_palette(*[black] * 5)

    assert _palette_key(invalid_palette) != _palette_key(black_palette)
    assert inline_graph_style(invalid_palette) is not inline_graph_style(black_palette)
    assert inline_graph_style(invalid_palette) != inline_graph_style(black_palette)


def test_the_style_cache_does_not_grow_without_bound(qapp):
    """A bounded cache can only ever cost a recomputation, never a wrong answer."""
    for step in range(dagwidget._INLINE_GRAPH_STYLE_CACHE_LIMIT * 3):
        palette = _cache_palette(
            QtGui.QColor(step % 256, 0, 0), '#edf0f4', '#202124', '#3268b2', '#ffffff'
        )
        assert inline_graph_style(palette).normal_fill.isValid()

    assert (
        len(dagwidget._INLINE_GRAPH_STYLE_CACHE)
        <= dagwidget._INLINE_GRAPH_STYLE_CACHE_LIMIT
    )
```

Now fix the one existing assertion that memoization contradicts (trap **F3**). Anchor:

```bash
grep -n "    assert first is not second" test/widgets_dag_history_test.py
```

**Expected:** exactly one hit, inside
`test_inline_graph_style_is_palette_derived_distinct_and_repeatable`. Replace that line with:

```python
    # The style is memoized on the identity of the five palette roles it reads,
    # so an equal palette hands back the same frozen instance. What still has to
    # hold is that a different palette produces a different style, without any
    # invalidation call - that is what the two tests at the end of this file
    # pin down.
    assert first is second
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -6
```

**Expected:** a collection error,

```
ImportError: cannot import name '_palette_key' from 'cola.widgets.dag'
```

Confirm beforehand: `grep -c "_INLINE_GRAPH_STYLE_CACHE" cola/widgets/dag.py` → `0`.

### Step 1.2 (GREEN) — The key and the cache

**Anchor:**

```bash
grep -n "^def inline_graph_style(palette):$" cola/widgets/dag.py
```

**Expected:** exactly one hit. The two lines below it are the docstring and
`    base = _opaque_color(palette.base().color())`. Replace these **three** lines —

```python
def inline_graph_style(palette):
    """Build inline graph colors from the current widget palette without caching."""
    base = _opaque_color(palette.base().color())
```

— with:

```python
def _color_key(color):
    """Return a hashable identity for a QColor.

    An invalid QColor reports the same rgba() as opaque black - measured - and
    _opaque_color() treats the two differently, so validity has to be part of
    the key.
    """
    return (color.isValid(), color.rgba())


_PALETTE_ROLES = ('base', 'alternateBase', 'text', 'highlight', 'highlightedText')
_INLINE_GRAPH_STYLE_CACHE = {}
_INLINE_GRAPH_STYLE_CACHE_LIMIT = 16


def _palette_key(palette):
    """Return the identity of the five palette roles the style is built from."""
    return tuple(
        _color_key(getattr(palette, role)().color()) for role in _PALETTE_ROLES
    )


def inline_graph_style(palette):
    """Return the inline graph colors for a palette, building them once.

    The result depends on nothing but the five palette roles read below, and
    InlineGraphStyle is frozen, so one instance can be shared. Keying the cache
    on the palette is what keeps a theme change working with no invalidation
    call anywhere: a different palette is a different key.

    This is not a micro-optimisation. The function was called once per painted
    row and measured 5.1 ms per call, which put the history at about six frames
    per second while scrolling.
    """
    key = _palette_key(palette)
    cached = _INLINE_GRAPH_STYLE_CACHE.get(key)
    if cached is not None:
        return cached
    base = _opaque_color(palette.base().color())
```

The body from `alternate = …` onwards is **unchanged**. Only its `return` becomes a store.

**Anchor:**

```bash
grep -n "^    return InlineGraphStyle($" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace that line with:

```python
    style = InlineGraphStyle(
```

**Anchor:**

```bash
grep -n "^        lane_colors=_lane_colors(palette),$" cola/widgets/dag.py
```

**Expected:** exactly one hit. The line below it closes the call with `    )`. Insert **below that
closing line**:

```python
    if len(_INLINE_GRAPH_STYLE_CACHE) >= _INLINE_GRAPH_STYLE_CACHE_LIMIT:
        _INLINE_GRAPH_STYLE_CACHE.clear()
    _INLINE_GRAPH_STYLE_CACHE[key] = style
    return style
```

> Nothing else changes. `_lane_colors`, `_distinct_chip_backgrounds` and every color helper keep
> their code exactly as it is — the point of this task is that they run **once per palette**
> instead of once per row.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -4
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** 794 → **798 passed**, still exactly the four baseline failures. In particular the
adversarial palette tests (`test_draw_labels_makes_every_adversarial_chip_opaque_and_contrasting`,
`test_lane_colors_*`, `test_chip_fills_*`) must all still pass — they are what proves the cached
answers are the same answers.

Optional, and worth doing once if you have a repository with a few hundred commits: open the
history and scroll. It should feel immediate.

### Commit

```bash
git add -A && git commit -m "perf: build the inline graph colors once per palette, not once per row

GraphDelegate.paint() opened with inline_graph_style(option.palette), and
that function measured 5.1 ms per call - 4.7 ms of it in _lane_colors,
which builds about 150 candidate colors and runs a contrast search over
them. It ran once per painted row, so repainting the 30 visible rows of
the history took 156 ms: about six frames per second while scrolling.
CommitMessageHighlighter called it a second time per text block.

The function is pure in the five palette roles it reads and returns a
frozen dataclass, so the result is now memoized on those five colors. The
cache-free design was deliberate - a theme change had to work without
invalidation logic - and keying the cache on the palette keeps exactly
that property: a different palette is a different key, and nothing calls
an invalidate.

The key carries isValid() next to rgba() because an invalid QColor and
opaque black report the same rgba(), and _opaque_color() treats them
differently.

Measured afterwards: 5.1 ms per call becomes 15 us, and the 30-row
repaint drops from 156 ms to 6.0 ms."
```

---

## Task 2 — Memoize the two color searches that run per row and per chip

**Goal:** a history where every visible row carries refs repaints at the same speed as one where
none do.

### Step 2.1 (RED) — Write the tests

Append to the **end** of `test/widgets_dag_history_test.py`:

```python
def test_equal_chip_inputs_reuse_the_same_fills(qapp):
    """readable_chip_fills ran once per painted row and measured 426 us."""
    palette = _cache_palette('#ffffff', '#edf0f4', '#202124', '#3268b2', '#ffffff')
    style = inline_graph_style(palette)
    fills = (style.chip_other, style.chip_remote, style.chip_head)
    background = palette.base().color()

    first = readable_chip_fills(fills, background)
    second = readable_chip_fills(
        tuple(QtGui.QColor(fill) for fill in fills), background
    )

    assert first is second


def test_a_different_row_background_gets_its_own_fills(qapp):
    """The selected row is a different background and must not reuse the answer."""
    palette = _cache_palette('#ffffff', '#edf0f4', '#202124', '#3268b2', '#ffffff')
    style = inline_graph_style(palette)
    fills = (style.chip_other, style.chip_remote, style.chip_head)

    on_base = readable_chip_fills(fills, palette.base().color())
    on_highlight = readable_chip_fills(fills, palette.highlight().color())

    assert on_base is not on_highlight
    assert [color.rgba() for color in on_base] != [
        color.rgba() for color in on_highlight
    ]


def test_best_contrast_is_memoized_per_color_identity(qapp):
    """_best_contrast runs once per chip per repaint and searches every candidate."""
    candidates = (QtGui.QColor('#000000'), QtGui.QColor('#ffffff'))
    background = (QtGui.QColor('#3268b2'),)

    first = _best_contrast(candidates, background)
    second = _best_contrast(
        tuple(QtGui.QColor(color) for color in candidates),
        (QtGui.QColor('#3268b2'),),
    )

    assert first is second
    assert _best_contrast(candidates, (QtGui.QColor('#ffffff'),)) is not first


def test_the_color_caches_do_not_grow_without_bound(qapp):
    """Same rule as the style cache: bounded, and a miss only costs time."""
    for step in range(dagwidget._COLOR_CACHE_LIMIT * 2):
        background = QtGui.QColor(step % 256, 17, 42)
        readable_chip_fills((QtGui.QColor('#808080'),), background)
        _best_contrast((QtGui.QColor('#000000'),), (background,))

    assert len(dagwidget._READABLE_CHIP_FILLS_CACHE) <= dagwidget._COLOR_CACHE_LIMIT
    assert len(dagwidget._BEST_CONTRAST_CACHE) <= dagwidget._COLOR_CACHE_LIMIT
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k "chip_inputs or row_background_gets or best_contrast_is_memoized or color_caches_do_not_grow" 2>&1 | tail -8
```

**Expected:** `3 failed, 1 passed`. Two report `assert <QColor…> is <QColor…>` and the third
reports

```
AttributeError: module 'cola.widgets.dag' has no attribute '_COLOR_CACHE_LIMIT'
```

`test_a_different_row_background_gets_its_own_fills` **passes already** — uncached calls return
distinct objects anyway. It is a guard that the cache must not collapse two different backgrounds
onto one answer, and it has to stay green in both directions.

### Step 2.2 (GREEN) — The shared cache helpers and `_best_contrast`

**Anchor:**

```bash
grep -n "^def _best_contrast(candidates, backgrounds):$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Replace **that line only** with:

```python
_BEST_CONTRAST_CACHE = {}
_READABLE_CHIP_FILLS_CACHE = {}
_COLOR_CACHE_LIMIT = 512


def _colors_key(colors):
    """Return a hashable identity for a sequence of QColors."""
    return tuple(_color_key(color) for color in colors)


def _cache_color_result(cache, key, value):
    """Store a memoized color result, discarding the cache when it grows"""
    if len(cache) >= _COLOR_CACHE_LIMIT:
        cache.clear()
    cache[key] = value
    return value


def _best_contrast(candidates, backgrounds):
    """Memoized front end for _compute_best_contrast().

    Called once per chip per repaint, and it walks every candidate against
    every background. The answer depends on nothing but the colors.
    """
    key = (_colors_key(candidates), _colors_key(backgrounds))
    cached = _BEST_CONTRAST_CACHE.get(key)
    if cached is not None:
        return cached
    return _cache_color_result(
        _BEST_CONTRAST_CACHE, key, _compute_best_contrast(candidates, backgrounds)
    )


def _compute_best_contrast(candidates, backgrounds):
```

> `_colors_key` iterates its argument. Every caller passes a tuple or a `dict.values()` view, both
> of which survive a second iteration (trap **F4**); do not change any call site to a generator.

### Step 2.3 (GREEN) — `readable_chip_fills`

**Anchor:**

```bash
grep -n "^def readable_chip_fills(fills, background, floor=2.5):$" cola/widgets/dag.py
```

**Expected:** exactly one hit. Insert **directly above it**:

```python
def readable_chip_fills(fills, background, floor=2.5):
    """Memoized front end for _compute_readable_chip_fills().

    Called once per painted row that carries chips, and measured at 426 us.
    """
    key = (_colors_key(fills), _color_key(background), floor)
    cached = _READABLE_CHIP_FILLS_CACHE.get(key)
    if cached is not None:
        return cached
    return _cache_color_result(
        _READABLE_CHIP_FILLS_CACHE,
        key,
        _compute_readable_chip_fills(fills, background, floor),
    )


```

Then rename the original definition. Anchor:

```bash
grep -n "^def readable_chip_fills(fills, background, floor=2.5):$" cola/widgets/dag.py
```

**Expected:** now **two** hits. Replace the **second** one — the one followed by the docstring
line `    """Make every fill readable on \`background\` and keep them distinct.` — with:

```python
def _compute_readable_chip_fills(fills, background, floor=2.5):
```

Verify afterwards:

```bash
grep -c "^def readable_chip_fills(fills, background, floor=2.5):$" cola/widgets/dag.py
grep -c "^def _compute_readable_chip_fills(fills, background, floor=2.5):$" cola/widgets/dag.py
grep -c "^def readable_chip_fill(fill" cola/widgets/dag.py
```

**Expected:** `1`, `1` and `1`. The third is `readable_chip_fill` — singular, no `s` — a
**different, public function** that is not touched by this task.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -4
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** 798 → **802 passed**, still exactly the four baseline failures.

### Commit

```bash
git add -A && git commit -m "perf: memoize the two color searches on the paint path

readable_chip_fills() runs once per painted row that carries refs and
measured 426 us; _best_contrast() runs once per chip and walks every
candidate against every background. Both are pure in their colors, and
neither ever returns an object its caller owns, so a shared result cannot
be mutated from underneath the cache.

With the style already cached, a history where every visible row carries
three chips still repainted well above the frame budget. Memoizing these
two brings the 30-row worst case to 20 ms, and what is left is Qt drawing
the chips and their labels - the floor.

The two caches share one bound and one store helper, and they key on the
same (isValid, rgba) identity the style cache uses."
```

---

## Task 3 — Make the file-status icons appear

**Goal:** the history's file panel shows an icon per row again, and the application starts without
a single `qt.svg` warning.

### Step 3.1 (RED) — Write the tests

`test/widgets_history_filelist_test.py` already imports `icons`. Add one more. Anchor:

```bash
grep -n "^from cola import icons$" test/widgets_history_filelist_test.py
```

**Expected:** exactly one hit. Insert **directly below it**:

```python
from cola import qtcompat
```

Append to the **end** of `test/widgets_history_filelist_test.py`:

```python
def test_the_file_status_icon_resolves_through_the_icon_search_path(qapp):
    """The reported defect: every status icon in the file panel was missing.

    icons.from_name() wants an "icons:"-prefixed name; handed a bare basename
    it asks Qt for a path relative to the process working directory, which is
    the repository the user opened. This is the one test in the suite that
    registers the icon search path, so it has to put it back afterwards - and
    icons.from_name is memoized, so its cache has to go too.
    """
    icons.install(['default'])
    icons.from_name.cache.clear()
    try:
        item = FileTreeWidgetItem('12\t0\tsrc/main.py')
        item.set_status('A')

        assert not item.icon(0).pixmap(16, 16).isNull()
    finally:
        qtcompat.set_search_paths('icons', [])
        icons.from_name.cache.clear()


@pytest.mark.parametrize('status', ('A', 'D', 'M', 'T', 'R', 'C', ''))
def test_every_status_code_maps_to_an_asset_that_exists(qapp, status):
    """A basename with no file behind it fails silently at paint time."""
    icons.install(['default'])
    icons.from_name.cache.clear()
    try:
        basename = icons.diff_status_basename(status, 'src/main.py')

        assert not icons.icon(basename).pixmap(16, 16).isNull(), basename
    finally:
        qtcompat.set_search_paths('icons', [])
        icons.from_name.cache.clear()
```

> **Both tests clear `icons.from_name.cache` on the way in and on the way out** (trap **F15**).
> The memoized icon for a name that was looked up before the search path existed is permanently
> broken, and leaving a *working* one behind would let a later test pass for the wrong reason.
> `qtcompat.set_search_paths('icons', [])` restores the state every other test expects.
>
> **The assertion is `pixmap(16, 16).isNull()`, never `icon.isNull()`** (trap **F16**).

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py -k "resolves_through_the_icon_search_path or maps_to_an_asset" 2>&1 | tail -6
```

**Expected:** `1 failed, 7 passed`, and in the captured stderr

```
qt.svg: Cannot open file '<repository root>/plus.svg', because: No such file or directory
```

The seven parametrisations of `test_every_status_code_maps_to_an_asset_that_exists` **pass
already** — they check `icons.icon()`, which is the call the fix switches to, and they are there so
a future basename with no asset behind it cannot slip in.

### Step 3.2 (GREEN) — Use the prefixing helper

**Anchor:**

```bash
grep -n "        self.setIcon(0, icons.from_name(basename))" cola/widgets/filelist.py
```

**Expected:** exactly one hit, in `FileTreeWidgetItem.set_status`. Replace that line with:

```python
        self.setIcon(0, icons.icon(basename))
```

That is the whole fix. `icons.icon(basename)` is defined as
`from_name(name_from_basename(basename))`, i.e. exactly what the other call sites do.

> **Do not "fix" `icons.from_name()` to accept a bare basename instead.** Its docstring states the
> contract — an absolute filename or an `icons:` name — and every other caller honours it.
> `qtutils.create_treeitem()` prefixes the name itself at `cola/qtutils.py:834`. Loosening the
> helper would hide the next occurrence.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -8
```

**Expected:** 802 → **810 passed**, still exactly the four baseline failures.

Then confirm the warnings are gone from a real start. This runs the actual entry point against a
scratch repository for five seconds and counts the warnings:

```bash
QT_QPA_PLATFORM=offscreen timeout 40 python3 - 2>&1 <<'RUN' | grep -c "qt.svg"
import sys
sys.argv = ['git-fanta', '--repo', '.']
from qtpy import QtCore, QtWidgets
from cola import main
QtCore.QTimer.singleShot(
    0, lambda: QtCore.QTimer.singleShot(
        5000, lambda: QtWidgets.QApplication.instance().quit()))
try:
    main.main()
except SystemExit:
    pass
RUN
```

**Expected:** `0`. `grep -c` exits non-zero when it counts nothing, so a `0` with a non-zero exit
status is the success case here.

### Commit

```bash
git add -A && git commit -m "fix: show the file-status icons in the history file panel

FileTreeWidgetItem.set_status() handed a bare basename to
icons.from_name(), whose docstring asks for an absolute filename or an
'icons:'-prefixed name. Without the prefix Qt resolves the name against
the process working directory - the repository the user opened - so every
status icon in the panel was invisible and every start printed

  qt.svg: Cannot open file '<repo>/plus.svg', because: No such file ...

It affected all six status codes and the filename-derived fallback, not
just the added one. icons.icon() is the helper that prefixes the name,
and it is what every other call site already uses.

The two new tests are the first in this suite to register the icon search
path on purpose. They clear the memoized icon cache before and after,
because an icon built while no search path existed stays broken once one
is registered - and they assert on pixmap(), because QIcon.isNull() is
false for any non-empty name."
```

---

## Task 4 — Rename the Python package from `cola` to `fanta`

**Goal:** `import fanta` is how the code is called. One commit; the suite is red in the middle of
this task and green at the end.

> **Read §3 before starting.** This task renames the *package*. It does not rename the `git fanta
> cola` sub-command alias, `icons.cola()`, the `cola.*` config-key fallback, `ColaApplication`, or
> any comment. If you find yourself editing a docstring, you have gone too far.

### Step 4.1 — Move the directory

```bash
ls -d fanta 2>/dev/null && echo "STOP: fanta/ already exists"
git mv cola fanta
ls fanta/__init__.py fanta/widgets/dag.py fanta/models/dag.py
ls -d cola 2>/dev/null && echo "STOP: cola/ is still there"
```

**Expected:** the first `ls` prints nothing, the three files exist, and the last `ls` prints
nothing. From here until Step 4.6 the suite does not run — that is expected.

> **`git mv` moves *into* an existing directory** (trap **F14**). If a previous attempt left a
> `fanta/` behind — `git clean -fd` does **not** remove one that holds only ignored
> `__pycache__` directories — then `git mv cola fanta` silently produces `fanta/cola/` and exits
> 0. That is what the two guard commands catch. To recover: `git reset --hard`, then
> `rm -rf fanta`, then start this task again. **Do not** reach for `git clean -x`; it deletes
> `env3/` and anything else you have not committed.

### Step 4.2 — Rewrite imports and module-path literals in every tracked `*.py`

The sweep rewrites three things and nothing else: `from cola` / `from cola.`, `import cola` /
`import cola.`, and a quoted `'cola.<module>'` where `<module>` is a real module or sub-package of
the package.

```bash
MODULES=$(ls fanta/*.py | xargs -n1 basename | sed 's/\.py$//' | tr '\n' '|' | sed 's/|$//')
SUBPKGS="bin|data|i18n|icons|models|widgets"
git ls-files -z '*.py' | xargs -0 sed -i -E \
  -e 's/(^|[^A-Za-z0-9_.])from cola( |\.)/\1from fanta\2/g' \
  -e 's/(^|[^A-Za-z0-9_.])import cola( |$|\.)/\1import fanta\2/g' \
  -e "s/(['\"])cola\.($MODULES|$SUBPKGS)\b/\1fanta.\2/g"
```

Now undo the one file where that sweep rewrote **sample data** instead of code (trap **F8**):

```bash
git checkout -- test/diffparse_test.py
python3 - <<'PY'
path = 'test/diffparse_test.py'
text = open(path, encoding='utf-8').read()
text = text.replace('from cola import core', 'from fanta import core')
text = text.replace('from cola import diffparse', 'from fanta import diffparse')
open(path, 'w', encoding='utf-8').write(text)
PY
grep -n "cola" test/diffparse_test.py
```

**Expected:** exactly three lines — the path handed to the parser and the two assertions that
describe the content of `test/fixtures/diff.txt`:

```
    patch = diffparse.Patch.parse('cola/diffparse.py', core.read(fixture_path))
    assert hunks[0].lines[0] == '@@ -6,10 +6,21 @@ from cola import gitcmds\n'
    assert hunks[0].lines[1] == ' from cola import gitcfg\n'
```

Leave all three. `test/fixtures/diff.txt` is a captured diff and is **not** rewritten.

### Step 4.3 — The three launchers without a `.py` extension

Trap **F6** — `git ls-files '*.py'` does not match these:

```bash
sed -i -E \
  -e 's/(^|[^A-Za-z0-9_.])from cola( |\.)/\1from fanta\2/g' \
  -e 's/(^|[^A-Za-z0-9_.])import cola( |$|\.)/\1import fanta\2/g' \
  bin/git-fanta bin/git-dag bin/git-fanta-sequence-editor
grep -n "fanta\." bin/git-fanta bin/git-dag bin/git-fanta-sequence-editor
```

**Expected:** `from fanta.main import main`, `from fanta import dag` (twice) and
`from fanta import sequenceeditor` — four lines in total.

### Step 4.4 — The literals that are really a path, not prose

Trap **F7**. **Anchor:**

```bash
grep -n "site-packages', 'cola'\|'pkgs', 'cola'" fanta/resources.py
```

**Expected:** exactly two hits. Replace `'cola'` with `'fanta'` in both, so the lines read:

```python
if _package.endswith(os.path.join('site-packages', 'fanta')):
```

```python
elif _package.endswith(os.path.join('pkgs', 'fanta')):
```

Four comment lines around them spell the same three path layouts out and would now contradict the
code directly above and below them. Rewrite those too, plus the three docstrings that name the
package *directory* rather than the product. Anchor:

```bash
grep -n "cola/__file__\|site-packages/cola\|pkgs/cola\|cola/data/\|cola/i18n\|cola.. Python package" fanta/resources.py
```

**Expected:** exactly **seven** hits — lines 29, 30, 36, 40, 97, 106 and 156. Replace `cola` with
`fanta` in each, so they read `site-packages/fanta/__file__.py`, `site-packages/fanta`,
`pkgs/fanta`, `$prefix/fanta/__file__.py`, `hotkey files as fanta/data/ package data`,
`e.g. fanta/i18n`, and `inside the fanta Python package`.

Every other `cola` in that file is prose about the application, not a path, and stays.

Then the one in the documentation build. **Anchor:**

```bash
grep -n "os.path.join(srcdir, 'cola', '_version.py')" docs/conf.py
```

**Expected:** exactly one hit. Replace `'cola'` with `'fanta'` on that line.

Finally the module-run banner. **Anchor:**

```bash
grep -n "python -m cola" fanta/__main__.py
```

**Expected:** exactly one hit, in the module docstring. Replace the first three lines of the file
with:

```python
"""Run git-fanta as a Python module.

Usage: python -m fanta
```

### Step 4.5 — Packaging, build and installer files

None of these contain the product name `git-fanta` in the places being edited; only the package
path changes.

```bash
python3 - <<'PY'
edits = {
    'pyproject.toml': [
        ('"cola', '"fanta'),
        ('\ncola = [', '\nfanta = ['),
    ],
    'pynsist.cfg': [
        ('entry_point=cola.', 'entry_point=fanta.'),
        ('icon=cola/', 'icon=fanta/'),
        ('packages=cola', 'packages=fanta'),
    ],
    'Makefile': [
        ('cola/_version.py', 'fanta/_version.py'),
        ('PYTHON_DIRS = cola', 'PYTHON_DIRS = fanta'),
        ('cola/icons/git-fanta.svg', 'fanta/icons/git-fanta.svg'),
        ('cola/data/*.html', 'fanta/data/*.html'),
        ('"$(DESTDIR)$(pythondir)"/cola', '"$(DESTDIR)$(pythondir)"/fanta'),
    ],
    'garden.yaml': [
        ('cola/*.py cola/*/*.py', 'fanta/*.py fanta/*/*.py'),
        ('mypy --config-file pyproject.toml bin cola',
         'mypy --config-file pyproject.toml bin fanta'),
        ('bin/git-* cola test extras', 'bin/git-* fanta test extras'),
        ('cola/data/*.html', 'fanta/data/*.html'),
        ('cola/icons/git-fanta.svg', 'fanta/icons/git-fanta.svg'),
        ('cola/i18n/*.po', 'fanta/i18n/*.po'),
        ('cola/i18n/git-fanta.pot', 'fanta/i18n/git-fanta.pot'),
        ('--output-dir cola/i18n', '--output-dir fanta/i18n'),
        ('cola/*.py \\', 'fanta/*.py \\'),
        ('cola/*/*.py', 'fanta/*/*.py'),
        ('"$@" cola test', '"$@" fanta test'),
        ('/cola/_version.py', '/fanta/_version.py'),
        ('--ignore=cola/inotify.py', '--ignore=fanta/inotify.py'),
    ],
}
for path, pairs in edits.items():
    text = open(path, encoding='utf-8').read()
    for old, new in pairs:
        text = text.replace(old, new)
    open(path, 'w', encoding='utf-8').write(text)
print('packaging files rewritten')
PY
grep -n "\bcola\b" pyproject.toml pynsist.cfg Makefile garden.yaml | grep -v "git-cola\|cola-app"
```

**Expected:** exactly one remaining line,

```
Makefile:121:	$(RM) "$(DESTDIR)$(prefix)"/bin/cola
```

That is an uninstall rule for a legacy launcher name and is left alone. `cola-app` in
`garden.yaml` is a garden variable for the macOS bundle, not the package (§2.4).

### Step 4.6 — The guard test's self-references

`test/rename_guard_test.py` describes the repository to itself (trap **F9**):

```bash
python3 - <<'PY'
path = 'test/rename_guard_test.py'
text = open(path, encoding='utf-8').read()
pairs = [
    ("EXEMPT_PREFIXES = ('cola/i18n/'", "EXEMPT_PREFIXES = ('fanta/i18n/'"),
    ("('cola/gravatar.py'", "('fanta/gravatar.py'"),
    ("('cola/widgets/about.py'", "('fanta/widgets/about.py'"),
    ("('cola/widgets/log.py'", "('fanta/widgets/log.py'"),
    ("('cola/settings.py'", "('fanta/settings.py'"),
    ("('cola/themes.py'", "('fanta/themes.py'"),
    ("REPO_ROOT / 'cola' / 'version.py'", "REPO_ROOT / 'fanta' / 'version.py'"),
    ("REPO_ROOT / 'cola' / 'i18n' / 'git-fanta.pot'",
     "REPO_ROOT / 'fanta' / 'i18n' / 'git-fanta.pot'"),
    ("'cola/version.py fragt nicht", "'fanta/version.py fragt nicht"),
    ("name.startswith(('cola/', 'bin/'))", "name.startswith(('fanta/', 'bin/'))"),
    ("not name.startswith(('cola/i18n/', 'docs/plans/'))",
     "not name.startswith(('fanta/i18n/', 'docs/plans/'))"),
    ("assert 'cola/icons/git-fanta.svg' in text",
     "assert 'fanta/icons/git-fanta.svg' in text"),
]
for old, new in pairs:
    assert text.count(old) == 1, f'{old!r} found {text.count(old)} times'
    text = text.replace(old, new)
open(path, 'w', encoding='utf-8').write(text)
print('guard test updated')
PY
```

The script asserts each replacement is unique; if one fails, **stop and report**.

### Step 4.7 — Format, then check what is left

```bash
garden fmt
grep -rn "\bcola\b" --include="*.py" fanta/ bin/ test/ extras/ docs/ | grep -v "git-cola\|git_cola\|Git Cola\|ColaApplication\|icons.cola\|_activate_cola" | wc -l
```

**Expected:** a number around **100** — measured: **102**. That is not a warning sign; every one
of them is prose, a git-config key, the sub-command alias or fixture data. The distribution
measured after the sweep, for comparison:

| file | hits | what they are |
|---|---|---|
| `fanta/resources.py` | 11 | prose, "a path relative to cola's …". The seven that named a *path* were fixed in Step 4.4 |
| `test/widgets_dag_history_test.py` | 11 | sample paths inside the `commit_message_file_spans` test data |
| `test/appearance_test.py` | 10 | `cola.*` git-config keys |
| `fanta/gitcfg.py` + `test/gitcfg_test.py` | 11 | the `cola.*` config-key fallback and its tests |
| `test/rename_guard_test.py` | 5 | the legacy product names it guards against |
| `fanta/app.py`, `fanta/cmds.py`, `fanta/main.py` | 10 | config keys, the sub-command alias, prose |
| everything else | the rest | comments and docstrings |

Spot-check with:

```bash
grep -rn "\bcola\b" --include="*.py" fanta/main.py fanta/widgets/toolbarcmds.py test/main_test.py
```

**Expected:** the sub-command alias `aliases=('cola',)`, the two `'icon': 'cola'` entries, and the
alias test. **All three stay** — see §3.

### Verification

```bash
garden check/fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test 2>&1 | tail -8
QT_QPA_PLATFORM=offscreen python3 -m fanta --help 2>&1 | head -2
for launcher in git-fanta git-dag git-fanta-sequence-editor; do
  printf '%-28s ' "$launcher"
  QT_QPA_PLATFORM=offscreen python3 "bin/$launcher" --help 2>&1 | head -1
done
```

**Expected:** formatting clean; **810 passed** and the same four baseline failures; `python3 -m
fanta --help` prints a usage line; each of the three launchers prints its own usage line. A
`ModuleNotFoundError` from any launcher means Step 4.3 was skipped.

> `pytest … cola test` now collects nothing from the package and silently drops every doctest
> (trap **F12**). From here on the command is `pytest … fanta test`.

### Commit

```bash
git add -A && git commit -m "refactor: rename the Python package from cola to fanta

Everything user-facing already carried the fork's name; the package that
implements it did not. 'import fanta' is now how the code is called.

The rename is deliberately shallow. It covers the import name, the
module-path literals that tests patch through, the packaging metadata and
entry points, the build and installer files, the three launchers in bin/
- which have no .py extension and are missed by any sweep over *.py - and
the two literals in resources.py that decide the installation prefix from
the package directory name.

It does not touch what only reads like the old name: the 'git fanta cola'
sub-command alias and its test, icons.cola() and the two 'icon': 'cola'
entries that resolve through getattr, the cola.* git-config fallback,
ColaApplication, the ~/.cola legacy path, the source references inside
the .po catalogs, or any comment.

test/diffparse_test.py keeps three mentions of the old name, because they
describe the content of test/fixtures/diff.txt - a captured diff, not
source code."
```

---

## Task 5 — Write down what was decided

> **Documentation only.** No production code, no tests.

### Step 5.1 — `docs/plans/README.md`

Add one row to the table, directly below the `2026-08-01-history-ui-improvements.md` row:

```markdown
| [2026-08-01-paint-performance-and-fanta-module.md](2026-08-01-paint-performance-and-fanta-module.md) | completed | `cola-module/performance/plan` → *fill in the last commit* |
```

Replace the placeholder with the short hash of the Task 4 commit (`git rev-parse --short HEAD`).

### Step 5.2 — The frontmatter of this plan

Replace the frontmatter of `docs/plans/2026-08-01-paint-performance-and-fanta-module.md` —
currently the three lines `---`, `status: open`, `---` — with:

```yaml
---
status: completed
completed_at: 2026-08-01
plan_commit: <short hash of the commit that added this plan>
implementation_branch: cola-module/performance/plan
implementation_head: <short hash of the Task 4 commit>
ci_run: not run (green locally)
manual_verification: |
  - <what you actually looked at, or "not possible in a headless environment">
---
```

`plan_commit` is found with
`git log --oneline --diff-filter=A -- docs/plans/2026-08-01-paint-performance-and-fanta-module.md`.

### Step 5.3 — `.claude/skills/project-brief/references/fork-history.md`

Anchor:

```bash
grep -n "^## Where the fork's tests live$" .claude/skills/project-brief/references/fork-history.md
```

**Expected:** exactly one hit. Insert **directly above it**:

```markdown
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

```

### Step 5.4 — `.claude/skills/project-brief/references/gotchas.md`

Anchor:

```bash
grep -n "^\*\*Contrast ratio is luminance-only, so it cannot assert that two colors look different.\*\*" .claude/skills/project-brief/references/gotchas.md
```

**Expected:** exactly one hit. Insert **directly above it**:

```markdown
**An invalid `QColor` and opaque black report the same `rgba()`** — both `0xff000000`. Measured.
Anything that keys on a color has to carry `isValid()` as well, because `_opaque_color()`
synthesizes mid-grey for the invalid one and leaves black alone.

**`inline_graph_style()` is memoized on the palette.** It returns a shared frozen instance, so an
equal palette hands back the *same object* — a test that asserts `is not` between two calls is
asserting the old, uncached behavior. A different palette is a different key; nothing invalidates.

```

Then anchor:

```bash
grep -n "^\*\*The formatter is \`cercis\`, not black\*\*" .claude/skills/project-brief/references/gotchas.md
```

**Expected:** exactly one hit. Insert **directly above it**:

```markdown
**An icon built before `icons.install()` stays broken.** `QIcon` resolves its file lazily and
caches the failure: registering the `icons:` search path afterwards does not repair it, and
`icons.from_name` is memoized on top, so one early lookup poisons every later user of that name.
A test that registers the search path must clear `icons.from_name.cache` on the way in and out.

**`QIcon.isNull()` answers the wrong question.** `QIcon('does-not-exist.svg')` is *not* null — only
an icon built from an empty string is. "Does this icon render" is `icon.pixmap(16, 16).isNull()`.

**`icons.from_name()` wants an `icons:`-prefixed name; `icons.icon()` wants a bare basename.**
Handing a basename to `from_name()` makes Qt resolve it against the process working directory,
which is the repository the user opened — the icon silently disappears and `qt.svg` prints one
warning per name. `qtutils.create_treeitem()` prefixes by hand with `icons.name_from_basename()`;
everything else goes through `icons.icon()`.

**The three launchers in `bin/` are Python without a `.py` extension.** `git ls-files '*.py'` does
not match `bin/git-fanta`, `bin/git-dag` or `bin/git-fanta-sequence-editor`; any sweep over the
sources has to name them. `bin/_activate_fanta.py` does have the extension.

**`fanta/resources.py` derives the installation prefix from the package directory name.** Two
`endswith(os.path.join(..., 'fanta'))` checks distinguish a Unix release tree, a Windows release
tree and the source tree. They are code, not comments, and a rename that misses them silently
computes the wrong prefix for an installed release.

**`git mv <dir> <existing-dir>` moves *into* it and exits 0.** A leftover target directory holding
only ignored files survives `git clean -fd`, so a retried rename can silently nest the package.
Guard with `ls -d <target>` first.

```

### Step 5.5 — `.claude/skills/project-brief/SKILL.md`

The brief still says the package is called `cola`. Anchor:

```bash
grep -n "^The Python package is still" .claude/skills/project-brief/SKILL.md
```

**Expected:** exactly one hit. That sentence runs to the end of the following line,
`names it — that is deliberate, do not "fix" it.`. Replace both lines with:

```markdown
The Python package is `fanta` (`import fanta`, `fanta/`); it was renamed from `cola` on
2026-08-01, see `docs/plans/2026-08-01-paint-performance-and-fanta-module.md`. A handful of `cola`
spellings survive on purpose — the `git fanta cola` sub-command alias, `icons.cola()`, the
`cola.*` config fallback and `ColaApplication` — do not "fix" those.
```

Then replace every remaining `cola/` path in that file with `fanta/`:

```bash
sed -i 's|`cola/|`fanta/|g' .claude/skills/project-brief/SKILL.md
grep -n "cola" .claude/skills/project-brief/SKILL.md
```

**Expected:** only the sentences that deliberately mention the old name, plus
`brew install git-cola` and the upstream URLs. If a `cola/` path survives, fix it by hand.

### Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test 2>&1 | tail -8
git status --short
```

**Expected:** the same four baseline failures; only documentation files modified.

### Commit

```bash
git add -A && git commit -m "docs: document the paint cache and the fanta package rename

Records why the style cache is a memoization keyed on the palette rather
than a cache with invalidation, why the key carries isValid() next to
rgba(), what was profiled and deliberately left alone, and where the line
was drawn for the package rename.

Adds the gotchas that cost time here: the invalid-versus-black rgba()
collision, the lazily-resolved QIcon that stays broken once it has failed,
QIcon.isNull() answering the wrong question, from_name() versus icon(),
the three launchers in bin/ that are Python without a .py extension, and
git mv moving a directory into an existing target."
```

---

# After the last task

```bash
git log --oneline -5
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test 2>&1 | tail -8
garden check/fmt
```

Five commits, the four `test/git_test.py` failures and nothing else, formatting clean.

**Do not push and do not open a pull request.** Report what was done, what the final test output
was, and anything you had to deviate from.

## Manual check, if a display is available

1. `garden run` (or `python3 -m fanta`) in a repository with a few hundred commits.
2. Scroll the history with the mouse wheel and by dragging the scrollbar. It follows the input
   without visible lag — before this change it repainted at about six frames per second.
3. Switch the theme (`Preferences → Appearance`). The graph, the chips and the commit-message
   markings all change color immediately; nothing keeps the old palette.
4. Select a commit whose message mentions a file. The file name is still marked in the
   description panel, in the chip color.
5. Select a commit that carries a branch and a tag. The chips look exactly as they did before.
6. `git fanta cola` still starts the application — the sub-command alias was not renamed.
7. The toolbar still shows its icon. If it is missing, `icons.cola()` or one of the two
   `'icon': 'cola'` entries was renamed after all.
8. Select a commit in the history. **Every row of the file panel carries a status icon** — a plus
   for an added file, a slashed circle for a deleted one, and so on. Before this change they were
   all blank.
9. The terminal the application was started from prints **no** `qt.svg` lines at all.
