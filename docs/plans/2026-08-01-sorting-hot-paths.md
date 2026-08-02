---
status: completed
completed_at: 2026-08-01
plan_commit: a478a19b
implementation_branch: cola-module/performance/minimax-M3
implementation_head: 4763969c
ci_run: not run (green locally)
manual_verification: |
  - not possible in a headless environment
---

# Two sorts that should not be sorts

**Created:** 2026-08-01
**Branch:** commit onto whatever branch is checked out when you start. **Never onto `main`** —
check with `git rev-parse --abbrev-ref HEAD` before Task 1 and create a feature branch first if it
says `main`. This plan does not switch branches.
**Affects:** `fanta/widgets/dag.py` (four lines) and `fanta/sequenceeditor.py` (a new helper plus
three call sites), with a new test file for the second one.

> **The Python package is `fanta/`, not `cola/`.** It was renamed on 2026-08-01 by
> `docs/plans/2026-08-01-paint-performance-and-fanta-module.md`, which is completed and already in
> this branch's history. `import fanta`, `fanta/widgets/dag.py`, `pytest … fanta test`. A stale
> `cola/` directory holding nothing but `__pycache__` may still be lying around in a working copy —
> it is not the package, and passing it to `pytest` collects nothing.

---

## 0. How to read this plan

This plan is written so that it can be executed **without prior knowledge and without making any
decisions of your own**.

- **Do the tasks strictly in order 0 → 3.** Skip nothing. Each task leaves the suite green.
- **One task = one commit.** The commit message is written out verbatim at the end of each task.
- **Commit only. Never push.** No task here runs `git push`, and none should.
- **Every task has RED → GREEN → VERIFICATION.** Where a RED step names an expected error, the
  actual output must match it. If it does not: **stop and report**.
- **Line numbers are orientation, not truth.** Every edit is preceded by a `grep` that finds the
  anchor. Use the `grep`, not the line number.
- **Copy the code blocks verbatim.** Every block below was applied to this repository and the
  suite was run afterwards.
- **Never run `git clean -x`.** It deletes untracked and ignored files, `env3/` among them.
- If a command fails and the plan names no way out: **stop and report.**

**Language.** Everything written into the repository is **English**: code, comments, docstrings,
test names, commit messages, documentation. Some files still contain German from before
2026-07-31 — do not match them, and do not translate them as a side effect of this plan.

**Working directory.** All commands run in the **root of the repository**. Every path here is
relative to it.

**Tool substitution — settle this in Task 0, then apply it everywhere.**

| Written in the plan | Replace with, if that does not run |
|---|---|
| `python3 -B -m pytest …` | `env3/bin/python -B -m pytest …`, as soon as `env3/` exists |
| `garden fmt` | `cercis bin bin/git-* fanta test extras/sphinxtogithub` followed by `isort --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* fanta test extras/sphinxtogithub` |
| `garden check/fmt` | `cercis --check bin bin/git-* fanta test extras/sphinxtogithub` |

Those two substitutions are the exact commands `garden.yaml` runs; check them against it if in doubt.

Standard test command:

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test
```

---

## 1. What is being built

Every sorting site in the package was inventoried and measured. **Forty-seven** call sites; six
of them are inside `fanta/polib.py`, a vendored MIT-licensed third-party library that is not ours to
touch. Of the remaining forty-one, exactly **two** are worth changing — and in both cases the fix
is *not to sort*, not to sort differently:

1. **`_color_contrast()` sorts two floating point numbers** to find out which is larger
   (`fanta/widgets/dag.py`). Every colour search on the paint path runs through it — 24 596 calls
   in one *uncached* repaint of 30 history rows. A comparison does the same job. Since the paint
   caches landed it only runs on a cache miss; see §2.4 before you quote any repaint number.
2. **The rebase editor looks up a row number with `list.index()`, once per selected row**
   (`fanta/sequenceeditor.py`). That is O(rows × selection). One pass over the rows answers it for
   every selected item at once. Measured on a 2000-commit rebase with 200 rows selected: **18.9 ms
   → 0.41 ms**, i.e. one arrow-key press stops stuttering.

A third, smaller thing rides along in the same file: `move()` sorts the same list twice.

### The question about LeetCode solutions, answered with a measurement

The request was to check LeetCode-style algorithms, on the grounds that they tend to be the best.
For an algorithms exercise that is fair. For CPython it is the opposite, and it is worth writing
the numbers down so nobody re-opens the question. Sorting 2000 floats:

| implementation | time |
|---|---|
| `sorted()` — Timsort, implemented in C | **0.28 ms** |
| `heapq.heapify` + `heappop` | 0.69 ms — 2.5x slower |
| textbook quicksort, the LeetCode shape | 4.57 ms — **16x slower** |
| textbook merge sort, the LeetCode shape | 6.62 ms — **24x slower** |

Every comparison and every swap in a hand-written sort is a Python bytecode round trip;
`list.sort()` does the whole thing inside one C call, and Timsort additionally exploits runs that
are already ordered — which git output usually is. **Replacing any `sorted()` in this code base
with a hand-written algorithm would be a 16-24x regression.** The wins are elsewhere: not sorting
at all when a comparison or a `min()` answers the question, and not rebuilding an index per lookup.

### Settled decisions

| Question | Decision |
|---|---|
| Replace Timsort anywhere? | **No.** See the table above. Every remaining `sorted()`/`.sort()` in the package is Timsort over data that is either tiny or already nearly ordered, which is Timsort's best case. |
| `_color_contrast`: `max()`/`min()` or a branch? | **A branch.** Measured on the sorting step alone: `sorted()` 365 ns, `max()`/`min()` 226 ns, a branch 109 ns. `max`/`min` are two more C calls and two more luminance-sized temporaries for no gain. |
| How much does that actually buy? | Honest number: **1.21x on the function**, and **1.06x on an uncached 30-row repaint** — median 161.4 ms → 151.9 ms over 18 interleaved samples each. It is free, and it is the hottest function in the program on a cache miss — but the paint caches have since landed, so a miss is only the first paint and a theme change. **§2.4 is not optional reading; it is what keeps this commit message honest.** |
| Key the rebase row map on the item? | **Impossible, and this is the trap of this plan.** `RebaseTreeWidgetItem.__hash__` returns `self.oid`, a **string**, so the item cannot be a dict key or a set member at all — `TypeError: __hash__ method should return an integer`. The map is keyed on `id()`. |
| Fix `__hash__` instead? | **No.** That is a separate defect with its own blast radius, and this plan is explicitly the quick, isolated one. Keying on `id()` needs no change to the class and is exactly what `index()` already does, because `__eq__` is `self is other`. |
| Why does this need a new test file? | `fanta/sequenceeditor.py` has **no test coverage at all** — verified by grep. Nineteen characterization tests go in first, against the current behaviour, and the change has to leave every one of them green. |
| Annotate the new helper? | **Yes.** `fanta/sequenceeditor.py` carries `from __future__ import annotations` and every `def` in it is annotated. `mypy` is configured loosely enough not to force it, but an unannotated helper in that file is idiom drift. Step 2.2 spells the signature out. |

## 2. Ground truth — all measured

### 2.1 The inventory

```bash
grep -rn "\bsorted(\|\.sort(\|heapq\|bisect\|cmp_to_key\|nsmallest\|nlargest" --include="*.py" fanta/
```

47 hits, and **every one of them is a `sorted()` or a `.sort()`** — the package contains no
`heapq`, no `bisect`, no `cmp_to_key`, no `nsmallest`/`nlargest` at all. Grouped, and the counts
sum to 47:

| group | count | verdict |
|---|---|---|
| `fanta/polib.py` | 6 | **Vendored third party** (MIT, see `extras/polib/LICENSE`). Not ours. |
| Sorting git output — `gitcmds.py` (9), `utils.py` (2), `gitcfg.py` (2), `models/main.py` (1), `models/browse.py` (1), `models/selection.py` (1), `widgets/browse.py` (1), `guicmds.py` (1) | 18 | Plain Timsort over lists of paths or refs, once per refresh. Correct as written. |
| Widget-level sorts — `completion.py` (4), `diff.py` (2), `bookmarks.py` (1), `startup.py` (1), `toolbar.py` (1), `status.py` (1), `spellcheck.py` (1) | 11 | Measured, see §2.3. None worth changing. |
| The inline graph — `widgets/dag.py` | 7 | One is worth changing (§2.2); the other six are in §2.3. |
| The rebase editor — `sequenceeditor.py` | 5 | Four lines across three statements are worth changing (§2.2); the fifth is in §2.3. |

### 2.2 The two that are worth changing

**`_color_contrast`**, `fanta/widgets/dag.py`:

```python
def _color_contrast(first, second):
    lighter, darker = sorted(
        (_color_luminance(first), _color_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)
```

`sorted()` over a two-element tuple allocates a list, calls into Timsort and unpacks the result, to
answer "which of these two floats is bigger". Measured:

| the sorting step alone | ns/call |
|---|---|
| `sorted((a, b), reverse=True)` | 365 |
| `max(a, b)` / `min(a, b)` | 226 |
| `if a < b: a, b = b, a` | **109** |

Whole function, luminance included: 2153 ns → 1777 ns, **1.21x**. In the application, on an
uncached 30-row repaint, interleaved A/B with 18 samples each: median **161.4 ms → 151.9 ms**.

**The rebase row lookup**, `fanta/sequenceeditor.py`, in both `shift_up()` and `shift_down()`:

```python
sel_idx = sorted([all_items.index(item) for item in sel_items])
```

`list.index()` scans from the front for every selected item — O(rows × selection). Measured on a
real `RebaseTreeWidget`, and both forms return **identical** row lists at every size:

| rebase size | selected | `index()` | one-pass `id()` map | speedup |
|---|---|---|---|---|
| 50 | 5 | 0.007 ms | 0.009 ms | 0.8x |
| 500 | 50 | 0.981 ms | 0.077 ms | **12.7x** |
| 2000 | 200 | 18.857 ms | 0.407 ms | **46x** |

At 50 rows it is marginally slower and nobody can measure 2 µs. At 2000 rows an arrow-key press
currently blocks the GUI thread for 19 ms.

**`move()`**, same file, sorts the same list twice:

```python
src_base = sorted(src_idxs)[0]
for idx in reversed(sorted(src_idxs)):
```

One sort, then index and reverse it: **2.2x** on that statement pair (58.6 µs → 26.6 µs for 300
indices). It is not hot; it is in this plan because it is three lines away and obviously redundant.

### 2.3 Measured and deliberately left alone

| Candidate | Measurement | Verdict |
|---|---|---|
| Hand-written quicksort / merge sort anywhere | 16x / 24x **slower** than `sorted()` | Never |
| `completion.filter_matches()` — fold the second `_lower()` pass into a decorate-sort-undecorate | **0.87x — slower.** 20 000 refs: 30.25 ms today, 34.60 ms "optimised" | The list comprehension runs in C; the explicit Python loop that would save one `lower()` per match costs more than it saves |
| `reversed(sorted(rows))` → `sorted(rows, reverse=True)` in `diff.py` and `status.py` | 37.7 µs → 33.6 µs for 400 rows, and these lists hold the *selected* rows of a status view | 1.12x on a list of a handful of entries. Not worth a diff |
| `list(sorted(values))` → `sorted(values)` in `models/selection.py` | 33.4 µs → 32.8 µs | Inside the noise |
| The two sorts inside `_prepare_labels()` | 0.31 µs and 0.44 µs of the 7.9 µs the whole function costs | Both sort one to three refs |
| The two sorts inside `commit_message_file_spans()` — `sorted(needles, key=…)` and `spans.sort()` | Over the paths of a single commit, once per description render | **Load-bearing, not incidental.** The first orders needles longest-first so a full path claims its range before its basename can; the second orders the result. Changing either changes behaviour |
| `sorted(node.children, …)` in the graph layout, `commits.sort(key=…)` in `sort_by_generation` | Timsort over the commit list, once per layout; `build_graph` for 1000 commits is 5-12 ms in total | Correct as written |
| `add_remark()` in `sequenceeditor.py` — `tuple(sorted(set(self.remarks + (remark,))))` | A handful of single-character remarks on one item | Deduplicates and orders in one expression. Nothing to win |
| `heapq` / `bisect` for any of the above | — | Nothing here needs a partial sort, a priority queue or an insertion point. `heapq` measured 2.5x slower than `sorted()` for a full ordering |

### 2.4 The paint caches already landed — what Task 1 is actually worth

`docs/plans/2026-08-01-paint-performance-and-fanta-module.md` is **completed and merged**. Commits
`dcf59e04` and `41315c44` memoized `inline_graph_style()`, `readable_chip_fills()` and the best-
contrast search, taking a 30-row repaint from 156 ms to 6.0 ms. That is what stopped
`_color_contrast` from being called 24 596 times per repaint.

There are exactly four `_color_contrast` call sites, and **all four are reachable only through a
cache miss**:

| call site | reached from |
|---|---|
| `_compute_best_contrast()` | `_best_contrast()`, behind `_BEST_CONTRAST_CACHE` |
| `readable_chip_fill()` | only called from `_compute_readable_chip_fills()` |
| `_compute_readable_chip_fills()` | `readable_chip_fills()`, behind `_READABLE_CHIP_FILLS_CACHE` |
| `inline_graph_style()` | behind `_INLINE_GRAPH_STYLE_CACHE` |

**So Task 1 buys ~9 ms on a cache miss and nothing at all while scrolling.** A miss is the first
paint after startup and every theme change. That is still worth four lines — the function gets
cheaper, nothing gets slower, and the `sorted()` was pure overhead either way — but the honest
headline is "the first paint", not "every repaint".

> **Do not repeat the 161.4 ms → 151.9 ms A/B as if it described scrolling.** It was measured
> before the caches existed. It is still the correct number for an *uncached* repaint, which is
> what Task 1's commit message says, and nothing more than that.

Task 2 is unaffected by that plan entirely; the rebase editor has no colours in it.

## 3. Non-goals

- **No new sorting algorithm anywhere.** §1 has the numbers.
- **No `heapq`, no `bisect`, no `functools.cmp_to_key`.** Nothing here needs a partial ordering or
  an insertion point.
- **No change to `fanta/polib.py`.** Vendored third-party code.
- **No fix for `RebaseTreeWidgetItem.__hash__`,** although it is broken: it returns a string, so the
  class is unhashable. Task 2 pins that down in a test and routes around it. Repairing it means
  auditing whatever might start hashing rebase items, which is not a quick fix.
- **No change to `completion.filter_matches`,** measured slower — §2.3.
- **No micro-edits that measure inside the noise** — the `list(sorted(…))` and
  `reversed(sorted(…))` sites stay as they are.
- **No behaviour change of any kind.** Both tasks are pure refactors; every existing assertion has
  to stay green untouched.

## 4. Traps — all empirically verified

| # | Trap | Evidence |
|---|---|---|
| **F1** | **`RebaseTreeWidgetItem` cannot be a dict key or a set member.** `__hash__` returns `self.oid`, a string, so `hash(item)` raises `TypeError: __hash__ method should return an integer`. A row map keyed on the item — the obvious implementation — crashes the rebase editor the first time it is used. Key on `id(item)`. | Measured: `{item: 0}` → `TypeError: cannot use 'fanta.sequenceeditor.RebaseTreeWidgetItem' as a dict key` |
| **F2** | **`__eq__` is `self is other`.** That is what makes an `id()` map equivalent to `list.index()`: both find the same row even when two items carry the same oid and summary. If `__eq__` were value-based the two would disagree on duplicates. | `fanta/sequenceeditor.py`, `RebaseTreeWidgetItem.__eq__`; asserted in `test_the_rebase_item_compares_by_identity` |
| **F3** | **`fanta/sequenceeditor.py` has no tests at all.** `grep -rln "sequenceeditor\|RebaseTreeWidget" test/` finds nothing. Task 2 writes nineteen characterization tests *first* and they must pass against the **unchanged** code — a RED here would mean the tests are wrong, not the code. | Measured: `19 passed` before any production edit |
| **F4** | **`RebaseTreeWidget.__init__` takes three positional arguments** — `(context, comment_char, parent)` — and all three are required. `RebaseTreeWidget(None, None)` raises `TypeError: missing 1 required positional argument: 'parent'`. A `None` context is fine for these tests: `move()` reaches only `decorate()` and `validate()`, and neither reads `self.context`. | Measured |
| **F5** | **The suite is not green on a clean checkout in this environment.** Four tests in `test/git_test.py` fail before any change and are unrelated to this work. **Do not "fix" them.** | Measured: `4 failed, 811 passed`, stable over three consecutive runs |
| **F6** | **A Qt teardown segfault appears roughly once in a dozen full-suite runs**, with no failing test, and does not reproduce. Re-run once. It repeats at the same test only if something is genuinely broken. The new test file was run five times in a row without a repeat. | Measured during this plan's development |
| **F7** | **`pytest.ini` sets `--doctest-modules`.** A `>>>` in a new docstring becomes a test. None of the docstrings here contain one. | `pytest.ini` |

## 5. What already exists and is reused (do not rebuild)

| Exists | Where | Role |
|---|---|---|
| `_color_luminance()` | `fanta/widgets/dag.py` | Untouched. Task 1 only changes how its two results are compared. |
| The contrast assertions | `test/widgets_dag_history_test.py` — `test_chip_fills_*`, `test_head_accent_stays_visible_*`, `test_draw_labels_makes_every_adversarial_chip_*` | **Already** cover `_color_contrast` against thirteen palettes. Task 1 adds no new colour test; those are the proof it did not change behaviour. |
| `standard.TreeMixin.items()` / `selected_items()` | `fanta/widgets/standard.py` | The two accessors the rebase helper takes its arguments from. Untouched. |
| `qapp` / `managed_qobject` fixtures | `test/widgets_history_checkout_test.py` | The pattern the new test file copies verbatim, as this repository requires. |

---

# TASKS

## Task 0 — Make sure the tests run, and record the baseline

> **Blocking. No commit.**

```bash
git rev-parse --abbrev-ref HEAD
python3 -m pytest --version 2>&1 | head -1
ls -d env3 2>/dev/null && env3/bin/python -m pytest --version 2>&1 | head -1
command -v garden cercis isort
```

If the branch is `main`, create a feature branch before Task 1 and stay on it. If **no**
interpreter has `pytest`:

```bash
garden dev/virtualenv && garden dev
```

```bash
python3 -m venv --system-site-packages env3 && env3/bin/python -m ensurepip --upgrade && env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

If that fails: **STOP and report.** `cercis` and `isort` **must** be available.

### Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test 2>&1 | tail -7
```

**Expected:**

```
FAILED test/git_test.py::test_stdout - assert 69 == 0
FAILED test/git_test.py::test_stderr - assert 0 == 69
FAILED test/git_test.py::test_stdout_and_stderr - assert 0 == 69
FAILED test/git_test.py::test_it_doesnt_deadlock - assert 0 == 69
4 failed, 811 passed
```

**The check that matters is "no failure outside `test/git_test.py`", not the exact number.** If
anything else fails, **stop and report**. The pass count can come up one short on a run that hit
the teardown flake of trap **F6**; re-run once before treating a one-off `810` as a problem. What
must hold at every step is the *delta*: Task 2 adds exactly 19 and nothing else moves.

> **If you see `ERROR: file or directory not found: cola`,** you typed `cola` where the package is
> `fanta`. If you see a number well below 811, you pointed `pytest` at a leftover `cola/` directory
> that holds only `__pycache__`: `pytest.ini` sets `--doctest-modules`, so a wrong package path
> silently drops every module doctest instead of failing. Re-run with `fanta test`.

| After task | new tests | `passed` | `failed` |
|---|---|---|---|
| 0 (baseline) | — | 811 | 4 |
| 1 — the contrast comparison | 0 | 811 | 4 |
| 2 — the rebase row lookup | +19 | 830 | 4 |
| 3 — documentation | 0 | 830 | 4 |

---

## Task 1 — Stop sorting two numbers to find the larger one

**Goal:** `_color_contrast()` compares instead of sorting. No behaviour change.

> **No RED step, and that is deliberate.** This is a pure refactor of a function that thirteen
> palette tests already exercise from every direction. Writing a test that asserts "the result is
> the same as before" would only restate the implementation. The existing suite is the RED/GREEN
> gate: it is green now, and it has to be green afterwards with **not one assertion touched**.

### Step 1.1 — Replace the sort with a comparison

**Anchor:**

```bash
grep -n "^def _color_contrast(first, second):$" fanta/widgets/dag.py
```

**Expected:** exactly one hit. Replace that function — the five lines from `def _color_contrast`
down to and including the `return` — with:

```python
def _color_contrast(first, second):
    """Return the WCAG contrast ratio between two colors.

    sorted() over a two-element tuple allocates a list and calls into Timsort
    to answer "which of these is larger"; measured at 365 ns against 109 ns for
    the comparison. Every color search on the paint path runs through here, so
    this is the hottest function in the program whenever those caches miss -
    24596 calls in one uncached repaint of 30 history rows.
    """
    lighter = _color_luminance(first)
    darker = _color_luminance(second)
    if lighter < darker:
        lighter, darker = darker, lighter
    return (lighter + 0.05) / (darker + 0.05)
```

> The result is identical for equal luminances, and `darker` is a luminance in `[0, 1]`, so the
> denominator can never be zero. Both were true before and neither is changed here.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test 2>&1 | tail -7
git diff --stat
```

**Expected:** **811 passed**, the same four baseline failures, **no test file modified** — the diff
touches `fanta/widgets/dag.py` and nothing else. In particular these must all still pass, because
they are what proves the contrast maths is unchanged:

- `test_chip_fills_stay_readable_on_a_selected_row`
- `test_chip_fills_stay_readable_on_an_unselected_row`
- `test_chip_fills_stay_three_distinct_colors`
- `test_head_accent_stays_visible_against_row_and_node`
- `test_draw_labels_makes_every_adversarial_chip_opaque_and_contrasting`

### Commit

```bash
git add -A && git commit -m "perf: compare two luminances instead of sorting them

_color_contrast() called sorted() on a two-element tuple to find out
which of two floats is larger. That allocates a list and enters Timsort;
measured at 365 ns against 109 ns for the comparison, and 2153 ns against
1777 ns for the whole function including the luminance work.

Every color search on the paint path goes through it, so it is the
hottest function in the program on a cache miss - 24596 calls in one
uncached repaint of 30 history rows. An interleaved A/B over 18 samples
each put that uncached repaint at 161.4 ms before and 151.9 ms after.

Since the paint caches landed in 41315c44 a miss only happens on the
first paint and on a theme change; while scrolling, the caches answer and
this function is not called at all. The four lines are still worth it -
nothing gets slower and the sorted() was pure overhead.

Pure refactor. The thirteen palette tests that exercise the contrast
maths are untouched and still green."
```

---

## Task 2 — Look up rebase rows in one pass

**Goal:** `shift_up()` and `shift_down()` stop scanning the row list once per selected item, and
`move()` stops sorting the same list twice.

### Step 2.1 (characterization) — Write the tests against the **unchanged** code

`fanta/sequenceeditor.py` has no tests (trap **F3**). Create `test/sequenceeditor_move_test.py`
with exactly this content:

```python
# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Row bookkeeping in the rebase sequence editor.

shift_up(), shift_down() and move() translate between selected items and their
row numbers. There was no coverage for any of it before these tests.
"""

import sys

import pytest

from fanta.sequenceeditor import RebaseTreeWidget
from fanta.sequenceeditor import RebaseTreeWidgetItem
from qtpy import QtCore
from qtpy import QtTest
from qtpy import QtWidgets


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for offscreen widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-fanta-test']
        )
    yield instance


@pytest.fixture
def managed_qobject(qapp):
    """Delete parentless Qt test objects after the test."""
    objects = []

    def manage(obj):
        objects.append(obj)
        return obj

    yield manage

    QtTest.QTest.qWait(5)
    qapp.processEvents()
    for obj in reversed(objects):
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def _rebase_tree(managed_qobject, count):
    """A rebase widget holding `count` pick rows."""
    tree = managed_qobject(RebaseTreeWidget(None, '#', None))
    items = [
        RebaseTreeWidgetItem(
            index, True, 'pick', oid='%040x' % index, summary='commit %d' % index
        )
        for index in range(count)
    ]
    tree.invisibleRootItem().addChildren(items)
    return tree, items


def _select(tree, items, rows):
    tree.clearSelection()
    for row in rows:
        items[row].setSelected(True)


def test_the_rebase_item_cannot_be_used_as_a_dict_key(qapp):
    """__hash__ returns the oid string, so hashing raises (trap F1).

    Any row lookup therefore has to key on id(), not on the item.
    """
    item = RebaseTreeWidgetItem(0, True, 'pick', oid='abc', summary='s')

    with pytest.raises(TypeError):
        hash(item)


def test_the_rebase_item_compares_by_identity(qapp):
    """Two items with equal contents are still different rows."""
    first = RebaseTreeWidgetItem(0, True, 'pick', oid='abc', summary='s')
    second = RebaseTreeWidgetItem(0, True, 'pick', oid='abc', summary='s')

    assert first == first
    assert first != second


@pytest.mark.parametrize('rows', ([0], [3], [1, 2], [0, 4], [0, 1, 2, 3, 4]))
def test_shift_down_reports_the_selected_rows_in_order(qapp, managed_qobject, rows):
    """The emitted row numbers are the selection, sorted, and nothing else."""
    tree, items = _rebase_tree(managed_qobject, 6)
    _select(tree, items, rows)
    emitted = []
    tree.move_rows.connect(lambda src, dst: emitted.append((list(src), dst)))

    tree.shift_down()

    assert emitted == [(sorted(rows), sorted(rows)[0] + 1)]


@pytest.mark.parametrize('rows', ([1], [4], [2, 3], [1, 5]))
def test_shift_up_reports_the_selected_rows_in_order(qapp, managed_qobject, rows):
    tree, items = _rebase_tree(managed_qobject, 6)
    _select(tree, items, rows)
    emitted = []
    tree.move_rows.connect(lambda src, dst: emitted.append((list(src), dst)))

    tree.shift_up()

    assert emitted == [(sorted(rows), sorted(rows)[0] - 1)]


def test_shift_up_does_nothing_at_the_top(qapp, managed_qobject):
    tree, items = _rebase_tree(managed_qobject, 4)
    _select(tree, items, [0])
    emitted = []
    tree.move_rows.connect(lambda src, dst: emitted.append((src, dst)))

    tree.shift_up()

    assert emitted == []


def test_shift_down_does_nothing_at_the_bottom(qapp, managed_qobject):
    tree, items = _rebase_tree(managed_qobject, 4)
    _select(tree, items, [3])
    emitted = []
    tree.move_rows.connect(lambda src, dst: emitted.append((src, dst)))

    tree.shift_down()

    assert emitted == []


def test_shift_without_a_selection_emits_nothing(qapp, managed_qobject):
    tree, _items = _rebase_tree(managed_qobject, 4)
    emitted = []
    tree.move_rows.connect(lambda src, dst: emitted.append((src, dst)))

    tree.shift_up()
    tree.shift_down()

    assert emitted == []


@pytest.mark.parametrize(
    ('src_idxs', 'dst_idx', 'expected'),
    (
        ([0], 2, [1, 2, 0, 3, 4]),
        ([3], 1, [0, 3, 1, 2, 4]),
        ([1, 2], 3, [0, 3, 4, 1, 2]),
        ([2, 1], 3, [0, 3, 4, 1, 2]),
        ([0, 1], 0, [0, 1, 2, 3, 4]),
    ),
)
def test_move_reorders_the_rows(qapp, managed_qobject, src_idxs, dst_idx, expected):
    """Characterization: move() is order-insensitive in its source rows."""
    tree, items = _rebase_tree(managed_qobject, 5)
    original = list(items)

    tree.move(list(src_idxs), dst_idx)

    root = tree.invisibleRootItem()
    order = [original.index(root.child(row)) for row in range(root.childCount())]
    assert order == expected
```

**Run it — against the code as it is now:**

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/sequenceeditor_move_test.py 2>&1 | tail -3
```

**Expected:** `19 passed`. The file is already in `cercis` and `isort` shape, so `garden fmt` will
not rewrite it.

> **These are characterization tests, not a RED step** (trap **F3**). They describe what the code
> already does, so they pass immediately. A failure here means the test is wrong — **stop and
> report**, do not "fix" the production code to match it.
>
> `test_the_rebase_item_cannot_be_used_as_a_dict_key` passing is what licenses the `id()` key in
> Step 2.2.

### Step 2.2 (GREEN) — One pass instead of one scan per selected row

**Anchor:**

```bash
grep -n "^class RebaseTreeWidget(standard.DraggableTreeWidget):$" fanta/sequenceeditor.py
```

**Expected:** exactly one hit. Insert **directly above it** (two blank lines stay between the new
function and the class):

```python
def _selected_rows(
    all_items: list[RebaseTreeWidgetItem],
    selected_items: list[RebaseTreeWidgetItem],
) -> list[int]:
    """Return the row number of every selected item.

    all_items.index(item) walks the list once per selected row, which is
    quadratic on a long rebase. RebaseTreeWidgetItem compares by identity, so a
    single pass over the rows gives the same answer. The map is keyed on id()
    and not on the item itself: __hash__ returns the oid string, so the item
    cannot be a dict key at all.
    """
    row_of = {id(item): row for row, item in enumerate(all_items)}
    return [row_of[id(item)] for item in selected_items if id(item) in row_of]


```

> The annotations reference `RebaseTreeWidgetItem`, which is defined **later** in the file. That is
> fine and needs no quoting: `fanta/sequenceeditor.py` starts with `from __future__ import
> annotations`, so annotations are never evaluated. The rest of the module annotates the same way —
> `toggle_remark_of_items()` already takes a `list[RebaseTreeWidgetItem]`.

**Anchor:**

```bash
grep -n "        sel_idx = sorted(\[all_items.index(item) for item in sel_items\])" fanta/sequenceeditor.py
```

**Expected:** **two** hits — one in `shift_down()`, one in `shift_up()`. Replace **both** lines
with:

```python
        sel_idx = sorted(_selected_rows(all_items, sel_items))
```

> The `if id(item) in row_of` guard keeps the old tolerance: `list.index()` would have raised
> `ValueError` for an item that is not in the list, but no caller ever passes one — `selected_items()`
> and `items()` read the same tree. The guard keeps a stray item from turning a silent no-op into a
> traceback.

### Step 2.3 (GREEN) — Sort once in `move()`

**Anchor:**

```bash
grep -n "        src_base = sorted(src_idxs)\[0\]" fanta/sequenceeditor.py
```

**Expected:** exactly one hit. Replace that line **and the one below it** —

```python
        src_base = sorted(src_idxs)[0]
        for idx in reversed(sorted(src_idxs)):
```

— with:

```python
        ordered_idxs = sorted(src_idxs)
        src_base = ordered_idxs[0]
        for idx in reversed(ordered_idxs):
```

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/sequenceeditor_move_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test 2>&1 | tail -7
```

**Expected:** `19 passed` for the new file — **the same nineteen, unchanged** — and 811 → **830
passed** for the whole suite, with the four baseline failures.

If the full-suite run dies in a Qt teardown segfault with no failing test, re-run it once
(trap **F6**).

### Commit

```bash
git add -A && git commit -m "perf: find rebase row numbers in one pass

shift_up() and shift_down() called all_items.index(item) once per
selected row, so moving a block of commits was O(rows x selection).
Measured on a real RebaseTreeWidget: a 2000-commit rebase with 200 rows
selected took 18.9 ms per arrow-key press, which is a visible stutter on
the GUI thread. One pass over the rows brings it to 0.41 ms. At 50 rows
the two are within 2 us of each other.

The map is keyed on id() rather than on the item, because
RebaseTreeWidgetItem.__hash__ returns the oid string and the class is
therefore unhashable - a dict keyed on the item raises TypeError. That is
safe here because __eq__ is 'self is other', so index() and an id() map
find the same row even for two items carrying the same oid.

move() sorted the same list twice; it now sorts once and indexes it.

The file had no test coverage at all. Nineteen characterization tests go
in first, describe the behaviour as it was, and are unchanged by this
commit."
```

---

## Task 3 — Write down what was decided

> **Documentation only.** No production code, no tests.

### Step 3.1 — `docs/plans/README.md`

**The table already has a row for this plan.** Do not add a second one — **replace** it.

**Anchor:**

```bash
grep -n "2026-08-01-sorting-hot-paths.md" docs/plans/README.md
```

**Expected:** exactly one hit, reading `| [2026-08-01-sorting-hot-paths.md](…) | **open** | — |`.
Replace that whole line with:

```markdown
| [2026-08-01-sorting-hot-paths.md](2026-08-01-sorting-hot-paths.md) | completed | *fill in the branch* → *fill in the last commit* |
```

Fill both placeholders from `git rev-parse --abbrev-ref HEAD` and `git rev-parse --short HEAD`.

While you are in this file, one row above is stale and belongs to the plan this one builds on:

**Anchor:**

```bash
grep -n "2026-08-01-paint-performance-and-fanta-module.md" docs/plans/README.md
```

**Expected:** exactly one hit, still marked `**open**`. That plan's own frontmatter says
`status: completed`, so the index contradicts it. Read the branch and the commit out of that
frontmatter rather than guessing them —

```bash
head -10 docs/plans/2026-08-01-paint-performance-and-fanta-module.md
```

— and replace the line with the same shape as every other completed row, substituting its
`implementation_branch` and `implementation_head`:

```markdown
| [2026-08-01-paint-performance-and-fanta-module.md](2026-08-01-paint-performance-and-fanta-module.md) | completed | `<implementation_branch>` → `<implementation_head>` |
```

Do not touch that plan's frontmatter. Its record is its own; this step only repairs the index.

### Step 3.2 — The frontmatter of this plan

Replace the three lines `---`, `status: open`, `---` at the top of
`docs/plans/2026-08-01-sorting-hot-paths.md` with:

```yaml
---
status: completed
completed_at: 2026-08-01
plan_commit: <short hash of the commit that added this plan>
implementation_branch: <branch>
implementation_head: <short hash of the Task 2 commit>
ci_run: not run (green locally)
manual_verification: |
  - <what you actually looked at, or "not possible in a headless environment">
---
```

### Step 3.3 — `.claude/skills/project-brief/references/gotchas.md`

Anchor:

```bash
grep -n "^## Toolchain$" .claude/skills/project-brief/references/gotchas.md
```

**Expected:** exactly one hit. Insert **directly above it**:

```markdown
## Sorting

**Do not replace `sorted()` with a hand-written algorithm.** Measured on 2000 floats: `sorted()`
0.28 ms, `heapq` 0.69 ms, textbook quicksort 4.57 ms, textbook merge sort 6.62 ms. Timsort runs
inside one C call and exploits the runs that git output already has; every comparison in a Python
implementation is a bytecode round trip. The wins are in *not* sorting — a comparison instead of
`sorted()` on two values, `min()` instead of `sorted(x)[0]`, one index pass instead of
`list.index()` per lookup.

**`RebaseTreeWidgetItem` is unhashable.** `__hash__` returns `self.oid`, a string, so `hash(item)`
raises `TypeError` and the item cannot be a dict key or a set member. `__eq__` is `self is other`,
so anything that needs a lookup table keys on `id(item)` — that finds the same row `list.index()`
would.

**`fanta/polib.py` is vendored third-party code** (MIT, `extras/polib/LICENSE`). It holds six of
the package's forty-seven sorting call sites and none of them are ours to change.

```

### Step 3.4 — `.claude/skills/project-brief/references/fork-history.md`

Anchor:

```bash
grep -n "^## Where the fork's tests live$" .claude/skills/project-brief/references/fork-history.md
```

**Expected:** exactly one hit. Insert **directly above it**:

```markdown
## 12. The two sorts that should not have been sorts

Plan: `docs/plans/2026-08-01-sorting-hot-paths.md`.

All 47 sorting call sites in the package were inventoried and measured; two were worth changing,
and in both cases the fix was to stop sorting rather than to sort differently.

**Decisions that later work must not undo:**

- **`_color_contrast()` compares, it does not sort.** Do not "tidy" it back into a `sorted()` or a
  `max()`/`min()` pair: 365 ns, 226 ns and 109 ns respectively for the same answer. Every colour
  search on the paint path reaches it, so it is the hottest function in the program on a cache
  miss — but since section 11 landed, a miss is only the first paint and a theme change. Do not
  quote its saving as a per-repaint number.
- **The rebase row lookup keys on `id()`.** `RebaseTreeWidgetItem.__hash__` returns a string, so
  the item cannot be a dict key. `__eq__` is identity, which is what makes `id()` equivalent to
  what `list.index()` found.
- **Timsort stays everywhere else.** A hand-written quicksort measured 16x slower and a merge sort
  24x slower than `sorted()`, and `heapq` 2.5x slower, on 2000 elements.
- **`completion.filter_matches()` was measured and left alone.** Folding its second `lower()` pass
  into a decorate-sort-undecorate loop is 0.87x — slower, because the list comprehension it
  replaces runs in C.
- **`test/sequenceeditor_move_test.py` is the first coverage `fanta/sequenceeditor.py` ever had.**
  Its nineteen tests are characterization tests: they described the behaviour before the change
  and were not touched by it.

```

### Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test 2>&1 | tail -7
git status --short
```

**Expected:** the same four baseline failures; only documentation files modified.

### Commit

```bash
git add -A && git commit -m "docs: document the sorting review and its two outcomes

Records what was measured across all 47 sorting call sites, why Timsort
stays everywhere, and the two places where the answer was to stop sorting
- a comparison instead of sorted() on two floats, and one index pass
instead of list.index() per selected rebase row.

Adds two gotchas: hand-written sort algorithms are 16-24x slower than
sorted() in CPython, and RebaseTreeWidgetItem is unhashable because
__hash__ returns a string."
```

---

# After the last task

```bash
git log --oneline -4
QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test 2>&1 | tail -7
garden check/fmt
```

Three commits, `830 passed` with the four `test/git_test.py` failures, formatting clean.

**Do not push and do not open a pull request.** Report what was done, what the final test output
was, and anything you had to deviate from.

## Manual check, if a display is available

1. `garden run`, open the history, switch the theme twice. The chips and the graph keep the same
   colours they had before this change — Task 1 is a refactor, not a restyle.
2. Start an interactive rebase over a few hundred commits
   (`GIT_SEQUENCE_EDITOR=... git rebase -i HEAD~300`, or the Rebase action in the application).
   Select a block of rows and hold the shift-up / shift-down shortcut. The rows follow the key
   without lag; before this change each press scanned the list once per selected row.
3. Drag a block of rows to a new position. The order afterwards is the same as it was before —
   that is what `test_move_reorders_the_rows` pins down.
