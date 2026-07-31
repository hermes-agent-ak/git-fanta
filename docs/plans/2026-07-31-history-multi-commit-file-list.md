---
status: completed
completed_at: 2026-07-31
plan_commit: cdb9cfde
implementation_branch: tree-ui/multi-select/minimax-M3
implementation_head: c8cca254
ci_run: nicht ausgefuehrt (lokal gruen - garden check/fmt lokal gruen; check/pyupgrade und check/mypy sind in der Umgebung nicht verfuegbar gewesen)
manual_verification: |
  - In einer Headless-Umgebung nicht moeglich. Punkte 4 (Diff-Doppelklick ueber Multi-Commit), 6 (DAG-Fenster) und 7 (Rebase-Editor) haben hier keine Test-Abdeckung. Punkte 1, 2, 3 und 5 sind durch die Tests aus Task 2 abgedeckt.
---

# Multi-commit selection in the history: every file the selection touches

**Created:** 2026-07-31
**Branch:** Commit the tasks onto whatever branch is checked out at the start. **Never onto
`main`** — the pattern for feature work is `tree-ui/<agent>/<model>/<topic>`. Check before Task 1:
`git rev-parse --abbrev-ref HEAD`. If it says `main`, create a branch first. This plan does **not**
create one.
**Affects:** `FileWidget` in `cola/widgets/filelist.py`, and through it **three** hosts: the
history file panel in the main window, the `Files` dock of the standalone DAG window, and the
rebase sequence editor (`cola/sequenceeditor.py:227`).

---

## 0. How to read this plan

This plan is written so that it can be executed **without prior knowledge and without making any
decisions of your own**.

- **Do the tasks strictly in order 0 → 3.** Skip nothing.
- **One task = one commit.** The commit message is written out verbatim at the end of each task.
  Use it as it stands.
- **Every task has RED → GREEN → VERIFICATION.** Where a RED step names an expected error, the
  actual output must match it. If it does not: **stop and report**, do not continue.
- **Line numbers are orientation, not truth.** Every edit is preceded by a `grep` that finds the
  anchor. Use the `grep`, not the line number.
- **The full test suite is green after every task.**
- If a command fails and the plan names no way out: **stop and report.**

**Language.** Everything written into the repository is **English**: code, comments, docstrings,
test names, commit messages, documentation. This plan is English for the same reason. Some
existing files still contain German from before 2026-07-31 — do not match them, and do not
translate them as a side effect of this plan either.

**Working directory.** All commands run in the **root of the repository** — where `pyproject.toml`
and `garden.yaml` live. Every path in this plan is **relative to that directory**; the plan
contains no absolute paths and needs none.

**Tool substitution — settle this once in Task 0, then apply it everywhere.**

| Written in the plan | Replace with, if that does not run |
|---|---|
| `python3 -B -m pytest …` | `env3/bin/python -B -m pytest …`, as soon as `env3/` exists |
| `garden fmt` | `cercis bin bin/git-* cola test extras/sphinxtogithub` followed by `isort --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* cola test extras/sphinxtogithub` |
| `garden check/fmt` | `cercis --check bin bin/git-* cola test extras/sphinxtogithub` |

> **Important:** if Task 0 creates an `env3/`, then `env3/bin/python` applies to **every** further
> `pytest` call in this plan — the commands below are all written with `python3` for brevity. A
> `python3 -m pytest` that aborts with `No module named pytest` is **not** a RED, it is the wrong
> substitution.

Standard test commands:

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test
```

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py
```

---

## 1. What is being built

When the user selects **several** commits, the file list shows **the union of the files those
commits touch** — exactly one row per file.

Today the multi-commit branch instead attempts a **range** (`git diff commits[0]~ commits[-1]`)
and crashes before showing anything at all (trap **F1**).

Settled decisions:

| Question | Decision |
|---|---|
| Range or union? | **Union.** Decided by the user. A range shows files that were never selected when the selection is non-contiguous, swallows changes that cancel out inside the range, and yields an empty panel for any selection containing the root commit. Evidence in §2. |
| How is the union fetched? | With **one** call: `git show <oid1> <oid2> … --format= --numstat --raw --no-renames -z`. `git show` accepts several revisions and returns one raw+numstat block per revision, in the order given — **exactly the format `parse_status_and_numstat` already parses** (trap **F3**). The parser is **not** touched. |
| File touched by several commits? | **One** row. The numbers under `+` and `-` are **summed**; binary files keep the `-` git writes instead of a count (trap **F7**). |
| Which order? | **First appearance.** For a single commit that is literally git's own output, exactly as today — so the single-commit case changes **by not one character**. Sorting alphabetically would change behaviour for the single-commit case and is therefore a non-goal (§3). |
| Which status letter (`A`/`M`/`D`)? | That of the **newest** selected commit touching the file. It falls out for free: the selection arrives sorted old-to-new via `sort_by_generation` (`cola/widgets/dag.py:1597`), and `dict.update()` lets the last one win. |
| `STAGE`/`WORKTREE` in the selection? | They come along. They are not revisions, they need their own commands (`git diff-index` / `git diff-files`) and **no** `-z`. Costs **at most three** git calls, no matter how many commits are selected. |
| One source fails? | It is skipped rather than emptying the whole list. If **all** of them fail the list is empty — exactly as today. |
| Where does the code live? | All of it in `cola/widgets/filelist.py`. The widget is shared by three hosts; the rule belongs in the widget, not in the hosts. |

## 2. Why a union — the evidence

Measured against a purpose-built repository (`C1` root, `C2` adds `a.txt`, `C3` adds
`middle.txt`, `C4` adds `tmp.txt`, `C5` deletes `tmp.txt`):

| Selection | Range (`git diff C[0]~ C[-1]`) | Union |
|---|---|---|
| `C2` + `C4`, `C3` skipped | `a.txt`, **`middle.txt`**, `tmp.txt` — `middle.txt` was never selected | `a.txt`, `tmp.txt` |
| `C4` + `C5` (adds, then deletes) | **empty** — the changes cancel out | `tmp.txt` (`+1`/`-1`) |
| `C1` + `C3` (with the root) | **empty** — `C1~` does not exist, exit 128 | `A`, `B`, `middle.txt` |

The root case is also the reason the crash in trap **F1** went unnoticed for so long: it only
occurs for a **valid** range. For an invalid range the `status != 0` early return fires first and
all you see is an empty panel.

## 3. Non-goals

- **No change to `parse_status_and_numstat`.** It already parses `git show` output over several
  revisions correctly — measured, see trap **F3**.
- **No change to `list_files` or `FileTreeWidgetItem`.** The new function produces exactly the row
  format `adds\tdels\tpath` that both already expect.
- **No alphabetical sorting of the file list.** That would change behaviour for the single-commit
  case (today: git's order) and is not part of the request.
- **No change to the description panel.** Its rule "show the newest commit when several are
  selected" is already correct in `docs/plans/2026-08-01-commit-description-panel.md`. See §6.
- **No change to `cola/widgets/dag.py`, `cola/widgets/main.py` or `cola/sequenceeditor.py`.** All
  three call `commits_selected(commits)` unchanged.
- **No handling of tabs inside paths.** `list_files` and `FileTreeWidgetItem` have always taken
  `path = texts[2]` after `split('\t')`; the new function does the same. A path containing a real
  tab would already be displayed wrongly today — that is a separate subject.
- **No translation of the German plan or German comments that already exist elsewhere.** New
  material is English; old material is corrected when it is touched, not by this plan.
- **No `widget_version` bump**, no new state key, no new menu action.

## 4. Traps — all empirically verified

| # | Trap | Evidence |
|---|---|---|
| **F1** | **Today's multi-commit branch crashes.** `oid` is assigned only in the single-commit branch (`cola/widgets/filelist.py:130`) but read unconditionally after the `if`/`else` (`:159`). | Measured against a real repo, selecting two commits over a valid range: `UnboundLocalError: cannot access local variable 'oid' where it is not associated with a value`, raised at `cola/widgets/filelist.py:159` |
| **F2** | **`--numstat -z` leaves the path tab-separated.** One might expect `-z` to NUL-separate the numstat fields too ("use NULs as output field terminators"). It does **not** for the path: the row stays `adds\tdels\tpath`, only the record ends with NUL. That is why `parse_status_and_numstat` works unchanged. | Measured with git 2.53.0: `git show <oid> --format= --numstat --raw --no-renames -z` → `:100644 100644 5626abf 9a72323 M<NUL>one.txt<NUL>1<TAB>0<TAB>one.txt<NUL>` |
| **F3** | **`git show` accepts several revisions** and returns one raw+numstat block per revision, **in the order given**, in the same NUL format it uses for a single one. This is the whole trick of this plan. | Measured: `git show C1 C2 …` → `:…A<NUL>a.txt<NUL>1<TAB>0<TAB>a.txt<NUL>:…M<NUL>f.txt<NUL>1<TAB>0<TAB>f.txt<NUL>`. `git show C2 C1` returns the same blocks in reverse, so it does **not** reorder. |
| **F4** | **A merge commit yields numstat without raw.** The status part is missing entirely; `status_by_path` stays empty for those paths and the icon falls back to the filename. That is already true today and stays true. | Measured: `git show <merge> --format= --numstat --raw --no-renames -z` → only `1<TAB>0<TAB>side.txt<NUL>`. Covered by `test_parser_tolerates_numstat_without_raw` |
| **F5** | **`git show <root>` works, `<root>~` does not.** Precisely why the union is right for the root commit and the range is empty. | Measured: `git show <root> --format= --numstat --raw -z` → `:000000 100644 0000000 4286f42 A<NUL>root.txt<NUL>1<TAB>0<TAB>root.txt<NUL>`; `git diff <root>~ …` → exit 128, `fatal: ambiguous argument …` |
| **F6** | **A test counts the `git show` calls.** `test_public_selection_reaches_all_standalone_consumers_synchronously` (`test/widgets_dag_history_test.py:371`) monkeypatches `git.show` and asserts `len(show_calls) == 1` (`:399`) for a single-commit selection. The one-call design in this plan honours that; "one `show` per commit" would have broken it. | `test/widgets_dag_history_test.py:399`; measured with the new implementation: single selection → 1 call, six commits → **also 1** |
| **F7** | **Binary files carry `-` instead of a number.** Anything summing the numbers has to tolerate that, or `int()` raises `ValueError`. | Measured: `git show <oid> … -z` for a binary file → `-<TAB>-<TAB>b.bin<NUL>` |
| **F8** | **The wording of `UnboundLocalError` depends on the Python version.** From 3.11 on it reads `cannot access local variable 'oid' where it is not associated with a value`, before that `local variable 'oid' referenced before assignment`. The exception **type** is `UnboundLocalError` in both cases — check for that, not for the text. | The long wording measured under Python 3.14.4. The short wording is **not** measured (no 3.9/3.10 available) and comes from the known CPython change |
| **F9** | **`cola/widgets/filelist.py` uses no type annotations** and has no `from __future__ import annotations`. New code must therefore carry **no** annotations: `int \| None` would be a runtime error under the 3.9 target interpreter. | Measured: `grep -c "def .*) ->" cola/widgets/filelist.py` → `0`; `grep -n "from __future__" cola/widgets/filelist.py` → no hit (`cola/git.py:1` and `cola/core.py:6` have it, `filelist.py` does not) |
| **F10** | **`pytest.ini` sets `--doctest-modules`.** A `\t` in a docstring is a real tab; write **`\\t`** in docstrings, exactly as `parse_status_and_numstat` already does (`cola/widgets/filelist.py:292`). A `>>>` would become a test. | `pytest.ini:3`; `cola/widgets/filelist.py:292` |
| **F11** | **There is a third host.** `cola/sequenceeditor.py:227` connects `FileWidget.commits_selected` to the rebase editor's selection. It is **harmless**: `cola/sequenceeditor.py:562` truncates the list with `commits = commits[-1:]` to **exactly one** commit, so it never reaches the multi-commit branch. Nothing changes for it. | `cola/sequenceeditor.py:226-228`, `:559-563` |
| **F12** | **Not a single test touches the multi-commit branch.** That is how the bug shipped, and why the suite is green today even though the function is broken. | Measured: `grep -rn "commits_selected(\[.*,.*\])" test/` → no hit |
| **F13** | **`STAGE` and `WORKTREE` always sit last in the sorted selection.** `RepoReader` gives them `generation = parent_commit.generation + 1` (`cola/models/dag.py:415`, `:431`), and the selection passes through `sort_by_generation`. That is why their status wins the `dict.update()` — which is correct, they are the newest state. | `cola/models/dag.py:405-431`, `cola/widgets/dag.py:1597` |
| **F14** | **`docs/plans/2026-08-01-commit-description-panel.md` runs in parallel** and changes **the same two files**: it appends `all_paths()` to `FileWidget` (its Task 2) and tests to `test/widgets_history_filelist_test.py`. Different methods, same files. See §6. | `docs/plans/2026-08-01-commit-description-panel.md`, Task 2 |

## 5. What already exists and is reused (do not rebuild)

| Exists | Where | Role in this plan |
|---|---|---|
| `parse_status_and_numstat(output, separator)` | `cola/widgets/filelist.py:285` | **Is** the parser. Handles the multi-revision output of `git show` unchanged (trap **F3**) and tolerates numstat without raw (trap **F4**). **Not** touched. |
| `FileWidget.list_files(files_log, status_by_path=None)` | `cola/widgets/filelist.py:167` | **Is** the display. Clears itself first, so the empty case needs no special path. Expects rows `adds\tdels\tpath` — exactly what the new function produces. |
| `app_context` fixture | `test/helper.py:85` | **Is** the test repository: a real `git init` in a temp directory, `chdir` into it, `A` and `B` staged (not yet committed), a real `git`/`cfg`/`MainModel`. Do not build your own repo, do not mock `context.git`. |
| `qapp`, `managed_qobject` | `test/widgets_history_filelist_test.py:21`, `:31` | **Already in the file** this plan extends. Do not rewrite them, do not copy them. |
| `_fake_commit(oid, summary='summary')` | `test/widgets_history_filelist_test.py:135` | **Is** the commit stand-in. `commits_selected` reads nothing but `.oid`. |
| `_git(*args)` with `subprocess` + `.strip()` | `test/widgets_main_history_test.py:138`, `test/widgets_history_checkout_test.py:52` | **Template** for the git helper that `test/widgets_history_filelist_test.py` does not have yet. Copy the form literally. |
| `dag.STAGE`, `dag.WORKTREE` | `cola/models/dag.py:17-18` | Already imported (`cola/widgets/filelist.py:11`). No new import. |

## 6. Relationship to the description panel

`docs/plans/2026-08-01-commit-description-panel.md` runs in parallel. The boundary:

- **This plan changes the file list, that one changes the text field above it.** The rule "on a
  multi-commit selection the description shows the newest commit, `selection[-1]`" is already
  settled there — its §1 decision table, wired up in its Task 4, anchor 4. **Nothing to do here
  for that.** (That plan is still written in German; it predates the English rule.)
- **Trap F8 of that plan becomes moot through this one.** It describes exactly this
  `UnboundLocalError` and defers the fix to a separate plan — this is that plan. That plan
  re-checks the spot itself before its Task 4. Task 3 here updates the note.
- **A side effect that should be known there:** after this plan `all_paths()` returns the paths of
  **all** selected commits, while the description shows only the newest commit's message. A
  filename in that message can therefore be highlighted even though a *different* selected commit
  touched it. That is acceptable — what gets highlighted is what stands in the list below — but it
  is a deliberate decision, not an oversight.
- **The order of the two plans does not matter.** They touch different methods. Both plans carry
  the same working-tree guard (Task 1 here, Task 2 there).

---

# TASKS

## Task 0 — Make sure the tests run

> **Blocking. No commit.** The goal is a single finding: **which test command works here?** Every
> task that follows depends on an observed RED and GREEN output.

```bash
python3 -m pytest --version 2>&1 | head -1
ls -d env3 2>/dev/null && env3/bin/python -m pytest --version 2>&1 | head -1
command -v garden cercis isort pyupgrade mypy
python3 -c "import qtpy; print('qtpy', qtpy.API_NAME)"
```

> **Careful — in the environment where this plan was written, _none_ of that was installed.**
> Measured on 2026-07-31: `pytest`, `cercis`, `isort`, `pyupgrade`, `mypy`, `garden` and `ruff`
> were all missing; there was no `env3/`; `python3` was 3.14.4; only `qtpy` (vendored in the
> repository root) and `PyQt5` were present, `PyQt6` was not. `python3 -m venv` also failed
> (`ensurepip` missing, `python3-venv` not installed) and there was no `python3 -m pip`.

If **no** interpreter has `pytest`, try one of the two routes:

```bash
garden dev/virtualenv && garden dev
```

```bash
python3 -m venv --system-site-packages env3 && env3/bin/python -m ensurepip --upgrade && env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

If that fails too: **STOP and report.** This plan cannot be executed without running tests — it is
structured entirely around TDD, and every RED expectation below is an observation that has to be
made.

### Verification

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -5
```

**Expected:** `NNN passed`, no `failed`, no `error`. **Note `NNN` as the baseline.**

---

## Task 1 — Fold the rows together

**Goal:** a pure function with no Qt and no git: `merge_numstat_rows(rows)` turns the numstat rows
of several commits into one row per path.

> Deliberately written without Qt so that it can be pinned down entirely by a table test. It is
> the only piece of real logic in this plan.

### Step 1.1 — Check the working tree (trap **F14**)

```bash
git status --short cola/widgets/filelist.py test/widgets_history_filelist_test.py
```

If there are changes there that are **not yours**: **stop and report** instead of writing over
them. The description-panel plan changes the same two files.

### Step 1.2 (RED) — Write the tests

Add the import to `test/widgets_history_filelist_test.py` — **one line**, in the same group,
alphabetically (`merge_numstat_rows` before `parse_status_and_numstat`):

Anchor:

```bash
grep -n "^from cola.widgets.filelist import" test/widgets_history_filelist_test.py
```

```python
from cola.widgets.filelist import merge_numstat_rows
```

Append to the **end** of `test/widgets_history_filelist_test.py`:

```python
@pytest.mark.parametrize(
    ('scenario', 'rows', 'expected'),
    (
        ('nothing at all', [], []),
        ('a single row', ['1\t0\ta.py'], ['1\t0\ta.py']),
        (
            'two files stay two rows',
            ['1\t0\ta.py', '2\t3\tb.py'],
            ['1\t0\ta.py', '2\t3\tb.py'],
        ),
        ('the same file is summed', ['1\t0\ta.py', '2\t3\ta.py'], ['3\t3\ta.py']),
        (
            'the order of first appearance wins',
            ['1\t0\tb.py', '1\t0\ta.py', '1\t0\tb.py'],
            ['2\t0\tb.py', '1\t0\ta.py'],
        ),
        ('binary stays binary', ['-\t-\tb.bin'], ['-\t-\tb.bin']),
        ('binary is contagious', ['1\t0\tb.bin', '-\t-\tb.bin'], ['-\t-\tb.bin']),
        (
            'binary first is just as contagious',
            ['-\t-\tb.bin', '1\t0\tb.bin'],
            ['-\t-\tb.bin'],
        ),
        ('an incomplete row is dropped', ['1\t0'], []),
        ('an empty row is dropped', [''], []),
    ),
)
def test_merge_numstat_rows_lists_every_path_once(scenario, rows, expected):
    """One row per path, counts summed, binary files left alone."""
    assert merge_numstat_rows(rows) == expected
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -8
```

**Expected error — the whole file fails during collection:**

```
ImportError: cannot import name 'merge_numstat_rows' from 'cola.widgets.filelist'
```

> This is a **collection error**, not a single test failure, and here that is intended: the
> function does not exist yet. To confirm beforehand:
> `grep -c merge_numstat_rows cola/widgets/filelist.py` → `0`.

### Step 1.3 (GREEN) — Add the function

**Anchor:**

```bash
grep -n "^def parse_status_and_numstat(output, separator):" cola/widgets/filelist.py
```

**Expected:** exactly **one** hit. Insert **directly before it**:

```python
def _add_count(total, field):
    """Add one numstat field to a running total.

    Returns None as soon as a field is not a plain number: git writes '-'
    instead of a count for binary files, and a total that mixes counted and
    uncounted changes has no meaningful number to report.
    """
    if total is None or not field.isdigit():
        return None
    return total + int(field)


def merge_numstat_rows(rows):
    """Combine numstat rows so that every path is listed exactly once.

    Rows arrive as ``adds\\tdels\\tpath``, one per path *per commit*. A path
    that several selected commits touch is reported once, with its added and
    deleted lines summed; its first appearance decides where it sits in the
    list. A binary file keeps the '-' that git writes instead of a count.
    """
    totals = {}
    for row in rows:
        fields = row.split('\t')
        if len(fields) < 3:
            continue
        path = fields[2]
        adds, dels = totals.get(path, (0, 0))
        totals[path] = (_add_count(adds, fields[0]), _add_count(dels, fields[1]))
    return [
        '{}\t{}\t{}'.format(
            '-' if adds is None else adds, '-' if dels is None else dels, path
        )
        for path, (adds, dels) in totals.items()
    ]


```

> **No type annotations** (trap **F9**). **`\\t` in the docstring**, not `\t` (trap **F10**).
> The "first appearance" order costs no code: `dict` has preserved insertion order since
> Python 3.7.

### Verification

```bash
garden fmt
```

> Without `garden`, the substitutes from the table in §0. If **no** formatter is installed: note
> it and carry on — the code above is hand-set to 88 columns.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -3
```

**Expected:** all passed, **10 tests more** than before.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 10 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "feat: fold per-commit numstat rows into one row per path

merge_numstat_rows() sums the added and deleted lines of a path that several
commits touch and keeps the order of its first appearance. Binary files carry
'-' instead of a count and keep it."
```

---

## Task 2 — The file list shows the union

**Goal:** `commits_selected` describes the selection as a union instead of a range — and stops
crashing while doing it.

### Step 2.1 (RED) — Write the tests

Add the import at the top of `test/widgets_history_filelist_test.py`. Anchor:

```bash
grep -n "^import sys$" test/widgets_history_filelist_test.py
```

Insert **directly before it** (alphabetically before `sys`):

```python
import subprocess
```

Append to the **end** of the file:

```python
def _git(*args):
    """Same form as in test/widgets_main_history_test.py: with strip()."""
    return subprocess.run(
        ('git', *args), check=True, text=True, capture_output=True
    ).stdout.strip()


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(content)


def _commit_file(path, content, message):
    """Write, stage and commit one file, and return its oid."""
    _write(path, content)
    _git('add', path)
    _git('commit', '-q', '-m', message)
    return _git('rev-parse', 'HEAD')


@pytest.fixture
def history_repo(app_context):
    """Six commits where a union and a range disagree.

    app_context has already staged A and B but committed nothing, so the first
    commit made here is the root commit holding exactly those two files.
    """
    _git('commit', '-q', '-m', 'C1 root')
    oids = {'root': _git('rev-parse', 'HEAD')}
    oids['a'] = _commit_file('a.txt', 'a\n', 'C2 add a')
    oids['middle'] = _commit_file('middle.txt', 'm\n', 'C3 add middle')
    oids['tmp'] = _commit_file('tmp.txt', 't\n', 'C4 add tmp')
    _git('rm', '-q', 'tmp.txt')
    _git('commit', '-q', '-m', 'C5 delete tmp')
    oids['untmp'] = _git('rev-parse', 'HEAD')
    oids['a_again'] = _commit_file('a.txt', 'a\nagain\n', 'C6 touch a again')
    return oids


def _listed(widget):
    """(path, +, -) per row, in display order."""
    return [
        (
            widget.topLevelItem(row).path,
            widget.topLevelItem(row).text(1),
            widget.topLevelItem(row).text(2),
        )
        for row in range(widget.topLevelItemCount())
    ]


def _paths(widget):
    return [path for path, _adds, _dels in _listed(widget)]


def test_two_selected_commits_list_the_files_of_both(
    qapp, app_context, history_repo, managed_qobject
):
    """The reported bug: two commits spanning a valid range."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['a']), _fake_commit(history_repo['middle'])]
    )

    assert _paths(widget) == ['a.txt', 'middle.txt']


def test_non_contiguous_selection_ignores_unselected_commits(
    qapp, app_context, history_repo, managed_qobject
):
    """C3 was skipped, so middle.txt does not belong in the list."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['a']), _fake_commit(history_repo['tmp'])]
    )

    assert _paths(widget) == ['a.txt', 'tmp.txt']


def test_selection_including_the_root_commit_lists_its_files(
    qapp, app_context, history_repo, managed_qobject
):
    """The root commit has no parent, and its files still show up."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['root']), _fake_commit(history_repo['middle'])]
    )

    assert _paths(widget) == ['A', 'B', 'middle.txt']


def test_file_added_and_deleted_across_the_selection_stays_listed(
    qapp, app_context, history_repo, managed_qobject
):
    """C4 adds tmp.txt and C5 deletes it; it was touched either way."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['tmp']), _fake_commit(history_repo['untmp'])]
    )

    assert _listed(widget) == [('tmp.txt', '1', '1')]


def test_file_touched_twice_is_listed_once_with_summed_counts(
    qapp, app_context, history_repo, managed_qobject
):
    """Two commits on the same file make one row, not two."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['a']), _fake_commit(history_repo['a_again'])]
    )

    assert _listed(widget) == [('a.txt', '2', '0')]


def test_single_commit_selection_is_unchanged(
    qapp, app_context, history_repo, managed_qobject
):
    """Characterization: a single-commit selection behaves as it always did."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected([_fake_commit(history_repo['a_again'])])

    assert _listed(widget) == [('a.txt', '1', '0')]


def test_unknown_revision_leaves_the_list_empty(
    qapp, app_context, history_repo, managed_qobject
):
    """Characterization: an unknown oid leaves nothing behind."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected([_fake_commit(history_repo['a']), _fake_commit('d' * 40)])

    assert _paths(widget) == []


def _dirty_worktree():
    """One staged and one unstaged change, as the history shows them.

    No update_status() needed: for STAGE and WORKTREE commits_selected asks git
    directly, not the model. Verified.
    """
    _write('staged.txt', 's\n')
    _git('add', 'staged.txt')
    with open('a.txt', 'a', encoding='utf-8') as handle:
        handle.write('dirty\n')


def test_stage_pseudo_commit_lists_the_staged_files(
    qapp, app_context, history_repo, managed_qobject
):
    """Characterization: STAGE is not a revision, it is the index."""
    widget = managed_qobject(FileWidget(app_context, None))
    _dirty_worktree()

    widget.commits_selected([_fake_commit(dag.STAGE)])

    assert _paths(widget) == ['staged.txt']


def test_worktree_pseudo_commit_lists_the_modified_files(
    qapp, app_context, history_repo, managed_qobject
):
    """Characterization: WORKTREE is the working tree against the index."""
    widget = managed_qobject(FileWidget(app_context, None))
    _dirty_worktree()

    widget.commits_selected([_fake_commit(dag.WORKTREE)])

    assert _paths(widget) == ['a.txt']


def test_commit_with_stage_and_worktree_lists_all_of_them(
    qapp, app_context, history_repo, managed_qobject
):
    """Commit, index and working tree together: three sources, one list."""
    widget = managed_qobject(FileWidget(app_context, None))
    _dirty_worktree()

    widget.commits_selected(
        [
            _fake_commit(history_repo['a_again']),
            _fake_commit(dag.STAGE),
            _fake_commit(dag.WORKTREE),
        ]
    )

    assert _listed(widget) == [('a.txt', '2', '0'), ('staged.txt', '1', '0')]


def test_one_git_show_serves_the_whole_selection(
    qapp, app_context, history_repo, managed_qobject
):
    """One call for all commits, not one per commit.

    Honours test_public_selection_reaches_all_standalone_consumers_synchronously,
    which expects exactly one git show call.
    """
    widget = managed_qobject(FileWidget(app_context, None))
    calls = []
    real_show = app_context.git.show
    app_context.git.show = lambda *args, **kwargs: (
        calls.append(args) or real_show(*args, **kwargs)
    )
    selection = [history_repo['a'], history_repo['middle'], history_repo['tmp']]

    widget.commits_selected([_fake_commit(oid) for oid in selection])

    assert len(calls) == 1
    assert list(calls[0]) == selection
```

Add the missing import for `dag`. Anchor:

```bash
grep -n "^from cola import icons$" test/widgets_history_filelist_test.py
```

Insert **directly below it**:

```python
from cola.models import dag
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -25
```

**Expected: 7 of the 11 new tests red, 4 green.** The exact split is measured:

| Test | today | Reason |
|---|---|---|
| `..._two_selected_commits_list_the_files_of_both` | **RED** | `UnboundLocalError` |
| `..._non_contiguous_selection_ignores_unselected_commits` | **RED** | `UnboundLocalError` |
| `..._selection_including_the_root_commit_lists_its_files` | **RED** | **`AssertionError: assert [] == ['A', 'B', 'middle.txt']`** — no exception is raised here, because `root~` fails and the `status != 0` early return fires first |
| `..._file_added_and_deleted_across_the_selection_stays_listed` | **RED** | `UnboundLocalError` |
| `..._file_touched_twice_is_listed_once_with_summed_counts` | **RED** | `UnboundLocalError` |
| `..._single_commit_selection_is_unchanged` | **green** | characterization |
| `..._unknown_revision_leaves_the_list_empty` | **green** | characterization |
| `..._stage_pseudo_commit_lists_the_staged_files` | **green** | characterization |
| `..._worktree_pseudo_commit_lists_the_modified_files` | **green** | characterization |
| `..._commit_with_stage_and_worktree_lists_all_of_them` | **RED** | `UnboundLocalError` |
| `..._one_git_show_serves_the_whole_selection` | **RED** | `UnboundLocalError` |

Under Python ≥ 3.11 the `UnboundLocalError` reads:

```
UnboundLocalError: cannot access local variable 'oid' where it is not associated with a value
```

and under older interpreters `local variable 'oid' referenced before assignment` (trap **F8**). It
comes from `cola/widgets/filelist.py`, the line reading `if oid in (dag.STAGE, dag.WORKTREE):`.

> **The four green tests are characterization tests** — they pin down what is already true today
> and must stay true after Task 2. They are **not a broken RED**. If any of the seven red ones is
> green, or any of the four green ones is red: **stop and report.**

### Step 2.2 (GREEN) — Replace `commits_selected`

**Anchor:**

```bash
grep -n "    def commits_selected(self, commits):" cola/widgets/filelist.py
```

**Expected:** exactly **one** hit. Starting at that line, the following block stands **verbatim**
in the file — the complete `commits_selected` method. Print it to check:

```bash
sed -n '/^    def commits_selected(self, commits):$/,/^        self.list_files(numstat_rows, status_by_path=status_by_path)$/p' cola/widgets/filelist.py
```

**Expected:** exactly this block, 83 lines:

```python
    def commits_selected(self, commits):
        self.commits = list(commits)
        if not commits:
            self.clear()
            return

        git = self.context.git

        if len(commits) > 1:
            # Get a list of changed files for a commit range.
            start_oid = commits[0].oid
            end = commits[-1].oid
            start = start_oid + '~'
            if end == dag.STAGE:
                status, out, _ = git.diff(
                    start,
                    cached=True,
                    z=True,
                    numstat=True,
                    raw=True,
                    no_renames=True,
                )
            elif end == dag.WORKTREE:
                if start_oid == dag.STAGE:
                    status, out, _ = git.diff(
                        z=True, numstat=True, raw=True, no_renames=True
                    )
                else:
                    status, out, _ = git.diff(
                        start,
                        z=True,
                        numstat=True,
                        raw=True,
                        no_renames=True,
                    )
            else:
                status, out, _ = git.diff(
                    start,
                    end,
                    z=True,
                    numstat=True,
                    raw=True,
                    no_renames=True,
                )
        else:
            # Get the list of changed files in a single commit.
            commit = commits[0]
            oid = commit.oid
            # NOTE: The output from "git diff-files --numstat -z" is not equivalent
            # to the output of "git show --numstat -z". "git diff-files" does not
            # emit a NULL separator between each entry. That's why we use the
            # default output (without "-z") and split on newline instead.
            # This is also true for "git diff-index" as well.
            if oid == dag.STAGE:
                status, out, _ = git.diff_index(
                    'HEAD', cached=True, numstat=True, raw=True, _readonly=True
                )
            elif oid == dag.WORKTREE:
                status, out, _ = git.diff_files(numstat=True, raw=True, _readonly=True)
            else:
                status, out, _ = git.show(
                    oid,
                    format='',
                    numstat=True,
                    raw=True,
                    no_renames=True,
                    z=True,
                    _readonly=True,
                )

        if status != 0:
            self.list_files([])
            return

        # git show uses -z; git diff-index / git diff-files do not.
        # git diff above always uses -z.
        if oid in (dag.STAGE, dag.WORKTREE):
            separator = '\n'
        else:
            separator = '\0'

        status_by_path, numstat_rows = parse_status_and_numstat(out, separator)
        self.list_files(numstat_rows, status_by_path=status_by_path)
```

Replace **exactly that block** — nothing before it, nothing after it; the blank line below it and
the following line `    def list_files(self, files_log, status_by_path=None):` stay untouched —
with:

```python
    def commits_selected(self, commits):
        self.commits = list(commits)
        if not commits:
            self.clear()
            return

        status_by_path = {}
        numstat_rows = []
        for out, separator in self._changed_file_output(commits):
            parsed_status, parsed_rows = parse_status_and_numstat(out, separator)
            status_by_path.update(parsed_status)
            numstat_rows.extend(parsed_rows)

        merged_rows = merge_numstat_rows(numstat_rows)
        self.list_files(merged_rows, status_by_path=status_by_path)

    def _changed_file_output(self, commits):
        """Yield an (output, separator) pair for every source in the selection.

        The list shows the union of what the user picked, so all real commits
        are described by a single "git show" over every one of them. STAGE and
        WORKTREE are not revisions and need their own commands. A source that
        fails is skipped rather than emptying the whole list.
        """
        git = self.context.git
        oids = [
            commit.oid
            for commit in commits
            if commit.oid not in (dag.STAGE, dag.WORKTREE)
        ]
        if oids:
            # "git show" takes several revisions and emits one raw+numstat
            # block per revision, in the order given -- the same shape it
            # emits for a single one.
            status, out, _ = git.show(
                *oids,
                format='',
                numstat=True,
                raw=True,
                no_renames=True,
                z=True,
                _readonly=True,
            )
            if status == 0:
                yield out, '\0'
        # NOTE: The output from "git diff-files --numstat -z" is not equivalent
        # to the output of "git show --numstat -z". "git diff-files" does not
        # emit a NULL separator between each entry. That's why we use the
        # default output (without "-z") and split on newline instead.
        # This is also true for "git diff-index" as well.
        selected = {commit.oid for commit in commits}
        if dag.STAGE in selected:
            status, out, _ = git.diff_index(
                'HEAD', cached=True, numstat=True, raw=True, _readonly=True
            )
            if status == 0:
                yield out, '\n'
        if dag.WORKTREE in selected:
            status, out, _ = git.diff_files(numstat=True, raw=True, _readonly=True)
            if status == 0:
                yield out, '\n'
```

> **What disappears with it:** the whole `if len(commits) > 1:` branch with its four `git.diff`
> variants, the `status != 0` early return and the separator choice via `oid`. The
> `UnboundLocalError` goes away not because `oid` gets assigned but because the variable no longer
> exists.
>
> **What stays:** the `NOTE` comment about `diff-files`/`diff-index` — it justifies the `'\n'` and
> belongs at this spot now.
>
> **No type annotations** (trap **F9**). No new import: `dag` is already on line 11.

### Verification

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -3
```

**Expected:** all passed.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py test/widgets_main_history_test.py test/diff_debounce_test.py 2>&1 | tail -3
```

**Expected:** all passed. These three files hold the tests that also use `commits_selected` — in
particular the call counter from trap **F6**.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 21 passed, 0 failed.

### Formatting

```bash
garden fmt
```

Without `garden`, the substitutes from the table in §0.

> The code above is **hand-set to 88 columns but was not checked with `cercis`** — the tool was not
> installed when the plan was written. `garden fmt` may rewrap it; run the tests again afterwards.

### Commit

```bash
git add -A && git commit -m "fix: list the files of every selected commit

Selecting more than one commit raised UnboundLocalError: the separator was
chosen from a variable that only the single-commit branch assigned. The branch
is gone. The file list now shows the union of the files the selected commits
touch, fetched with one 'git show' over all of them, instead of a diff of the
range between the oldest and the newest.

The range was wrong in three ways a union is not: it listed files from commits
between two non-adjacent selections, it hid changes that cancelled out inside
the range, and it showed nothing at all whenever the root commit was selected,
because there is no commit before it."
```

---

## Task 3 — Documentation

### Step 3.1 — `references/fork-history.md`

Anchor:

```bash
grep -n "^## " .claude/skills/project-brief/references/fork-history.md
```

Insert the new section **after** the last numbered section and **directly before** the line
`## Where the fork's tests live`.

**Which number?** Exactly one of the two rows below applies — decide from the `grep` output above,
without doing arithmetic:

| Last numbered section in the file | Then the new section is called |
|---|---|
| `## 5. Mouse actions and HEAD marking in the history` | `## 6. Multi-commit selection lists the union of the touched files` |
| `## 6. Commit description above the file list` | `## 7. Multi-commit selection lists the union of the touched files` |

If it says anything else: **stop and report.** Replace `<N>` below with the number decided that
way:

```markdown
## <N>. Multi-commit selection lists the union of the touched files

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
```

Also extend the test list at the end of that file:

```markdown
- `test/widgets_history_filelist_test.py` additionally holds the table test for
  `merge_numstat_rows()` and the multi-commit selection tests against a real repository
  (fixture `history_repo`).
```

### Step 3.2 — `references/gotchas.md`

Anchor:

```bash
grep -n "^## Git output$" -A 2 .claude/skills/project-brief/references/gotchas.md
grep -n "^## Icons$" .claude/skills/project-brief/references/gotchas.md
```

**Expected:** exactly **one** hit each, and `## Icons` sits **after** `## Git output`. Insert the
following text **at the end of the `## Git output` section**, that is **directly before** the
`## Icons` line (with one blank line before and after):

```markdown
**`git show` takes more than one revision.** `git show <a> <b> … --format= --numstat --raw
--no-renames -z` emits one raw+numstat block per revision, in the order given, in exactly the
shape `parse_status_and_numstat` already parses. It is the cheapest way to describe a whole
selection, and it works for a root commit — unlike `<root>~`, which does not resolve.

**`--numstat -z` does not NUL-separate the numstat fields.** Despite "use NULs as output field
terminators", the row stays `adds<TAB>dels<TAB>path`; only the record ends with NUL. Binary files
carry `-` instead of a count in both fields.

**`FileWidget.commits_selected` must not grow a git call per commit.**
`test_public_selection_reaches_all_standalone_consumers_synchronously`
(`test/widgets_dag_history_test.py`) monkeypatches `git.show` and asserts it ran exactly once.
```

### Step 3.3 — Update the note in the description-panel plan

`docs/plans/2026-08-01-commit-description-panel.md` lists the bug fixed here as trap **F8** and
says it will be fixed separately.

Check that plan's status first:

```bash
head -3 docs/plans/2026-08-01-commit-description-panel.md
```

If it says `status: open`, append to the end of its F8 row:

```markdown
**Fixed by `docs/plans/2026-07-31-history-multi-commit-file-list.md`.** That plan's integration tests may select several commits from now on; the description still shows `selection[-1]`.
```

> The surrounding table is German because that plan predates the English rule. Write the new
> sentence in **English** anyway — new material is English even inside an old German document.
> Matching the surrounding language is what the rule exists to stop.

If it is already `status: completed`, **change nothing** — completed plans are reference material
and are not rewritten (`docs/plans/README.md`).

### Step 3.4 — `SKILL.md`

Anchor:

```bash
grep -n "work packages have shipped" .claude/skills/project-brief/SKILL.md
```

**Expected:** exactly **one** hit. Exactly one of the two lines below stands there — replace it
with the one next to it, without doing arithmetic:

| It says | Replace with |
|---|---|
| `Five work packages have shipped:` | `Six work packages have shipped:` |
| `Six work packages have shipped:` | `Seven work packages have shipped:` |

If it says anything else: **stop and report.**

Also extend the enumerating sentence that runs over several lines, at its end, with
", and the multi-commit file list in the history" — directly before the closing full stop.

### Step 3.5 — Mark the plan as done

Set this plan's frontmatter to `status: completed` and add `completed_at`, `plan_commit`,
`implementation_branch`, `implementation_head`, `ci_run` and `manual_verification` — as described
in `docs/plans/README.md`. Move this plan's row in the table of `docs/plans/README.md` from
**open** to **completed**.

### Verification

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** green, unchanged.

```bash
garden check/fmt && garden check/pyupgrade && garden check/mypy
```

Without `garden`, the same checks one by one:

```bash
cercis --check bin bin/git-* cola test extras/sphinxtogithub
isort --check --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* cola test extras/sphinxtogithub
pyupgrade --py39-plus bin/git-* bin/*.py cola/*.py cola/*/*.py
python3 -m mypy --config-file pyproject.toml bin cola
```

**Expected:** no findings. A missing tool is not a reason to abort: **note which check did not
run**, and say so in the final report.

### Commit

```bash
git add -A && git commit -m "docs: document the multi-commit file list"
```

---

## Manual acceptance

```bash
garden run
```

Without `garden` — or in an environment without a display — through the launcher in the
repository:

```bash
env3/bin/python bin/git-fanta
```

1. Select two adjacent commits in the history: the file list shows the files of **both**, one row
   per file. (Before: empty panel, a crash in the log.)
2. Select two **non**-adjacent commits with Ctrl+click: **only** their files appear, nothing from
   the commits in between.
3. Include the **oldest** commit of the history in the selection: its files are there. (Before:
   empty.)
4. Double-click a file touched by several selected commits: the diff window opens as usual.
5. With uncommitted changes present, select `STAGE` and `WORKTREE` together with a commit: all
   three sources appear in one list.
6. The same in the standalone DAG window (`Files` dock).
7. Click a row in the rebase sequence editor: unchanged, exactly one commit is selected there.

> **In an environment without a display this section does not apply.** Then: points 1, 2, 3 and 5
> are covered by the tests from Task 2; **4, 6 and 7 are not** — a double-click over a multi-commit
> selection, the DAG window and the sequence editor have no test coverage for this case. **Write it
> that way in the final report, do not present it as "checked".**
