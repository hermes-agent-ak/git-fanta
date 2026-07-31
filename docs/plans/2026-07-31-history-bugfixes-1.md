---
status: open
---

# Four fixes: file diff over a multi-commit selection, chip colors, remote checkout, message box size

**Created:** 2026-07-31
**Branch:** Commit the tasks onto whatever branch is checked out at the start. **Never onto
`main`** — the pattern for feature work is `tree-ui/<agent>/<model>/<topic>`. Check before Task 1:
`git rev-parse --abbrev-ref HEAD`. If it says `main`, create a branch first. This plan does **not**
create one.
**Affects:** `cola/gitcmds.py`, `cola/widgets/diff.py`, `cola/widgets/dag.py`,
`cola/widgets/standard.py`. The message box in Task 4 is shared by every confirmation and error
dialog in the application.

---

## 0. How to read this plan

This plan is written so that it can be executed **without prior knowledge and without making any
decisions of your own**.

- **Do the tasks strictly in order 0 → 5.** Skip nothing. The four fixes are independent; the
  order only keeps the suite green after every step.
- **One task = one commit.** The commit message is written out verbatim at the end of each task.
  Use it as it stands.
- **Every task has RED → GREEN → VERIFICATION.** Where a RED step names an expected error, the
  actual output must match it. If it does not: **stop and report**, do not continue.
- **Line numbers are orientation, not truth.** Every edit is preceded by a `grep` that finds the
  anchor. Use the `grep`, not the line number.
- **The full test suite is green after every task.**
- If a command fails and the plan names no way out: **stop and report.**

**Language.** Everything written into the repository is **English**: code, comments, docstrings,
test names, commit messages, documentation. Some files still contain German from before
2026-07-31 — do not match them, and do not translate them as a side effect of this plan.

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

Standard test command:

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test
```

---

## 1. What is being fixed

| # | Report | Root cause (measured, §2) |
|---|---|---|
| **1** | With several commits selected, double-clicking a file that the newest commit did not touch shows no diff — only the newest commit's title. | `CommitFileDiffWindow.set_commit_file` shows a **range** diff `commits[0]~..commits[-1]` for the file, and labels it with `commits[-1]`. The range is empty whenever the file's change cancels out or `commits[0]` is the root commit. |
| **2** | The local-branch chip color collides with the blue background of the selected row. | The chip used for local branches is `chip_head`, mixed **76 % from `highlight`** — the very color the selected row is painted in. Measured contrast against the selected row: **1.41** (light) / **1.33** (dark). |
| **3** | Double-clicking a commit that only carries a remote branch detaches HEAD instead of creating the local branch. | `CommitTreeWidget.checkout_commit` looks only at `commit.branches`, which holds **local** branches. A remote-only commit has `branches == []` and falls through to the detached-checkout path. |
| **4** | The confirmation dialog after creating a branch is far too large, and the same box appears at the same size everywhere else. | `MessageBox.set_initial_size` hard-codes `defs.dialog_w` × `defs.msgbox_h` (720 × 128, before HiDPI scaling) regardless of content, and never centres on its parent. |

## 2. Root causes — all measured

### 2.1 The file diff uses a range (issue 1)

`cola/widgets/diff.py:2295` `set_commit_file` sets `oid_start = commits[0]` / `oid_end =
commits[-1]` and then calls `files_selected([filename])`, which runs
`set_diff_range(commits[0].oid, commits[-1].oid, filename=…)` →
`DiffRangeTask` → `git diff commits[0]~ commits[-1] -- filename`.

That is the range semantics the file **list** deliberately dropped in
`docs/plans/2026-07-31-history-multi-commit-file-list.md`. The list now shows the union, so it can
offer a file that the range diff renders as empty. The window still fills in the header from
`commits[-1]`, which is exactly the reported symptom: the newest commit's title with nothing
below it.

**The fix needs to know which commit actually touched the file.** Measured through the project's
own git wrapper:

```
ctx.git.rev_list(*oids, '--', path, max_count=1, no_walk=True, _readonly=True)
```

| Selection / path | Result |
|---|---|
| `C1 C2 C3` / `a.txt` (touched by C1 and C3) | `C3` — the **newest** |
| `C1 C2` / `a.txt` | `C1` |
| `C2` / `a.txt` (untouched) | empty string, status 0 |
| `C1` (root commit) / `a.txt` | `C1` |

> `--no-walk` considers **only the listed commits** and does not walk their ancestors. Its default
> ordering is `sorted` = reverse chronological, so `--max-count=1` yields the newest. Verified
> with distinct commit dates — with identical timestamps the order degenerates to the order given,
> which is what made an earlier measurement look wrong.

### 2.2 The local-branch chip is built out of the selection color (issue 2)

`cola/widgets/dag.py:1341-1346` picks the chip fill:

```python
brush = style.chip_other
if tag == _HEAD_REF or tag.startswith(_TAGS_PREFIX):
    brush = style.chip_remote
elif tag.startswith(_HEADS_PREFIX):
    brush = style.chip_head
```

**The names are misleading and this is trap F3.** `heads/…` is a **local** branch and gets
`chip_head`; `chip_other` is the fallback that remote branches land in.

`chip_head` is `_mix_color(highlight, base, 0.24)` — 76 % of the highlight color. The selected row
is painted in `highlight`. Measured contrast of each chip fill against the row it sits on:

| Chip fill | used for | vs unselected row | vs **selected** row (light) | vs **selected** row (dark) |
|---|---|---|---|---|
| `chip_other` | remote branches | 1.08 | 3.40 | 2.91 |
| `chip_remote` | `HEAD` and tags | 1.70 | 2.17 | 1.97 |
| `chip_head` | **local branches** | 2.61 | **1.41** | **1.33** |

1.41 means the chip and the row are very nearly the same blue — the reported collision, and it is
the worst of the three by construction.

Two candidate fixes were measured and **rejected**:

- Re-deriving the chips from the actual row background with the same mixing formula gives
  contrasts of 1.25–2.9 — worse than today.
- Forcing every chip to clear **3.0** against both row states pushes all three to the same
  luminance.

The accepted fix nudges each fill only as far as needed to clear a **2.5** floor against the
unselected *and* the selected row background. Measured result:

| Palette | remote | HEAD/tags | local |
|---|---|---|---|
| light | `#f6f6f6` → `#3d3d3d` | `#a8cbe1` → `#3b474f` | `#62a8d4` → `#274355` |
| dark | `#232323` → `#b2b2b2` | `#294153` → `#a9b3ba` | `#2b5c80` → `#a0b5c6` |

Measured with the implementation from Task 2 in place, the worst fill contrast per palette is:

| Palette | on the selected row | on the unselected row | distinct hues left |
|---|---|---|---|
| light | 2.58 | 2.61 | 2 of 3 |
| dark | 2.60 | 2.63 | 2 of 3 |
| solarized | 2.54 | 2.51 | 3 of 3 |

> Two of three hues surviving is expected and acceptable: in a palette whose base and highlight
> are both near-neutral, two chips legitimately land on the same hue and are told apart by
> lightness. All three collapsing would mean the semantics are gone — that is what the test
> asserts against.

> **The three stay distinguishable.** Their *contrast ratio* to one another drops to ~1.0, but
> contrast ratio is luminance-only; equal luminance is exactly what the floor forces. Mixing
> towards pure black or white preserves hue, so the three remain `#3d3d3d` grey, `#3b474f`
> blue-grey and `#274355` blue. **Distinctness is asserted on hue, not on contrast ratio** —
> see trap **F4**.

### 2.3 A remote-only commit has no local branch (issue 3)

`cola/models/dag.py:192` `add_label` files `refs/heads/X` into `commit.branches` and everything
else into `commit.tags`, prefix-stripped. Measured on a clone whose `feature` branch exists only
on the remote:

```
oid=cd54d228 summary='base'         branches=['main'] tags=['HEAD', 'heads/main', 'remotes/origin/main']
oid=4f3a4f4c summary='feature work' branches=[]       tags=['remotes/origin/feature']
```

`checkout_commit` (`cola/widgets/dag.py:315`) sees `branches == []`, skips every branch path and
lands on `cmds.Checkout(context, [commit.oid])` — a detached HEAD. The remote branch name is
right there in `commit.tags`.

**How to create the local branch — measured, and the obvious way is wrong:**

| Command | Result |
|---|---|
| `git checkout feature` (DWIM) | works **by default**, creates `feature` tracking `origin/feature` |
| the same with `checkout.guess=false` | `error: pathspec 'feature' did not match any file(s) known to git` |
| the same when a **local** `feature` already exists at another commit | **silently checks out the wrong commit** |
| `git checkout -b feature --track origin/feature` | creates and tracks; fails loudly if the name is taken |

So `cmds.CheckoutBranch` (which runs plain `git checkout <name>`) must **not** be used here. The
explicit form is trap **F5**.

### 2.4 The message box has a hard-coded size (issue 4)

`cola/widgets/standard.py:1114`:

```python
    def set_initial_size(self):
        width = defs.dialog_w
        height = defs.msgbox_h
        self.resize(width, height)
```

`defs.dialog_w = scale(720)`, `defs.msgbox_h = scale(128)` (`cola/widgets/defs.py:50`, `:53`),
and `scale()` multiplies by the HiDPI factor. Every `confirm()`, `critical()` and `information()`
call goes through this one class, which is why the same oversized box appears everywhere. Nothing
positions the dialog, so the window manager places it.

## 3. Non-goals

- **No change to the file list or to `merge_numstat_rows`.** Issue 1 lives entirely in the diff
  window.
- **No new "which commits touched this file" cache.** The lookup runs once per double-click, an
  explicit user action.
- **No redesign of the chip shapes, sizes or of `_distinct_chip_backgrounds`.** Only the fill is
  nudged, and only when it fails the floor.
- **No new preference** for any of the four behaviours.
- **No change to `cmds.CheckoutBranch`** — other callers rely on its current meaning.
- **No responsive re-layout of `MessageBox` contents.** Task 4 changes the initial size and the
  position only; the layout itself already stretches.
- **No translation of German text that already exists** in `cola/widgets/diff.py` or elsewhere.

## 4. Traps — all empirically verified

| # | Trap | Evidence |
|---|---|---|
| **F1** | **`--no-walk` ordering depends on commit *dates*, not on argument order.** Its default is `sorted` (reverse chronological), so `--max-count=1` gives the newest. With identical timestamps it degenerates to argument order — which makes a naive probe in a script-built repo look like it preserves input order. | Measured twice: same-second commits → argument order; distinct `GIT_COMMITTER_DATE` → newest first regardless of argument order |
| **F2** | **`git rev-list` returns status 0 and an empty string when no listed commit touched the path.** Absence is not an error and must not be treated as one. | Measured: `rev_list(C2, '--', 'a.txt', max_count=1, no_walk=True)` → `status=0`, `out=''` |
| **F3** | **The chip color names do not mean what they say.** `heads/…` (a **local** branch) is painted with `chip_head`; `chip_other` is the fallback that **remote** branches fall into; `chip_remote` paints `HEAD` and tags. Renaming them is out of scope, but reading the code as if the names were accurate leads to fixing the wrong chip. | `cola/widgets/dag.py:1341-1346` together with `_HEADS_PREFIX = 'heads/'` (`:757`) |
| **F4** | **Contrast ratio is luminance-only, so it is useless for asserting that two chips look different.** Forcing three fills to the same contrast floor necessarily puts them at the same luminance, which reads as "contrast 1.0" between them while they remain clearly different hues. Assert distinctness on **hue**. | Measured: after the fix the light-theme fills are `#3d3d3d`, `#3b474f`, `#274355` — mutual contrast 1.04–1.13, hues plainly different |
| **F5** | **Plain `git checkout <name>` is not a safe way to materialise a remote branch.** It depends on `checkout.guess`, and it silently checks out an unrelated local branch of the same name. | Measured, all three cases — see the table in §2.3 |
| **F6** | **`add_label` drops `…/HEAD`.** `refs/remotes/origin/HEAD` never reaches `commit.tags`, so `remotes/origin/HEAD` cannot be mistaken for a branch. | `cola/models/dag.py:202-203`; measured: tags were `['HEAD', 'heads/main', 'remotes/origin/main']`, no `remotes/origin/HEAD` |
| **F7** | **`_draw_labels` is called twice**, once to paint (`cola/widgets/dag.py:1295`) and once with `painter=None` purely to measure width (`:1381`). The measuring call must keep working, so every new parameter needs a default and must only be read inside `if painter is not None:`. | `cola/widgets/dag.py:1295`, `:1381` |
| **F8** | **`cola/widgets/diff.py` does not import the dag model.** Issue 1 needs `dag.STAGE` / `dag.WORKTREE`. `cola/models/dag.py` imports nothing from `cola/widgets/`, so the import is safe and not a cycle. | `grep -n "^from\|^import" cola/widgets/diff.py` → no `models.dag`; `grep -n widget cola/models/dag.py` → no hits |
| **F9** | **`cmds.do(cls, *args, **opts)` forwards keyword arguments**, so `checkout_branch=True` can be passed through it. | `cola/cmds.py:3587-3593` |
| **F10** | **`_REMOTES_PREFIX = 'remotes/'` already exists** at `cola/widgets/dag.py:755`. Do not add a second constant. | `grep -n "_REMOTES_PREFIX" cola/widgets/dag.py` |
| **F11** | **`pytest.ini` sets `--doctest-modules`.** A `>>>` in a new docstring becomes a test; a `\t` is a real tab. | `pytest.ini:3` |
| **F12** | **`cola/widgets/filelist.py` and `cola/widgets/dag.py` carry no type annotations in the code touched here.** New helpers follow the surrounding module: `cola/gitcmds.py` **does** annotate, `cola/widgets/dag.py` annotates only in places. Match the immediate neighbours of the anchor, do not introduce `X \| None` where the file has no `from __future__ import annotations`. | `grep -n "from __future__" cola/gitcmds.py cola/widgets/dag.py cola/widgets/diff.py cola/widgets/standard.py` |

## 5. What already exists and is reused (do not rebuild)

| Exists | Where | Role in this plan |
|---|---|---|
| `CommitDiffWidget.set_diff_oid(oid, filename=None)` | `cola/widgets/diff.py:2072` | **Is** the single-commit file diff. Task 1 only has to call it with the right oid. |
| `_color_contrast`, `_color_luminance`, `_mix_color`, `_opaque_color` | `cola/widgets/dag.py:936`, `:926`, `:911`, `:904` | **Are** the color maths for Task 2. No new color helpers beyond the one nudge function. |
| `_REMOTES_PREFIX` | `cola/widgets/dag.py:755` | The `remotes/` prefix for Task 3. |
| `cmds.Checkout(context, argv, checkout_branch=True)` | `cola/cmds.py` | **Is** the checkout command. Task 3 passes an explicit argv; it does **not** add a new command class. |
| `qtutils.desktop_size()` | used at `cola/widgets/standard.py:1140` | Screen size for clamping in Task 4. |
| `app_context` fixture | `test/helper.py:85` | Real temporary git repository for every test in this plan. |
| `test/gitcmds_test.py`, `test/widgets_commit_file_diff_test.py`, `test/widgets_history_checkout_test.py`, `test/widgets_dag_history_test.py`, `test/widgets_standard_test.py` | `test/` | **The five files this plan extends.** Each already has the fixtures it needs; copy nothing between them. |

---

# TASKS

## Task 0 — Make sure the tests run

> **Blocking. No commit.**

```bash
python3 -m pytest --version 2>&1 | head -1
ls -d env3 2>/dev/null && env3/bin/python -m pytest --version 2>&1 | head -1
command -v garden cercis isort pyupgrade mypy
python3 -c "import qtpy; print('qtpy', qtpy.API_NAME)"
```

If **no** interpreter has `pytest`, try one of the two routes:

```bash
garden dev/virtualenv && garden dev
```

```bash
python3 -m venv --system-site-packages env3 && env3/bin/python -m ensurepip --upgrade && env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

If that fails too: **STOP and report.** This plan is TDD-structured and cannot be executed without
running tests.

### Verification

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -5
```

**Expected:** `NNN passed`, no `failed`, no `error`. **Note `NNN` as the baseline.**

---

## Task 1 — The file diff shows the commit that touched the file

**Goal:** double-clicking a file in a multi-commit selection shows that file's diff from the
newest selected commit that actually changed it.

### Step 1.1 (RED) — Test the lookup helper

Append to `test/gitcmds_test.py`:

```python
def test_commit_touching_path_returns_the_newest_toucher(app_context):
    """Of the given commits, the newest one that changed the path wins."""
    first = _commit_file(app_context, 'a.txt', 'one\n', '2026-01-01T10:00:00')
    middle = _commit_file(app_context, 'b.txt', 'two\n', '2026-01-02T10:00:00')
    last = _commit_file(app_context, 'a.txt', 'three\n', '2026-01-03T10:00:00')

    result = gitcmds.commit_touching_path(app_context, [first, middle, last], 'a.txt')

    assert result == last


def test_commit_touching_path_ignores_commits_outside_the_list(app_context):
    """A commit that is not in the list never wins, even if it is newer."""
    first = _commit_file(app_context, 'a.txt', 'one\n', '2026-01-01T10:00:00')
    middle = _commit_file(app_context, 'b.txt', 'two\n', '2026-01-02T10:00:00')
    _commit_file(app_context, 'a.txt', 'three\n', '2026-01-03T10:00:00')

    result = gitcmds.commit_touching_path(app_context, [first, middle], 'a.txt')

    assert result == first


def test_commit_touching_path_handles_the_root_commit(app_context):
    """The root commit has no parent and is still a valid answer."""
    root = _commit_file(app_context, 'a.txt', 'one\n', '2026-01-01T10:00:00')

    assert gitcmds.commit_touching_path(app_context, [root], 'a.txt') == root


def test_commit_touching_path_returns_none_when_nothing_touched_it(app_context):
    """git exits 0 with empty output; absence is not an error (trap F2)."""
    first = _commit_file(app_context, 'a.txt', 'one\n', '2026-01-01T10:00:00')

    assert gitcmds.commit_touching_path(app_context, [first], 'b.txt') is None


@pytest.mark.parametrize(('oids', 'path'), (([], 'a.txt'), (['a' * 40], '')))
def test_commit_touching_path_without_usable_input(app_context, oids, path):
    """No commits or no path means no lookup and no git call."""
    assert gitcmds.commit_touching_path(app_context, oids, path) is None
```

Add the helper the tests use. Append it **above** the tests you just added:

```python
def _commit_file(context, path, content, date):
    """Commit `content` into `path` at a fixed date and return the oid.

    The dates matter: "git rev-list --no-walk" orders by commit time, and
    same-second commits would make the ordering assertions meaningless.
    """
    helper.write_file(path, content)
    env = {'GIT_AUTHOR_DATE': date, 'GIT_COMMITTER_DATE': date}
    context.git.add(path)
    context.git.commit('-m', f'touch {path}', _add_env=env)
    _status, out, _err = context.git.rev_parse('HEAD')
    return out.strip()
```

`test/gitcmds_test.py` already imports `helper`, `gitcmds` and `app_context`. It does **not**
import `pytest`, which the parametrised test needs. Anchor:

```bash
grep -n "^import os$" test/gitcmds_test.py
```

Insert **two lines below it** (blank line, then the import), so the third-party group stays
separate from the standard library:

```python
import pytest
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/gitcmds_test.py 2>&1 | tail -8
```

**Expected:** all six new tests fail with

```
AttributeError: module 'cola.gitcmds' has no attribute 'commit_touching_path'
```

To confirm beforehand: `grep -c commit_touching_path cola/gitcmds.py` → `0`.

### Step 1.2 (GREEN) — Add the helper

**Anchor:**

```bash
grep -n "^def rev_list_range" cola/gitcmds.py
```

**Expected:** exactly **one** hit. Insert **directly before it**:

```python
def commit_touching_path(context, oids, path):
    """Return the newest of `oids` that changed `path`, or None.

    "git rev-list --no-walk" looks at exactly the commits it is given and does
    not walk their ancestors, so a commit that is not in `oids` can never be the
    answer. Its default ordering is by commit date, newest first, which is why
    --max-count=1 yields the newest toucher rather than an arbitrary one.

    Returns None when no listed commit changed the path. git reports that as
    exit status 0 with empty output, so it is not an error.
    """
    if not oids or not path:
        return None
    status, out, _ = context.git.rev_list(
        *oids, '--', path, max_count=1, no_walk=True, _readonly=True
    )
    if status != 0:
        return None
    return out.strip() or None


```

### Step 1.3 (RED) — Test the diff window

Append to `test/widgets_commit_file_diff_test.py`:

```python
def test_double_click_shows_the_commit_that_touched_the_file(
    qapp, app_context, managed_qobject
):
    """The newest selected commit that changed the file supplies the diff."""
    window = _window(app_context, managed_qobject)
    older = _fake_commit('a' * 40, summary='older')
    newer = _fake_commit('b' * 40, summary='newer')
    asked = []
    app_context.git.rev_list = lambda *args, **kwargs: (
        asked.append(args) or (0, 'a' * 40 + '\n', '')
    )
    shown = []
    window.diffwidget.set_diff_oid = lambda oid, **kwargs: shown.append((oid, kwargs))

    window.set_commit_file([older, newer], 'src/a.py')

    assert shown == [('a' * 40, {'filename': 'src/a.py'})]
    assert window.diffwidget.oid == 'a' * 40


def test_double_click_never_asks_for_a_range(qapp, app_context, managed_qobject):
    """A range diff is what hid the file in the first place - it must not run."""
    window = _window(app_context, managed_qobject)
    app_context.git.rev_list = lambda *args, **kwargs: (0, 'a' * 40 + '\n', '')
    ranges = []
    window.diffwidget.set_diff_range = lambda *args, **kwargs: ranges.append(args)
    window.diffwidget.set_diff_oid = lambda oid, **kwargs: None

    window.set_commit_file([_fake_commit('a' * 40), _fake_commit('b' * 40)], 'src/a.py')

    assert ranges == []
    assert window.diffwidget.oid_start is None
    assert window.diffwidget.oid_end is None


def test_double_click_titles_the_window_with_the_touching_commit(
    qapp, app_context, managed_qobject
):
    """The header must name the commit whose diff is on screen, not the newest."""
    window = _window(app_context, managed_qobject)
    older = _fake_commit('a' * 40, summary='older')
    newer = _fake_commit('b' * 40, summary='newer')
    app_context.git.rev_list = lambda *args, **kwargs: (0, 'a' * 40 + '\n', '')
    window.diffwidget.set_diff_oid = lambda oid, **kwargs: None

    window.set_commit_file([older, newer], 'src/a.py')

    assert ('a' * 40)[:12] in window.windowTitle()


def test_double_click_falls_back_to_the_newest_commit(
    qapp, app_context, managed_qobject
):
    """No answer from git means the previous behaviour: use the newest commit."""
    window = _window(app_context, managed_qobject)
    app_context.git.rev_list = lambda *args, **kwargs: (0, '', '')
    shown = []
    window.diffwidget.set_diff_oid = lambda oid, **kwargs: shown.append(oid)

    window.set_commit_file([_fake_commit('a' * 40), _fake_commit('b' * 40)], 'src/a.py')

    assert shown == ['b' * 40]


def test_double_click_on_a_single_commit_asks_no_question(
    qapp, app_context, managed_qobject
):
    """Characterization: one commit needs no lookup, it is the answer."""
    window = _window(app_context, managed_qobject)
    asked = []
    app_context.git.rev_list = lambda *args, **kwargs: (
        asked.append(args) or (0, '', '')
    )
    shown = []
    window.diffwidget.set_diff_oid = lambda oid, **kwargs: shown.append(oid)

    window.set_commit_file([_fake_commit('a' * 40)], 'src/a.py')

    assert asked == []
    assert shown == ['a' * 40]
```

Before writing them, check what the file already provides:

```bash
grep -n "^def _fake_commit\|^def qapp\|^def managed_qobject\|CommitFileDiffWindow" test/widgets_commit_file_diff_test.py | head
```

If `_fake_commit` is missing or has a different signature, **stop and report** rather than
inventing a second one.

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_commit_file_diff_test.py 2>&1 | tail -12
```

**Expected:** four of the five fail. `..._on_a_single_commit_asks_no_question` is a
**characterization test** and is **green already** — today a single commit takes the
`else` branch and never calls `rev_list`. The other four fail on the range behaviour, most
visibly as

```
AssertionError: assert [] == [('aaaa…', {'filename': 'src/a.py'})]
```

If the characterization test is red, or any of the other four is green: **stop and report.**

### Step 1.4 (GREEN) — Use the touching commit

**Anchor 1 — the import.**

```bash
grep -n "^from ..models import main$" cola/widgets/diff.py
```

If that line exists, insert **directly above it**; otherwise insert directly above the first
`from ..` line that sorts after `models`. The new line is:

```python
from ..models import dag
```

Then run `garden fmt` at the end of the task and let isort settle the position.

**Anchor 2 — the method.**

```bash
grep -n "    def set_commit_file(self, commits, filename):" cola/widgets/diff.py
```

**Expected:** exactly **one** hit. Print the block to be replaced:

```bash
sed -n '/^    def set_commit_file(self, commits, filename):$/,/^            % {.filename.: filename, .oid.: commit.oid\[:12\]}$/p' cola/widgets/diff.py
```

Replace the whole method — from its `def` line down to and including the closing `)` of
`self.setWindowTitle(...)` — with:

```python
    def set_commit_file(self, commits, filename):
        """Show `filename` as the selected commits changed it.

        With several commits selected the list shows the union of the files they
        touch, so the newest commit is not necessarily one that changed this
        file. Ask git which of them did and diff that one; a range would render
        empty whenever the change cancels out inside it.
        """
        if not commits or not filename:
            return
        commit = self._commit_for_file(commits, filename)
        diffwidget = self.diffwidget
        diffwidget.set_details(
            commit.oid,
            commit.author or '',
            commit.email or '',
            commit.authdate or '',
            commit.summary or '',
        )
        diffwidget.oid = commit.oid
        diffwidget.oid_start = None
        diffwidget.oid_end = None
        diffwidget.set_diff_oid(commit.oid, filename=filename)
        self.setWindowTitle(
            N_('%(filename)s - %(oid)s')
            % {'filename': filename, 'oid': commit.oid[:12]}
        )

    def _commit_for_file(self, commits, filename):
        """Return the newest of `commits` that changed `filename`.

        Falls back to the newest selected commit when git has no answer, which
        is what happens for a path that only exists in the STAGE or WORKTREE
        pseudo-commits.
        """
        if len(commits) == 1:
            return commits[0]
        oids = [
            commit.oid
            for commit in commits
            if commit.oid not in (dag.STAGE, dag.WORKTREE)
        ]
        touching = gitcmds.commit_touching_path(self.context, oids, filename)
        if touching:
            for commit in commits:
                if commit.oid == touching:
                    return commit
        return commits[-1]
```

> `files_selected()` is no longer used here: it exists to re-diff when the *selection* changes,
> and it is what routed this call into the range path. `set_diff_oid` is the single-commit
> equivalent and is already used everywhere else.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/gitcmds_test.py test/widgets_commit_file_diff_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 11 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "fix: diff the commit that actually changed the double-clicked file

With several commits selected the file list shows the union of the files they
touch, so the newest selection is often not the commit that changed the file
the user double-clicked. The window diffed the range from the oldest to the
newest selection, which renders empty whenever the change cancels out inside
the range or the oldest selection is the root commit -- leaving the newest
commit's title above an empty view.

commit_touching_path() asks git which of the selected commits last changed the
path and the window diffs that one."
```

---

## Task 2 — Branch chips stay readable on a selected row

**Goal:** the chip fills keep their hues but no longer disappear into the row they sit on.

> **Read trap F3 before starting.** `chip_head` paints **local** branches, `chip_other` paints
> **remote** ones. The reported bug is about `chip_head`.

### Step 2.1 (RED) — Write the tests

Append to `test/widgets_dag_history_test.py`:

```python
_CHIP_CONTRAST_FLOOR = 2.5


def _demo_palette(base, alternate, text, highlight, highlighted_text):
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(base))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(alternate))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(text))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(highlight))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(highlighted_text))
    return palette


_DEMO_PALETTES = (
    ('light', ('#ffffff', '#f2f2f2', '#101010', '#308cc6', '#ffffff')),
    ('dark', ('#1e1e1e', '#252525', '#e8e8e8', '#2f6f9f', '#ffffff')),
    ('solarized', ('#fdf6e3', '#eee8d5', '#657b83', '#268bd2', '#fdf6e3')),
)


@pytest.mark.parametrize(('name', 'colors'), _DEMO_PALETTES)
def test_chip_fills_stay_readable_on_a_selected_row(qapp, name, colors):
    """The reported bug: a chip must not vanish into the blue selected row."""
    palette = _demo_palette(*colors)
    style = inline_graph_style(palette)
    selected = _opaque_color(palette.highlight().color())

    for fill in (style.chip_other, style.chip_remote, style.chip_head):
        readable = readable_chip_fill(fill, (selected,))
        assert _color_contrast(readable, selected) >= _CHIP_CONTRAST_FLOOR, name


@pytest.mark.parametrize(('name', 'colors'), _DEMO_PALETTES)
def test_chip_fills_stay_readable_on_an_unselected_row(qapp, name, colors):
    palette = _demo_palette(*colors)
    style = inline_graph_style(palette)
    base = _opaque_color(palette.base().color())

    for fill in (style.chip_other, style.chip_remote, style.chip_head):
        readable = readable_chip_fill(fill, (base,))
        assert _color_contrast(readable, base) >= _CHIP_CONTRAST_FLOOR, name


@pytest.mark.parametrize(('name', 'colors'), _DEMO_PALETTES)
def test_chip_fills_keep_their_hues_apart(qapp, name, colors):
    """Distinctness is a hue property - contrast ratio cannot see it (trap F4)."""
    palette = _demo_palette(*colors)
    style = inline_graph_style(palette)
    selected = _opaque_color(palette.highlight().color())

    hues = [
        readable_chip_fill(fill, (selected,)).getHsvF()[0]
        for fill in (style.chip_other, style.chip_remote, style.chip_head)
    ]
    # A grey reports hue -1.0; round the rest so float noise does not split
    # two hues that are really the same.
    distinct = {round(hue, 3) if hue >= 0.0 else -1.0 for hue in hues}

    assert len(distinct) >= 2, name


def test_readable_chip_fill_leaves_a_good_color_alone(qapp):
    """No nudge when the fill already clears the floor - the design is kept."""
    background = QtGui.QColor('#ffffff')
    fill = QtGui.QColor('#404040')

    assert readable_chip_fill(fill, (background,)) == fill


def test_readable_chip_fill_preserves_the_hue(qapp):
    """The nudge moves lightness, never hue."""
    background = QtGui.QColor('#308cc6')
    fill = QtGui.QColor('#62a8d4')

    nudged = readable_chip_fill(fill, (background,))

    assert nudged != fill
    assert abs(nudged.getHsvF()[0] - fill.getHsvF()[0]) < 0.05
```

Add the imports — one line each, alphabetically inside the existing
`from cola.widgets.dag import …` group:

```bash
grep -n "^from cola.widgets.dag import" test/widgets_dag_history_test.py
```

```python
from cola.widgets.dag import _color_contrast
from cola.widgets.dag import _opaque_color
from cola.widgets.dag import readable_chip_fill
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -8
```

**Expected — a collection error for the whole file:**

```
ImportError: cannot import name 'readable_chip_fill' from 'cola.widgets.dag'
```

### Step 2.2 (GREEN) — Add the nudge

**Anchor:**

```bash
grep -n "^def _distinct_chip_backgrounds" cola/widgets/dag.py
```

**Expected:** exactly **one** hit. Insert **directly before it**:

```python
def readable_chip_fill(fill, backgrounds, floor=2.5):
    """Return `fill`, lightened or darkened until it clears `floor` everywhere.

    A chip is painted on a row whose background changes when the row is
    selected, and the selected background is the palette highlight -- the very
    color the local branch chip is mixed from. Mixing towards pure black or
    pure white moves lightness only, so the three semantic chip hues stay
    apart; contrast ratio cannot express that, being luminance-only.

    The fill is returned untouched when it already clears the floor, so a
    palette that is fine keeps exactly the colors it has today.
    """
    backgrounds = tuple(_opaque_color(color) for color in backgrounds)
    if not backgrounds:
        return fill
    fill = _opaque_color(fill)

    def worst_contrast(color):
        return min(_color_contrast(color, background) for background in backgrounds)

    if worst_contrast(fill) >= floor:
        return fill
    best = fill
    best_contrast = worst_contrast(fill)
    for target in (
        QtGui.QColor.fromHsvF(0.0, 0.0, 0.0, 1.0),
        QtGui.QColor.fromHsvF(0.0, 0.0, 1.0, 1.0),
    ):
        for step in range(1, 21):
            candidate = _mix_color(fill, target, step / 20.0)
            contrast = worst_contrast(candidate)
            if contrast >= floor:
                return candidate
            if contrast > best_contrast:
                best = candidate
                best_contrast = contrast
    return best


```

### Step 2.3 (GREEN) — Paint with it

**Anchor 1 — the signature.**

```bash
grep -n "        selected_text: QtGui.QColor | None = None," cola/widgets/dag.py
```

**Expected:** exactly **one** hit, inside the `_draw_labels` parameter list. Insert **directly
below it**:

```python
        row_background: QtGui.QColor | None = None,
```

> A default of `None` is required: `_draw_labels` is also called to measure the label width with
> `painter=None` and only seven arguments (trap **F7**).

**Anchor 2 — the fill.**

```bash
grep -n "                chip_text = _best_contrast(candidates, (brush,))" cola/widgets/dag.py
```

**Expected:** exactly **one** hit. Insert **directly above it**:

```python
                if row_background is not None:
                    brush = readable_chip_fill(brush, (row_background,))
```

**Anchor 3 — the call site.**

```bash
grep -n "                style.selected_text if selected else None," cola/widgets/dag.py
```

**Expected:** exactly **one** hit. Insert **directly below it**:

```python
                option.palette.highlight().color()
                if selected
                else option.palette.base().color(),
```

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 11 more passed than after Task 1, 0 failed (3 palettes × 3 parametrised
tests, plus 2 single tests).

### Commit

```bash
git add -A && git commit -m "fix: keep branch chips readable on the selected row

The chip used for local branches is mixed 76% from the palette highlight, and
the selected row is painted in that same highlight -- measured contrast between
them was 1.41 in a light palette and 1.33 in a dark one, so the chip vanished
into the selection.

readable_chip_fill() lightens or darkens a fill until it clears a 2.5 contrast
floor against the row it is painted on, and leaves it untouched when it already
does. Mixing towards black or white moves lightness only, so the three semantic
chip hues stay apart."
```

---

## Task 3 — Double-clicking a remote-only commit creates the local branch

**Goal:** a commit that carries only `remotes/<remote>/<name>` checks out a new local `<name>`
tracking it, instead of detaching HEAD.

### Step 3.1 (RED) — Write the tests

Append to `test/widgets_history_checkout_test.py`:

```python
def test_remote_only_commit_creates_a_tracking_branch(
    qapp, app_context, managed_qobject, monkeypatch
):
    """A commit that only exists on a remote becomes a local branch."""
    commit = _fake_commit('a' * 40, tags=['remotes/origin/feature'])
    tree = _tree(app_context, managed_qobject)
    recorded = []
    monkeypatch.setattr(
        cmds,
        'do',
        lambda cls, context, *args, **kwargs: recorded.append((cls, args, kwargs)),
    )

    tree.checkout_commit(commit)

    assert recorded == [
        (
            cmds.Checkout,
            (['-b', 'feature', '--track', 'origin/feature'],),
            {'checkout_branch': True},
        )
    ]


def test_remote_only_commit_keeps_a_slashed_branch_name(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Only the remote name is stripped, not the rest of the branch name."""
    commit = _fake_commit('a' * 40, tags=['remotes/origin/feat/nested'])
    tree = _tree(app_context, managed_qobject)
    recorded = []
    monkeypatch.setattr(
        cmds, 'do', lambda cls, context, *args, **kwargs: recorded.append(args)
    )

    tree.checkout_commit(commit)

    assert recorded == [(['-b', 'feat/nested', '--track', 'origin/feat/nested'],)]


def test_several_remote_branches_do_not_guess(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Two remotes carrying the same commit is ambiguous - do not pick one."""
    commit = _fake_commit(
        'a' * 40, tags=['remotes/origin/feature', 'remotes/fork/feature']
    )
    tree = _tree(app_context, managed_qobject)
    recorded = []
    monkeypatch.setattr(
        cmds, 'do', lambda cls, context, *args, **kwargs: recorded.append(cls)
    )
    monkeypatch.setattr(dagwidget, '_confirm_detached_checkout', lambda *a: False)

    tree.checkout_commit(commit)

    assert recorded == []


def test_a_local_branch_still_wins_over_a_remote_one(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Characterization: an existing local branch is checked out by name."""
    commit = _fake_commit(
        'a' * 40, branches=['feature'], tags=['remotes/origin/feature']
    )
    tree = _tree(app_context, managed_qobject)
    recorded = []
    monkeypatch.setattr(
        cmds, 'do', lambda cls, context, *args, **kwargs: recorded.append((cls, args))
    )

    tree.checkout_commit(commit)

    assert recorded == [(cmds.CheckoutBranch, ('feature',))]
```

Check the fixtures and the `_fake_commit` signature in that file first:

```bash
grep -n "^def _fake_commit" -A 10 test/widgets_history_checkout_test.py
grep -n "^from\|^import" test/widgets_history_checkout_test.py
```

`_fake_commit` there already accepts `branches` and `tags`. Add whatever import is missing —
the tests need `cmds` and the module itself (imported as `dagwidget`) for the monkeypatch:

```python
from cola import cmds
from cola.widgets import dag as dagwidget
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py 2>&1 | tail -12
```

**Expected:** the first two fail, the last two are **green already**.
`..._several_remote_branches_do_not_guess` and `..._a_local_branch_still_wins_over_a_remote_one`
are **characterization tests**. The first two fail as

```
AssertionError: assert [] == [(<class 'cola.cmds.Checkout'>, …)]
```

because today the remote-only commit reaches `_confirm_detached_checkout` instead, which the test
does not stub. If either characterization test is red: **stop and report.**

### Step 3.2 (GREEN) — Handle remote branches

**Anchor:**

```bash
grep -n "        if 'HEAD' in commit.tags:" cola/widgets/dag.py
```

**Expected:** exactly **one** hit, inside `checkout_commit`. Insert **directly above it**:

```python
        remote_branches = [
            tag[len(_REMOTES_PREFIX) :]
            for tag in commit.tags
            if tag.startswith(_REMOTES_PREFIX)
        ]
        if len(remote_branches) == 1:
            # "git checkout <name>" would do this too, but only when
            # checkout.guess is on, and it silently checks out an unrelated
            # local branch of the same name when one exists. Be explicit.
            tracking = remote_branches[0]
            local_name = tracking.split('/', 1)[1]
            cmds.do(
                cmds.Checkout,
                context,
                ['-b', local_name, '--track', tracking],
                checkout_branch=True,
            )
            return
```

Then extend the method's docstring so it still describes what it does.

```bash
grep -n "        the user has to opt into." cola/widgets/dag.py
```

**Expected:** exactly **one** hit. That line is the last line of the docstring text; the line
after it is the closing `"""`. Replace **only that one line** — leave the closing `"""` where
it is — with these three lines:

```python
        the user has to opt into. A commit that only carries a remote branch
        becomes a new local branch tracking it -- that is what the user means
        by double-clicking a branch they do not have yet.
```

> **Why `len(...) == 1`:** two remotes carrying the same commit give no basis for choosing one.
> That case keeps today's behaviour and falls through to the detached-checkout confirmation.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 4 more passed than after Task 2, 0 failed.

### Commit

```bash
git add -A && git commit -m "fix: check out a remote-only branch instead of detaching HEAD

Commit.branches holds local branches only, so a commit whose only ref is
refs/remotes/origin/<name> looked branchless and fell through to the detached
checkout path. The remote name is right there in Commit.tags.

The checkout is explicit -- 'git checkout -b <name> --track <remote>/<name>'.
Plain 'git checkout <name>' depends on checkout.guess being enabled and
silently checks out an unrelated local branch of the same name when one exists.
Two remotes carrying the same commit stay ambiguous and are left alone."
```

---

## Task 4 — The message box fits its content and opens where the user is looking

**Goal:** `MessageBox` sizes itself from its content and centres on its parent window.

> This box is shared by `confirm()`, `critical()` and `information()`
> (`cola/widgets/standard.py:1167`, `:1202`, `:1224`), which is why the same oversized dialog
> shows up all over the application.

### Step 4.1 (RED) — Write the tests

Append to `test/widgets_standard_test.py`:

```python
def test_message_box_is_not_wider_than_the_fixed_legacy_width(qapp, app_context):
    """A one-line question must not open at the full 720px dialog width."""
    box = MessageBox(
        parent=None, title='Create Remote?', text='Create a remote branch too?',
        info='', ok_text='Create',
    )

    box.set_initial_size()

    assert box.width() < defs.dialog_w
    box.deleteLater()


def test_message_box_is_wide_enough_for_its_text(qapp, app_context):
    """Shrinking must not cut the content off."""
    box = MessageBox(
        parent=None, title='Long', text='x' * 200, info='y' * 200, ok_text='OK'
    )

    box.set_initial_size()

    assert box.width() >= box.minimumSizeHint().width()
    assert box.height() >= box.minimumSizeHint().height()
    box.deleteLater()


def test_message_box_with_details_keeps_room_for_them(qapp, app_context):
    """A box showing a details pane still needs the taller layout."""
    small = MessageBox(parent=None, title='t', text='short', ok_text='OK')
    large = MessageBox(
        parent=None, title='t', text='short', details='line\n' * 40,
        ok_text='OK', expand_details=True,
    )

    small.set_initial_size()
    large.set_initial_size()

    assert large.height() > small.height()
    small.deleteLater()
    large.deleteLater()


def test_message_box_never_exceeds_the_screen(qapp, app_context):
    """Clamping is what keeps a huge details blob from opening off-screen."""
    desktop_width, desktop_height = qtutils.desktop_size()
    box = MessageBox(
        parent=None, title='t', text='short', details='line\n' * 5000,
        ok_text='OK', expand_details=True,
    )

    box.set_initial_size()

    assert box.width() <= desktop_width
    assert box.height() <= desktop_height
    box.deleteLater()
```

This file currently imports only `_strip_maximized_geometry_flag` and `QtCore`. Add what the
tests need — one import per line, and a `qapp` fixture copied from a neighbouring widget test:

```bash
grep -n "^def qapp" -A 8 test/widgets_history_checkout_test.py
```

```python
from cola import qtutils
from cola.widgets import defs
from cola.widgets.standard import MessageBox
from qtpy import QtWidgets

from .helper import app_context
```

> `app_context` is needed because `MessageBox` reaches `qtutils.active_window()` and the icon
> lookup; it also keeps the test in the repository sandbox the rest of the suite uses.

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_standard_test.py 2>&1 | tail -10
```

**Expected:** `..._not_wider_than_the_fixed_legacy_width` and
`..._with_details_keeps_room_for_them` fail, because today every box is exactly
`defs.dialog_w × defs.msgbox_h`:

```
assert 720 < 720
```

The other two are **characterization tests** and pass already. If they do not: **stop and report.**

### Step 4.2 (GREEN) — Size from content, centre on the parent

**Anchor:**

```bash
grep -n "    def set_initial_size(self):" cola/widgets/standard.py
```

**Expected:** exactly **one** hit. Replace the method — its `def` line and the three lines below
it — with:

```python
    def set_initial_size(self):
        """Size to the content and centre on the parent window.

        The old fixed 720x128 was the same for a one-line question and for a
        box with a details pane, which made every confirmation far larger than
        what it asks. sizeHint() already accounts for the details pane when it
        is visible, so the two cases separate on their own.
        """
        desktop_width, desktop_height = qtutils.desktop_size()
        hint = self.sizeHint()
        minimum = self.minimumSizeHint()
        width = max(hint.width(), minimum.width(), defs.dialog_w // 2)
        height = max(hint.height(), minimum.height())
        self.resize(
            min(width, desktop_width, defs.dialog_w),
            min(height, desktop_height),
        )
        self.center_on_parent()

    def center_on_parent(self):
        """Move the dialog to the middle of its parent, or of the screen"""
        parent = self.parentWidget()
        if parent is not None and parent.isVisible():
            reference = parent.frameGeometry()
        else:
            screen = self.screen() if hasattr(self, 'screen') else None
            if screen is None:
                return
            reference = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(reference.center())
        self.move(frame.topLeft())
```

> **`defs.dialog_w // 2` is a floor, not a target:** a very short question would otherwise open
> as a sliver too narrow to read the button labels. `defs.dialog_w` stays the ceiling, so nothing
> ever gets *wider* than today.
>
> **Measured with this implementation in place:** a one-line confirmation opens at **360 × 124**
> instead of 720 × 128 — the floor is what decides its width, `sizeHint()` alone would be
> narrower still. A box with a 40-line details pane opens at **328** high, so the details case
> still gets its room.
>
> **`self.screen()` needs Qt 5.14+;** the `hasattr` guard keeps the older path working by simply
> not moving the dialog, which is today's behaviour.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_standard_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 4 more passed than after Task 3, 0 failed.

> **If a test elsewhere asserts the old dialog geometry, that is a real finding, not a chore.**
> Report it with the test name instead of loosening the assertion.

### Commit

```bash
git add -A && git commit -m "fix: size the message box to its content and centre it on the parent

MessageBox opened at a fixed 720x128 whatever it contained, and every
confirmation and error dialog in the application goes through it -- which is
why the 'create a remote branch too?' question filled a third of the screen.

It now sizes from sizeHint(), floored so the buttons stay readable, capped at
the old width and at the screen, and centres on its parent window instead of
wherever the window manager put it."
```

---

## Task 5 — Documentation

### Step 5.1 — `references/gotchas.md`

Anchor:

```bash
grep -n "^## Git output$" .claude/skills/project-brief/references/gotchas.md
grep -n "^## Icons$" .claude/skills/project-brief/references/gotchas.md
```

**Expected:** exactly **one** hit each, `## Icons` after `## Git output`. Insert at the **end of
the `## Git output` section**, directly before the `## Icons` line:

```markdown
**`git rev-list --no-walk <oids> -- <path>` answers "which of these commits touched this file".**
It does not walk ancestors, so a commit outside the list can never be the answer, and its default
ordering is by commit date, newest first -- `--max-count=1` therefore yields the newest toucher.
An empty result is exit status 0 with empty output, not an error. Beware when probing this in a
script-built repository: commits made in the same second fall back to argument order and make the
ordering look input-driven.

**Plain `git checkout <name>` is not a safe way to materialise a remote branch.** It depends on
`checkout.guess` being enabled, and when a local branch of the same name already exists elsewhere
it silently checks that one out. Use `git checkout -b <name> --track <remote>/<name>`.
```

Then anchor the Qt section:

```bash
grep -n "^## Qt widget behavior$" .claude/skills/project-brief/references/gotchas.md
```

Append to the end of that section:

```markdown
**The inline graph's chip color names are misleading.** `chip_head` paints **local** branches
(`heads/…`), `chip_other` is the fallback that **remote** branches land in, and `chip_remote`
paints `HEAD` and tags. See `cola/widgets/dag.py` where the brush is chosen.

**Contrast ratio is luminance-only, so it cannot assert that two colors look different.** Forcing
several fills to the same contrast floor against the same background necessarily puts them at the
same luminance, which reads as "contrast 1.0" between them while they stay clearly different
hues. Assert distinctness on hue.

**`MessageBox` is shared by `confirm()`, `critical()` and `information()`.** A change to its size
or position is felt in every dialog in the application.
```

### Step 5.2 — `references/fork-history.md`

Anchor:

```bash
grep -n "^## " .claude/skills/project-brief/references/fork-history.md
```

Insert **after** the last numbered section and **directly before** `## Where the fork's tests
live`. Take the number from the last numbered section you see and add one — if the last is
`## 7. …`, the new one is `## 8. …`. If there is no numbered section at all: **stop and report.**

```markdown
## <N>. Bug fixes after the multi-select work

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
```

### Step 5.3 — Mark the plan as done

Set this plan's frontmatter to `status: completed` and add `completed_at`, `plan_commit`,
`implementation_branch`, `implementation_head`, `ci_run` and `manual_verification` — as described
in `docs/plans/README.md`. Add this plan's row to the table there.

> `docs/plans/README.md` is currently in German again after a merge. Add your row in the language
> the table around you uses, and do not translate the rest as part of this plan.

### Verification

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
garden check/fmt && garden check/pyupgrade && garden check/mypy
```

**Expected:** green, unchanged. A missing tool is not a reason to abort: **note which check did
not run** and say so in the final report.

### Commit

```bash
git add -A && git commit -m "docs: document the four history bug fixes"
```

---

## Manual acceptance

```bash
garden run
```

1. **Issue 1.** Select two commits that changed different files. Double-click a file that only the
   *older* one touched: its diff appears, and the window title names that older commit. Repeat
   with the oldest commit of the repository in the selection.
2. **Issue 2.** Select a row that carries a local branch chip: the chip stays clearly readable
   against the blue selection, and remote, tag and local chips are still telling apart. Check in a
   light **and** a dark theme (`View → Theme`).
3. **Issue 3.** Fetch a branch you do not have locally, double-click its tip in the history: a
   local branch of the same name is created and checked out, tracking the remote. `git status`
   shows the branch name, not a detached HEAD.
4. **Issue 4.** Create a branch and let the "create a remote branch too?" dialog appear: it is
   only as large as its content and sits centred over the main window. Trigger an error dialog
   with a details pane and confirm it is still big enough to read.

> **In an environment without a display this section does not apply.** Points 1, 3 and 4 are
> covered by the tests from Tasks 1, 3 and 4. **Point 2 is not** — the tests assert contrast
> numbers, and nobody has looked at the result. **Write it that way in the final report, do not
> present it as "checked".**
