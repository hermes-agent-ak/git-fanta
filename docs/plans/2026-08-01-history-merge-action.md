---
status: open
---

# Merge action in the history context menu, with a robust preselection

**Created:** 2026-08-01
**Branch:** Commit the tasks onto whatever branch is checked out at the start. **Never onto
`main`** — the pattern for feature work is `tree-ui/<agent>/<model>/<topic>`. Check before Task 1:
`git rev-parse --abbrev-ref HEAD`. If it says `main`, create a branch first. This plan does **not**
create one.
**Affects:** `cola/gitcmds.py`, `cola/widgets/dag.py`, `cola/widgets/merge.py`. The menu action
lands in `ViewerMixin`, which is shared by the commit list **and** the graph view.

---

## 0. How to read this plan

This plan is written so that it can be executed **without prior knowledge and without making any
decisions of your own**.

- **Do the tasks strictly in order 0 → 5.** Skip nothing. Each task leaves the suite green.
- **One task = one commit.** The commit message is written out verbatim at the end of each task.
  Use it as it stands.
- **Commit only. Never push.** No task in this plan runs `git push`, and none should. The branch
  stays local; whoever reviews the work decides when it leaves the machine. Do not open a pull
  request either.
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
> `pytest` call in this plan. A `python3 -m pytest` that aborts with `No module named pytest` is
> **not** a RED, it is the wrong substitution.

Standard test command:

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test
```

---

## 1. What is being built

Right-clicking a row in the history whose branch has commits the current branch does not have adds
one entry to the context menu:

```
Checkout Branch
Merge "feature" into "main"      <- new, only when there is something to merge
Create Branch
Create Tag
Rebase to this commit
```

Choosing it opens **the standard merge dialog** — the same one as `Actions → Merge...` — with the
branch already filled in, the matching radio button selected and the branch highlighted in the
list.

Settled decisions:

| Question | Decision |
|---|---|
| Which menu? | The **history context menu** (`ViewerMixin`, `cola/widgets/dag.py`). It has no merge action today. The Branches dock already has one and is **not** touched — see §3. |
| What counts as "mergeable"? | The ref has at least one commit that `HEAD` does not: `git rev-list --count HEAD..<ref>` > 0. This is true for a branch strictly ahead **and** for a diverged branch, and false for a branch that is already contained — which is what "nothing to merge" means. `--is-ancestor` would have been wrong (trap **F1**). |
| Which ref, when a row carries several? | First local branch that is not the current branch, then the first remote branch, in the order git decorated them. Every ref at one commit merges to the identical result, so the choice only decides the wording; it is fixed so the same row never offers two different things. |
| Tags? | **Not offered by the menu.** The user asked for branches. `select_ref` still classifies tags, because it has to classify *something* for every ref it is handed and a partial classifier is the fragile kind — see §2.2. |
| Which dialog? | `cola/widgets/merge.py`, through `local_merge(context, ref=…)`. No new dialog, no new command. |
| Where does the git call happen? | In `update_menu_actions`, once per right-click, and only when a candidate ref exists. Never when the click was not on a row. |
| Detached HEAD? | Still works: `HEAD..<ref>` does not need a branch name. The dialog title falls back to whatever `model.currentbranch` holds. |

## 2. Root causes and ground truth — all measured

### 2.1 There is no merge action in the history

`ViewerMixin.context_menu_event` (`cola/widgets/dag.py:471`) lists 24 actions and none of them
merges. The other two merge entry points are:

| Where | What it does today |
|---|---|
| `cola/widgets/main.py:394` | `Actions → Merge...` → `merge.local_merge(context)` — the standard dialog, **no** preselection |
| `cola/widgets/branch.py:297` | Branches dock, "Merge into current branch" → `cmds.MergeBranch` **immediately, without a dialog**, offered for every non-current branch |

### 2.2 The dialog accepts a `ref` but preselects it weakly

`Merge.__init__(context, parent=None, ref=None)` already does `self.revision.set_value(ref)`
(`cola/widgets/merge.py:40-41`). Measured with a real repository, that is not enough:

| ref | revision field | radio | list shows | list selection |
|---|---|---|---|---|
| `ahead` (a local branch) | `'ahead'` ✓ | Local | `['ahead', 'behind', 'main']` | **empty** |
| `v1` (a tag) | `'v1'` ✓ | **Local** | `['ahead', 'behind', 'main']` | **empty** |

Two things go wrong. The preselected ref is **never highlighted** in the list, and for anything
that is not a local branch the radio button stays on *Local*, so the list shows a completely
different kind of ref. And it is fragile: measured, clicking any row of that list **overwrites**
the field — `v1` became `ahead` on the first stray click, because `revision_selected` writes the
list item back into the field (`cola/widgets/merge.py:193-199`).

That is the "nothing may go wrong with the preselection" requirement, and it needs the radio, the
list selection and the field to agree. Measured with the fix from Task 3:

| ref | field | radio | list shows | list selection |
|---|---|---|---|---|
| `ahead` | `'ahead'` | Local | `['ahead', 'behind', 'main']` | `['ahead']` |
| `v1` | `'v1'` | **Tag** | `['v1']` | `['v1']` |
| a raw oid | the oid | Local | local branches | none — and that is correct |

Setting the right radio has a second effect worth naming: the list then only contains refs of the
right kind, so a stray click can no longer jump to an unrelated one.

### 2.3 Mergeability, measured

`git rev-list --count HEAD..<ref>` through the project's own wrapper
(`context.git.rev_list(f'HEAD..{ref}', count=True, _readonly=True)`):

| ref | status | output | meaning |
|---|---|---|---|
| a branch 2 commits ahead | 0 | `'1'` | mergeable |
| a diverged branch | 0 | `'1'` | mergeable |
| a branch already contained | 0 | `'0'` | nothing to merge |
| the current branch | 0 | `'0'` | nothing to merge |
| a tag ahead | 0 | `'1'` | mergeable |
| a ref that does not exist | **128** | `''` | must be treated as "no" |

## 3. Non-goals

- **No change to the Branches dock.** Its "Merge into current branch" keeps merging immediately
  and keeps being offered unconditionally. Changing it is a separate decision with its own blast
  radius.
- **No change to `Actions → Merge...`** in the main menu. It keeps opening the dialog without a
  preselection; `ref` stays optional.
- **No new merge command.** `cmds.Merge` is what the dialog already runs.
- **No tags in the menu.** See §1.
- **No submenu listing every ref of a row.** One deterministic candidate, documented.
- **No mergeability indicator anywhere else** — not in the graph, not in the branch chips.
- **No caching of the mergeability answer.** One `git rev-list` per right-click on a row that
  carries a branch is cheap and always current.

## 4. Traps — all empirically verified

| # | Trap | Evidence |
|---|---|---|
| **F1** | **`git merge-base --is-ancestor` is the wrong test for "mergeable".** For a branch that is ahead *and* diverged it exits 1, which reads as "not mergeable" although there is plenty to merge. Count the commits instead. | Measured: branch `ahead` (2 commits the current branch lacks) → `--is-ancestor` exit 1, `rev-list --count HEAD..ahead` = 2 |
| **F2** | **`git rev-list` exits 128 for a ref that does not exist** and prints `fatal: ambiguous argument`. The status must be checked; an unchecked `int(out)` would raise `ValueError` on the empty output. | Measured through the wrapper: `status=128`, `out=''`, `err="fatal: ambiguous argument 'HEAD..does-no…"` |
| **F3** | **The menu action set is asserted exactly, twice by count and once by key set.** `test/widgets_main_history_test.py:360-363` checks `set(tree.menu_actions) == VIEWER_ACTION_KEYS`, `len(...) == 24` and `len(set(values())) == 24`. A new action breaks all three unless they are updated. | `test/widgets_main_history_test.py:45-70` (the 24-key set) and `:360-363` |
| **F4** | **That same test also requires every action to be *disabled* when the click misses a row.** It sends a context-menu event at `QPoint(-1, -1)` and asserts `all(not action.isEnabled() …)`. The new action must therefore be disabled whenever there is no candidate — and must not call git in that case. | `test/widgets_main_history_test.py:376-384` |
| **F5** | **`ViewerMixin` is shared by two widgets.** `CommitTreeWidget` (`cola/widgets/dag.py:1618`) and `GraphView` (`:3429`) both mix it in, and `GitDAG` builds the action dict for both (`:2575-2576`). The new action therefore appears in the graph view's menu too. Both set `self.clicked`, so the handler works in both. | `cola/widgets/dag.py:106`, `:1618`, `:3429`, `:2575-2576` |
| **F6** | **`menu_actions` is `None` on a freshly built `CommitTreeWidget`.** `ViewerMixin.__init__` sets it to `None` "provided by implementation"; only `GitDAG` assigns it. A test that calls `update_menu_actions` on a bare tree crashes with `TypeError: 'NoneType' object is not subscriptable` unless it assigns `viewer_actions(tree, tree)` first. | `cola/widgets/dag.py:113`, `:2575` |
| **F7** | **`cola/widgets/dag.py` does not import `gitcmds` or `merge`.** Both are needed. `cola/widgets/merge.py` imports neither `dag` nor `gitcmds`, so neither import is a cycle. | `grep -c "^from \\.\\. import gitcmds$" cola/widgets/dag.py` → `0`; `grep -n import cola/widgets/merge.py` shows no `dag` |
| **F8** | **`local_merge` has two callers and one of them passes the function itself, not a call.** `cola/widgets/main.py:394` uses `partial(merge.local_merge, context)` and `cola/widgets/toolbarcmds.py:112` stores `merge.local_merge` as a value. A new parameter must therefore be **last and optional**, or both break. | `grep -rn "local_merge" cola/` |
| **F9** | **`Merge.__init__` calls `update_all()` near the end**, which calls `update_revisions()` and rebuilds the list. Preselection must happen **after** that call, otherwise the list selection is wiped. The revision *field* survives either way — `update_revisions` only touches the list. | `cola/widgets/merge.py:143-148`; measured: a later `model.updated` does not clear the field |
| **F10** | **Selecting a list item writes it into the revision field.** `revision_selected` is connected to `itemSelectionChanged`. Any preselection must therefore set the field **last**, after selecting the item, or the item wins. | `cola/widgets/merge.py:136`, `:193-199`; measured: `v1` became `ahead` after one stray click |
| **F11** | **`commit.tags` carries prefixed refs.** A local branch appears both in `commit.branches` (bare) and in `commit.tags` as `heads/<name>`; remote branches appear as `remotes/<remote>/<name>`, tags as `tags/<name>`, and `HEAD` appears bare. `refs/remotes/origin/HEAD` is dropped by `add_label`. | `cola/models/dag.py:192-238`; measured tags for a clone: `['HEAD', 'heads/main', 'remotes/origin/main']` |
| **F13** | **`update_menu_actions` overwrites `self.clicked` from the event position.** Its first lines do `item = self.itemAt(event.pos())` and then set `self.clicked` from it. A test that assigns `tree.clicked` and *then* calls `update_menu_actions` has its assignment silently thrown away and sees every action disabled. Patch `itemAt` instead. The handler `merge_branch()` reads `self.clicked` directly and *is* set that way in a test. | Measured: presetting `tree.clicked` then calling `update_menu_actions(QPoint(-1, -1))` left the action disabled; patching `itemAt` to report a row produced `Merge "ahead" into "main"`, enabled |
| **F12** | **`pytest.ini` sets `--doctest-modules`.** A `>>>` in a new docstring becomes a test. | `pytest.ini:3` |

## 5. What already exists and is reused (do not rebuild)

| Exists | Where | Role in this plan |
|---|---|---|
| `Merge` dialog with a `ref` parameter | `cola/widgets/merge.py:23` | **Is** the dialog. Task 3 makes its preselection robust; it does not build a new one. |
| `local_merge(context)` | `cola/widgets/merge.py:15` | **Is** the entry point. Task 3 adds an optional `ref`. |
| `cmds.Merge` | run by `merge_revision` | **Is** the merge. Untouched. |
| `viewer_actions(widget, proxy)` | `cola/widgets/dag.py:548` | **Is** the action factory. The new action is one more entry in its dict. |
| `ViewerMixin.checkout_branch` | `cola/widgets/dag.py:217` | **Template** for the new handler: reads `self.clicked`, falls back to the selection, returns early when there is nothing. |
| `_REMOTES_PREFIX`, `_TAGS_PREFIX`, `_HEADS_PREFIX` | `cola/widgets/dag.py:755-757` | The ref prefixes. No new constants. |
| `app_context` fixture | `test/helper.py:85` | Real temporary git repository for every test here. |
| `qapp`, `managed_qobject`, `_tree`, `_fake_commit` | `test/widgets_history_checkout_test.py:24`, `:35`, `:90`, `:72` | **Already in the file** Task 4 extends. `_fake_commit(oid, branches=(), tags=())` is exactly the stand-in the candidate logic needs. |
| `test/gitcmds_test.py` | whole file | Where Task 1's tests go; it already imports `gitcmds`, `helper` and `app_context`. |

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

If that fails too: **STOP and report.**

### Verification

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -5
```

**Expected:** `NNN passed`, no `failed`, no `error`. **Note `NNN` as the baseline.**

---

## Task 1 — Ask git whether there is anything to merge

**Goal:** `gitcmds.can_merge(context, ref)` answers one question and nothing else.

### Step 1.1 (RED) — Write the tests

`test/gitcmds_test.py` already imports `gitcmds`, `helper` and `app_context`. It does **not**
import `pytest`. Anchor:

```bash
grep -n "^import os$" test/gitcmds_test.py
```

Insert **two lines below it** (a blank line, then the import), keeping the standard library group
separate:

```python
import pytest
```

Append to the **end** of `test/gitcmds_test.py`:

```python
def _merge_repo(context):
    """A branch ahead of main, one behind it, and one that diverged."""
    helper.run_git('commit', '-m', 'base')
    base = helper.run_git('rev-parse', 'HEAD').strip()
    helper.run_git('checkout', '-q', '-b', 'ahead')
    helper.write_file('ahead.txt', 'ahead\n')
    helper.run_git('add', 'ahead.txt')
    helper.run_git('commit', '-m', 'ahead')
    helper.run_git('checkout', '-q', 'main')
    helper.run_git('branch', 'behind', base)
    helper.run_git('checkout', '-q', '-b', 'diverged', base)
    helper.write_file('diverged.txt', 'diverged\n')
    helper.run_git('add', 'diverged.txt')
    helper.run_git('commit', '-m', 'diverged')
    helper.run_git('checkout', '-q', 'main')
    helper.write_file('main.txt', 'main\n')
    helper.run_git('add', 'main.txt')
    helper.run_git('commit', '-m', 'main work')
    context.model.update_status()
    return base


@pytest.mark.parametrize(
    ('ref', 'expected'),
    (
        ('ahead', True),
        ('diverged', True),
        ('behind', False),
        ('main', False),
    ),
)
def test_can_merge_reports_whether_the_ref_has_new_commits(app_context, ref, expected):
    """Ahead and diverged both have something to merge; contained does not."""
    _merge_repo(app_context)

    assert gitcmds.can_merge(app_context, ref) is expected


def test_can_merge_says_no_for_a_ref_that_does_not_exist(app_context):
    """git exits 128 there; that is a no, not a crash (trap F2)."""
    _merge_repo(app_context)

    assert gitcmds.can_merge(app_context, 'no-such-branch') is False


@pytest.mark.parametrize('ref', ('', None))
def test_can_merge_says_no_without_a_ref(app_context, ref):
    """No ref means no question to ask and no git call."""
    assert gitcmds.can_merge(app_context, ref) is False
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/gitcmds_test.py 2>&1 | tail -8
```

**Expected:** all seven fail with

```
AttributeError: module 'cola.gitcmds' has no attribute 'can_merge'
```

Confirm beforehand: `grep -c can_merge cola/gitcmds.py` → `0`.

### Step 1.2 (GREEN) — Add the helper

**Anchor:**

```bash
grep -n "^def merge_base(context: ApplicationContext, head: str, ref: str) -> core.UStr:" cola/gitcmds.py
```

**Expected:** exactly **one** hit. Insert **directly before it**:

```python
def can_merge(context, ref):
    """Return True when `ref` holds commits that HEAD does not.

    That is what "there is something to merge" means: it covers a branch that
    is strictly ahead and a branch that diverged, and excludes one that is
    already contained. "git merge-base --is-ancestor" cannot express it -- it
    answers a different question and reports a diverged branch as unmergeable.

    A ref that does not resolve makes git exit non-zero; that is a no, not an
    error worth surfacing.
    """
    if not ref:
        return False
    status, out, _ = context.git.rev_list(
        f'HEAD..{ref}', count=True, _readonly=True
    )
    if status != 0:
        return False
    return out.strip() not in ('', '0')


```

> **No `int()` on the output.** It is empty whenever git failed, and comparing the text avoids a
> `ValueError` on a path the tests deliberately exercise.

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/gitcmds_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 7 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "feat: ask git whether a ref has anything to merge

can_merge() counts the commits a ref holds that HEAD does not. That covers a
branch which is strictly ahead and one which diverged, and excludes one that is
already contained. 'git merge-base --is-ancestor' answers a different question
and calls a diverged branch unmergeable."
```

---

## Task 2 — Decide which ref of a row to offer

**Goal:** `merge_candidate(commit, current_branch)` — a pure function, no git, no Qt.

### Step 2.1 (RED) — Write the tests

Append to `test/widgets_dag_history_test.py`:

```python
def _candidate_commit(branches=(), tags=(), oid='a' * 40):
    commit = dag.Commit(None, dag.CommitFactory(), oid=oid)
    commit.branches = list(branches)
    commit.tags = list(tags)
    return commit


@pytest.mark.parametrize(
    ('scenario', 'branches', 'tags', 'expected'),
    (
        ('a local branch', ['feature'], ['heads/feature'], 'feature'),
        ('the current branch is skipped', ['main'], ['heads/main'], ''),
        (
            'the first branch that is not current wins',
            ['main', 'feature'],
            ['heads/main', 'heads/feature'],
            'feature',
        ),
        (
            'a remote branch when there is no local one',
            [],
            ['remotes/origin/feature'],
            'origin/feature',
        ),
        (
            'a local branch beats a remote one',
            ['feature'],
            ['heads/feature', 'remotes/origin/other'],
            'feature',
        ),
        ('a tag alone is not offered', [], ['tags/v1'], ''),
        ('HEAD alone is not offered', [], ['HEAD'], ''),
        ('nothing at all', [], [], ''),
    ),
)
def test_merge_candidate_picks_one_ref(scenario, branches, tags, expected):
    """One deterministic ref per row, local branches first."""
    commit = _candidate_commit(branches, tags)

    assert merge_candidate(commit, 'main') == expected, scenario


@pytest.mark.parametrize('oid', (dag.STAGE, dag.WORKTREE))
def test_merge_candidate_ignores_the_pseudo_commits(oid):
    """STAGE and WORKTREE are not revisions and cannot be merged."""
    commit = _candidate_commit(['feature'], ['heads/feature'], oid=oid)

    assert merge_candidate(commit, 'main') == ''


def test_merge_candidate_without_a_commit():
    assert merge_candidate(None, 'main') == ''
```

Add the import — one line, alphabetically inside the existing `from cola.widgets.dag import …`
group:

```bash
grep -n "^from cola.widgets.dag import" test/widgets_dag_history_test.py
```

```python
from cola.widgets.dag import merge_candidate
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -8
```

**Expected — a collection error for the whole file:**

```
ImportError: cannot import name 'merge_candidate' from 'cola.widgets.dag'
```

> That reddens every test in the file. Here that is intended: the function does not exist yet.

### Step 2.2 (GREEN) — Add the function

**Anchor:**

```bash
grep -n "^_REMOTES_PREFIX = 'remotes/'" cola/widgets/dag.py
```

**Expected:** exactly **one** hit. The three prefix constants and `_HEAD_REF` sit together just
below it. Find the end of that group:

```bash
grep -n "^_HEAD_REF = 'HEAD'" cola/widgets/dag.py
```

Insert **two lines below `_HEAD_REF`** (leave one blank line, then two, as the module does between
top-level definitions):

```python
def merge_candidate(commit, current_branch):
    """Return the ref of `commit` to offer for merging, or ''.

    A row can carry several refs and they all point at the same commit, so any
    of them merges to the identical result. Local branches come first because
    that is the name the user thinks in, then remote branches. The order is
    fixed so the same row never offers two different things.

    Tags are deliberately not offered: the menu entry is about branches.
    """
    if commit is None or commit.oid in (dag.STAGE, dag.WORKTREE):
        return ''
    for branch in commit.branches:
        if branch != current_branch:
            return branch
    for tag in commit.tags:
        if tag.startswith(_REMOTES_PREFIX):
            return tag[len(_REMOTES_PREFIX) :]
    return ''
```

> **No new constants** — `_REMOTES_PREFIX` is already there (trap **F11** explains the shapes in
> `commit.tags`).

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 18 passed, 0 failed — 8 table rows, 2 pseudo-commit rows, 1 single test,
on top of Task 1's 7.

### Commit

```bash
git add -A && git commit -m "feat: pick one merge candidate ref per history row

merge_candidate() prefers a local branch that is not the current one, then a
remote branch. Every ref at a commit merges identically, so the choice only
decides the wording -- but it is fixed, so one row never offers two different
things. STAGE and WORKTREE are not revisions and yield nothing."
```

---

## Task 3 — Preselect the ref in the merge dialog, robustly

**Goal:** the dialog opens with the radio, the list selection and the revision field all agreeing.

### Step 3.1 (RED) — Write the tests

Create the new file `test/widgets_merge_preselect_test.py`. Copy the `qapp` and `managed_qobject`
fixtures **verbatim** from `test/widgets_history_checkout_test.py` — do not invent variants:

```bash
sed -n '/^@pytest.fixture(scope=.module.)$/,/^def _git/p' test/widgets_history_checkout_test.py
```

The new file:

```python
# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""The merge dialog opens with a ref already chosen, in every field that shows it."""

import subprocess
import sys

import pytest

from cola.qtutils import get
from cola.widgets.merge import Merge
from cola.widgets.merge import local_merge
from qtpy import QtCore
from qtpy import QtTest
from qtpy import QtWidgets

from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


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


def _git(*args):
    """Same form as in test/widgets_main_history_test.py: with strip()."""
    return subprocess.run(
        ('git', *args), check=True, text=True, capture_output=True
    ).stdout.strip()


@pytest.fixture
def merge_repo(app_context):
    """A local branch ahead of main and a tag on it."""
    _git('commit', '-q', '-m', 'base')
    _git('checkout', '-q', '-b', 'ahead')
    _git('commit', '-q', '--allow-empty', '-m', 'ahead')
    _git('tag', 'v1')
    _git('checkout', '-q', 'main')
    app_context.model.update_status()
    return app_context


def _dialog(app_context, managed_qobject):
    return managed_qobject(Merge(app_context, parent=None))


def _listed(dialog):
    revisions = dialog.revisions
    return [revisions.item(row).text() for row in range(revisions.count())]


def _selected(dialog):
    return [item.text() for item in dialog.revisions.selectedItems()]


def test_a_local_branch_is_selected_everywhere(qapp, merge_repo, managed_qobject):
    """Field, radio and list selection must agree, or a click undoes the choice."""
    dialog = _dialog(merge_repo, managed_qobject)

    dialog.select_ref('ahead')

    assert dialog.revision.text() == 'ahead'
    assert get(dialog.radio_local)
    assert _selected(dialog) == ['ahead']


def test_a_tag_switches_the_radio_and_the_list(qapp, merge_repo, managed_qobject):
    """Without this the list keeps showing branches and the tag is unreachable."""
    dialog = _dialog(merge_repo, managed_qobject)

    dialog.select_ref('v1')

    assert dialog.revision.text() == 'v1'
    assert get(dialog.radio_tag)
    assert _listed(dialog) == ['v1']
    assert _selected(dialog) == ['v1']


def test_an_unknown_ref_still_lands_in_the_field(qapp, merge_repo, managed_qobject):
    """A raw object ID is a legal revision; it just has no list to appear in."""
    dialog = _dialog(merge_repo, managed_qobject)

    dialog.select_ref('a' * 40)

    assert dialog.revision.text() == 'a' * 40
    assert _selected(dialog) == []
    assert dialog.button_merge.isEnabled()


def test_selecting_nothing_changes_nothing(qapp, merge_repo, managed_qobject):
    dialog = _dialog(merge_repo, managed_qobject)

    dialog.select_ref('')

    assert dialog.revision.text() == ''


def test_a_model_update_does_not_clobber_the_choice(qapp, merge_repo, managed_qobject):
    """update_all() rebuilds the list; the choice has to survive it."""
    dialog = _dialog(merge_repo, managed_qobject)
    dialog.select_ref('ahead')

    merge_repo.model.updated.emit()
    qapp.processEvents()

    assert dialog.revision.text() == 'ahead'


def test_local_merge_passes_the_ref_through(qapp, merge_repo, managed_qobject):
    """The entry point the history menu calls."""
    view = managed_qobject(local_merge(merge_repo, ref='ahead'))

    assert view.revision.text() == 'ahead'
    assert _selected(view) == ['ahead']


def test_local_merge_without_a_ref_is_unchanged(qapp, merge_repo, managed_qobject):
    """Characterization: Actions -> Merge... still opens an empty dialog."""
    view = managed_qobject(local_merge(merge_repo))

    assert view.revision.text() == ''
```

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_merge_preselect_test.py 2>&1 | tail -12
```

**Expected:** six of the seven fail with

```
AttributeError: 'Merge' object has no attribute 'select_ref'
```

except `..._local_merge_passes_the_ref_through`, which fails earlier with

```
TypeError: local_merge() got an unexpected keyword argument 'ref'
```

`..._local_merge_without_a_ref_is_unchanged` is a **characterization test** and is **green
already**. If it is red: **stop and report.**

### Step 3.2 (GREEN) — Add `select_ref`

**Anchor 1 — remove the weak preselection.**

```bash
grep -n "        if ref:" -A 1 cola/widgets/merge.py
```

**Expected:** exactly **one** hit, followed by `            self.revision.set_value(ref)`. Delete
**both** lines.

**Anchor 2 — preselect after the list has been built.**

```bash
grep -n "        self.update_all()" cola/widgets/merge.py
```

**Expected:** exactly **one** hit. Insert **directly below it**:

```python
        self.select_ref(ref)
```

> It has to go **after** `update_all()`: that call rebuilds the revision list, so a selection made
> before it would be wiped (trap **F9**).

**Anchor 3 — the method.**

```bash
grep -n "    def update_all(self):" cola/widgets/merge.py
```

**Expected:** exactly **one** hit. Insert **directly above it**:

```python
    def select_ref(self, ref):
        """Show `ref` as the chosen revision in every widget that displays one.

        The revision field alone is not enough. The radio group decides which
        refs the list offers, so a tag preselected while "Local Branch" is
        checked is invisible there -- and selecting any list row overwrites the
        field, so the first stray click would silently merge something else.
        Setting the radio, the list selection and the field together keeps them
        from disagreeing.

        The field is written last on purpose: selecting a list item writes that
        item into it, so anything else would lose to the list.
        """
        if not ref:
            return
        model = self.model
        if ref in model.local_branches:
            radio = self.radio_local
        elif ref in model.remote_branches:
            radio = self.radio_remote
        elif ref in model.tags:
            radio = self.radio_tag
        else:
            radio = None
        if radio is not None:
            radio.setChecked(True)
            # setChecked() does not emit "released", so the list that the radio
            # buttons drive has to be rebuilt by hand.
            self.update_revisions()
            items = self.revisions.findItems(ref, Qt.MatchExactly)
            if items:
                self.revisions.setCurrentItem(items[0])
        self.revision.set_value(ref)

```

> `Qt` is already imported at the top of the file (`from qtpy.QtCore import Qt`). No new import.

**Anchor 4 — the entry point.**

```bash
grep -n "^def local_merge(context):" -A 6 cola/widgets/merge.py
```

**Expected:** exactly **one** hit. Replace that function with:

```python
def local_merge(context, ref=None):
    """Provides a dialog for merging branches"""
    view = Merge(context, qtutils.active_window(), ref=ref)
    view.show()
    view.raise_()
    return view
```

> `ref` is **last and optional** so the two existing callers keep working — one of them stores the
> function itself rather than calling it (trap **F8**).

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_merge_preselect_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 25 passed, 0 failed — Task 1's 7, Task 2's 11 and 7 here.

### Commit

```bash
git add -A && git commit -m "feat: preselect a revision in the merge dialog properly

The dialog already took a ref and wrote it into the revision field, but nothing
else followed: the radio group stayed on Local Branch, so a tag was invisible in
the list, and the ref was never highlighted. Selecting any list row overwrites
the field, so the first stray click silently replaced the choice -- measured, a
preselected tag became the first local branch.

select_ref() sets the radio, rebuilds the list, selects the item and writes the
field last, so the three cannot disagree. local_merge() forwards an optional
ref; both existing callers pass none and are unaffected."
```

---

## Task 4 — Offer the merge in the history context menu

**Goal:** the action appears, is enabled only when there is something to merge, and opens the
dialog on the right branch.

### Step 4.1 (GREEN, no test yet) — Keep the action-set contract honest

The history menu's action set is asserted **exactly** (trap **F3**). Update it first, so the RED
in step 4.2 is about the new behaviour and not about a count.

```bash
grep -n "^VIEWER_ACTION_KEYS = {" -A 26 test/widgets_main_history_test.py
```

Insert `'merge_branch',` into that set, alphabetically — between `'diff_this_selected',` and
`'rebase_to_commit',`:

```python
    'merge_branch',
```

Then the two counts:

```bash
grep -n "== 24" test/widgets_main_history_test.py
```

**Expected:** exactly **two** hits, both in
`test_mainview_history_context_actions_are_composed_once_and_disable_off_item`. Change both `24`
to `25`.

> Do **not** add the key to `UNSUPPORTED_MAIN_VIEWER_ACTION_KEYS`: the action is supported in the
> main window and the test asserts that everything outside that set is visible.

### Step 4.2 (RED) — Write the tests

Append to `test/widgets_history_checkout_test.py`:

```python
def _tree_with_actions(context, managed_qobject):
    """A commit tree that owns its menu actions, the way GitDAG builds them."""
    tree = _tree(context, managed_qobject)
    tree.menu_actions = dagwidget.viewer_actions(tree, tree)
    return tree


def _context_menu_event():
    position = QtCore.QPoint(-1, -1)
    return QtGui.QContextMenuEvent(
        QtGui.QContextMenuEvent.Mouse, position, position
    )


def _row_under_cursor(tree, monkeypatch, commit):
    """Make itemAt() report a row, the way a real right-click does.

    update_menu_actions() re-reads the row under the cursor and overwrites
    tree.clicked, so presetting that attribute would be thrown away (trap F13).
    """
    item = Mock()
    item.commit = commit
    monkeypatch.setattr(tree, 'itemAt', lambda _pos: item)


def test_merge_action_is_offered_for_a_branch_with_new_commits(
    qapp, app_context, managed_qobject, monkeypatch
):
    """The reported feature: a branch ahead of the current one can be merged."""
    tree = _tree_with_actions(app_context, managed_qobject)
    monkeypatch.setattr(app_context.model, 'currentbranch', 'main')
    monkeypatch.setattr(dagwidget.gitcmds, 'can_merge', lambda _context, _ref: True)
    _row_under_cursor(tree, monkeypatch, _fake_commit('a' * 40, branches=['feature']))

    tree.update_menu_actions(_context_menu_event())

    action = tree.menu_actions['merge_branch']
    assert action.isEnabled()
    assert action.text() == 'Merge "feature" into "main"'


def test_merge_action_is_disabled_when_there_is_nothing_to_merge(
    qapp, app_context, managed_qobject, monkeypatch
):
    """A branch already contained in the current one offers nothing."""
    tree = _tree_with_actions(app_context, managed_qobject)
    monkeypatch.setattr(app_context.model, 'currentbranch', 'main')
    monkeypatch.setattr(dagwidget.gitcmds, 'can_merge', lambda _context, _ref: False)
    _row_under_cursor(tree, monkeypatch, _fake_commit('a' * 40, branches=['feature']))

    tree.update_menu_actions(_context_menu_event())

    action = tree.menu_actions['merge_branch']
    assert not action.isEnabled()
    assert action.text() == 'Merge into Current Branch'


def test_merge_action_asks_git_only_when_a_ref_exists(
    qapp, app_context, managed_qobject, monkeypatch
):
    """A click that misses a row must not run git (trap F4)."""
    tree = _tree_with_actions(app_context, managed_qobject)
    asked = []
    monkeypatch.setattr(
        dagwidget.gitcmds, 'can_merge', lambda _c, ref: asked.append(ref) or True
    )
    monkeypatch.setattr(tree, 'itemAt', lambda _pos: None)

    tree.update_menu_actions(_context_menu_event())

    assert asked == []
    assert not tree.menu_actions['merge_branch'].isEnabled()


def test_merge_action_opens_the_dialog_on_that_branch(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Choosing the action reaches local_merge with the branch preselected."""
    tree = _tree_with_actions(app_context, managed_qobject)
    monkeypatch.setattr(app_context.model, 'currentbranch', 'main')
    monkeypatch.setattr(dagwidget.gitcmds, 'can_merge', lambda _context, _ref: True)
    opened = []
    monkeypatch.setattr(
        dagwidget.merge, 'local_merge', lambda context, ref=None: opened.append(ref)
    )
    tree.clicked = _fake_commit('a' * 40, branches=['feature'])

    tree.merge_branch()

    assert opened == ['feature']


def test_merge_action_does_nothing_without_a_candidate(
    qapp, app_context, managed_qobject, monkeypatch
):
    opened = []
    tree = _tree_with_actions(app_context, managed_qobject)
    monkeypatch.setattr(
        dagwidget.merge, 'local_merge', lambda context, ref=None: opened.append(ref)
    )
    tree.clicked = None

    tree.merge_branch()

    assert opened == []
```

Check which of the names the new tests use are already imported:

```bash
grep -n "^from cola.widgets import dag as dagwidget$" test/widgets_history_checkout_test.py
grep -n "^from qtpy import QtGui$" test/widgets_history_checkout_test.py
grep -n "^from unittest.mock import Mock$" test/widgets_history_checkout_test.py
```

**Expected:** the first finds a line, the second finds **nothing**. `dagwidget` is already
imported — **do not add it a second time.** Add only `QtGui`. Anchor:

```bash
grep -n "^from qtpy import QtCore$" test/widgets_history_checkout_test.py
```

Insert **directly below** that line — the group is alphabetical and `QtGui` sorts after `QtCore`:

```python
from qtpy import QtGui
```

`Mock` is needed too. If the third `grep` above found nothing, add it as the **first** import of
the file's standard-library group:

```bash
grep -n "^import subprocess$" test/widgets_history_checkout_test.py
```

Insert **directly below** `import sys` (the last line of that group):

```python
from unittest.mock import Mock
```

> `dagwidget` is the module object, which is what the monkeypatches need: `gitcmds` and `merge`
> are looked up as attributes of `cola.widgets.dag` at call time, so patching them there is what
> takes effect. If either `grep` above disagrees with the expectation: **stop and report.**

**Run RED:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py 2>&1 | tail -12
```

**Expected:** all five fail. The three that reach `update_menu_actions` fail with

```
AttributeError: module 'cola.widgets.dag' has no attribute 'gitcmds'
```

and the two that call `tree.merge_branch()` with

```
AttributeError: 'CommitTreeWidget' object has no attribute 'merge_branch'
```

### Step 4.3 (GREEN) — Wire it up

**Anchor 1 — the imports.**

```bash
grep -n "^from \.\. import guicmds$" cola/widgets/dag.py
```

Insert **directly above it** (isort orders `gitcmds` before `guicmds`):

```python
from .. import gitcmds
```

```bash
grep -n "^from \. import finder$" cola/widgets/dag.py
```

Insert **directly below it** (isort orders `merge` after `finder`):

```python
from . import merge
```

**Anchor 2 — the handler.**

```bash
grep -n "    def checkout_branch(self):" cola/widgets/dag.py
```

**Expected:** exactly **one** hit, in `ViewerMixin`. Insert **directly above it**:

```python
    def merge_candidate_ref(self):
        """Return the mergeable ref of the right-clicked row, or ''.

        The right-clicked row wins over the selection: a right-click is a
        statement about the row under the cursor. git is only asked once a ref
        exists, so a click that misses a row costs nothing.
        """
        commit = self.clicked
        if commit is None:
            selected = self.selected_item()
            commit = selected.commit if selected is not None else None
        ref = merge_candidate(commit, self.context.model.currentbranch)
        if not ref or not gitcmds.can_merge(self.context, ref):
            return ''
        return ref

    def merge_branch(self):
        """Open the merge dialog with the clicked branch already chosen"""
        ref = self.merge_candidate_ref()
        if not ref:
            return
        merge.local_merge(self.context, ref=ref)

```

**Anchor 3 — enable it and name it.**

```bash
grep -n "        self.menu_actions\['checkout_branch'\].setEnabled(bool(has_branches) and has_oid)" cola/widgets/dag.py
```

**Expected:** exactly **one** hit. Insert **directly below it**:

```python
        merge_ref = self.merge_candidate_ref()
        merge_action = self.menu_actions['merge_branch']
        merge_action.setEnabled(bool(merge_ref))
        if merge_ref:
            merge_action.setText(
                N_('Merge "%(revision)s" into "%(branch)s"')
                % {
                    'revision': merge_ref,
                    'branch': self.context.model.currentbranch,
                }
            )
        else:
            merge_action.setText(N_('Merge into Current Branch'))
```

**Anchor 4 — the action itself.**

```bash
grep -n "        'checkout_branch': set_icon(" -A 3 cola/widgets/dag.py
```

**Expected:** exactly **one** hit, three lines long, ending in `),`. Insert **directly below that
closing `),`**:

```python
        'merge_branch': set_icon(
            icons.merge(),
            qtutils.add_action(
                widget, N_('Merge into Current Branch'), proxy.merge_branch
            ),
        ),
```

**Anchor 5 — put it in the menu.**

```bash
grep -n "        menu.addAction(self.menu_actions\['checkout_branch'\])" cola/widgets/dag.py
```

**Expected:** exactly **one** hit. Insert **directly below it**:

```python
        menu.addAction(self.menu_actions['merge_branch'])
```

### Verification

```bash
garden fmt
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_checkout_test.py test/widgets_main_history_test.py test/widgets_dag_history_test.py 2>&1 | tail -3
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Expected:** baseline + 30 passed, 0 failed — the 25 from Tasks 1–3 plus 5 here. The action-set
test was edited, not added, so it does not change the count.

> **If any other test asserts on the history menu, that is a real finding, not a chore.** Report
> it with the test name instead of loosening the assertion.

### Commit

```bash
git add -A && git commit -m "feat: offer a merge in the history context menu

Right-clicking a row whose branch holds commits the current branch does not
now offers 'Merge \"<branch>\" into \"<current>\"', which opens the standard
merge dialog with that branch already chosen. The entry is disabled when there
is nothing to merge, and git is only asked once a candidate ref exists, so a
click that misses a row costs nothing.

ViewerMixin is shared by the commit list and the graph view, so both menus gain
the action."
```

---

## Task 5 — Documentation

### Step 5.1 — `references/fork-history.md`

Anchor:

```bash
grep -n "^## " .claude/skills/project-brief/references/fork-history.md
```

Insert **after** the last numbered section and **directly before** `## Where the fork's tests
live`. Take the number from the last numbered section and add one — if the last is `## 8. …`, the
new one is `## 9. …`. If there is no numbered section at all: **stop and report.**

```markdown
## <N>. Merge from the history context menu

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
```

Also extend the test list at the end of that file:

```markdown
- `test/widgets_merge_preselect_test.py` covers the merge dialog's preselection; the menu entry
  itself is covered in `test/widgets_history_checkout_test.py`.
```

### Step 5.2 — `references/gotchas.md`

Anchor:

```bash
grep -n "^## Git output$" .claude/skills/project-brief/references/gotchas.md
grep -n "^## Icons$" .claude/skills/project-brief/references/gotchas.md
```

**Expected:** exactly **one** hit each, `## Icons` after `## Git output`. Insert at the **end of
the `## Git output` section**, directly before the `## Icons` line:

```markdown
**`git merge-base --is-ancestor` does not answer "can I merge this".** It reports a diverged
branch as not an ancestor, although a diverged branch is the ordinary merge case. Count instead:
`git rev-list --count HEAD..<ref>` is greater than zero exactly when there is something to merge.
A ref that does not resolve exits 128 with empty output.
```

Then anchor the Qt section:

```bash
grep -n "^## Qt widget behavior$" .claude/skills/project-brief/references/gotchas.md
```

Append to the end of that section:

```markdown
**`ViewerMixin.menu_actions` is `None` until something assigns it.** Only `GitDAG` calls
`viewer_actions()`; a bare `CommitTreeWidget` has `None` and `update_menu_actions()` raises
`TypeError`. Tests must assign `viewer_actions(tree, tree)` themselves.

**The history's action set is asserted exactly.**
`test_mainview_history_context_actions_are_composed_once_and_disable_off_item` compares the key
set and the count twice. Adding a context-menu action means editing `VIEWER_ACTION_KEYS` and two
literals in the same file.

**Radio buttons wired with `qtutils.connect_released` do not react to `setChecked()`.** `released`
is a user gesture; changing the state in code has to run the same update by hand.
```

### Step 5.3 — `SKILL.md`

Anchor:

```bash
grep -n "work packages have shipped" .claude/skills/project-brief/SKILL.md
```

**Expected:** exactly **one** hit. Exactly one of the two lines below stands there — replace it
with the one next to it, without doing arithmetic:

| It says | Replace with |
|---|---|
| `Seven work packages have shipped:` | `Eight work packages have shipped:` |
| `Eight work packages have shipped:` | `Nine work packages have shipped:` |

If it says anything else: **stop and report.**

Also extend the enumerating sentence at its end with ", and the merge action in the history
context menu" — directly before the closing full stop.

### Step 5.4 — Mark the plan as done

Set this plan's frontmatter to `status: completed` and add `completed_at`, `plan_commit`,
`implementation_branch`, `implementation_head`, `ci_run` and `manual_verification` — as described
in `docs/plans/README.md`. Add this plan's row to the table there.

> `docs/plans/README.md` is in German. Add your row in the language the table around you uses and
> do not translate the rest as part of this plan.

### Verification

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
garden check/fmt && garden check/pyupgrade && garden check/mypy
```

**Expected:** green, unchanged. A missing tool is not a reason to abort: **note which check did
not run** and say so in the final report.

### Commit

```bash
git add -A && git commit -m "docs: document the history merge action"
```

---

## Manual acceptance

```bash
garden run
```

1. Check out a branch that is behind another one. Right-click the row where the other branch's tip
   sits: the menu shows `Merge "<other>" into "<current>"`.
2. Choose it. The standard merge dialog opens, the revision field holds that branch, the **Local
   Branch** radio is selected and the branch is **highlighted in the list**.
3. Press Merge. The merge runs exactly as it would from `Actions → Merge...`.
4. Right-click a row whose branch is already contained in the current branch: the entry is there
   but greyed out.
5. Right-click a row with no branch at all, and empty space below the last row: the entry is
   greyed out and nothing happens.
6. Right-click the row of the **current** branch: greyed out.
7. Repeat 1–2 in the standalone DAG window, in both the commit list and the graph pane — both use
   the same menu.
8. With a remote branch you do not have locally, right-click its tip: the entry offers
   `origin/<name>`, and choosing it preselects that remote branch with the **Tracking Branch**
   radio selected.

> **In an environment without a display this section does not apply.** Points 1, 4, 5, 6 and the
> preselection in 2 are covered by the tests from Tasks 1–4. **Points 3, 7 and 8 are not** — an
> actual merge, the graph pane's menu and the remote-branch path have no test coverage here.
> **Write it that way in the final report, do not present it as "checked".**
