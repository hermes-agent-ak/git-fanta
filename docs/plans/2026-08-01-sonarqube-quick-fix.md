---
status: open
---

# Low-Risk, High-Impact SonarQube Quick-Fix Implementation Plan

**Created:** 2026-08-01
**Branch:** **Dieser Plan arbeitet auf einem bereits angelegten Branch `sonarqube/findings-2/minimax-M3`, der zum Planungszeitpunkt auf `dev` (`dc150fc3`) basiert.** Die im Report urspruenglich genannten Branch-Namen pro Pull Request werden beibehalten (`chore/sonar-quick-fix-baseline`, `refactor/sonar-s1192-constants`, `refactor/sonar-s7498-literals`, `chore/sonar-mechanical-cleanup`), aber alle landen auf dem schon existierenden `sonarqube/findings-2/minimax-M3` -- also als lineare Commit-Folge statt als vier getrennte Branches. Falls die Aufteilung in vier PRs spaeter doch gewuenscht ist: jeder Task commitet einzeln (siehe PR 4), und die Branch-Aufteilung kann per `git branch -f` nachtraeglich aus den vorhandenen Commits rekonstruiert werden. **Niemals direkt auf `main` commiten.**
**Affects:** `sonar-project.properties`, alle in PR 2-4 aufgelisteten Python-Dateien unter `cola/` und `docs/`. `qtpy/` wird in PR 1 aus der SonarQube-Analyse ausgeschlossen, aber **nicht** aus dem Python-Build oder den Tests.

## Voraussetzung: aktueller Stand

- Branch `dev` ist lokal auf `dc150fc3` (Stand: 2026-08-01, "docs: document the history merge action").
- Branch `sonarqube/findings-2/minimax-M3` existiert seit dem Planungs-Setup und zeigt auf denselben Commit.
- Working tree ist clean.
- `sonar-project.properties` enthaelt aktuell nur `sonar.projectKey=git-fanta` -- `sonar.exclusions` muss fuer PR 1 neu hinzugefuegt werden (nicht anhaengen).

## Uebersicht

Ziel: moeglichst viele SonarQube-Findings entfernen, ohne Verhalten, Public APIs oder Architektur zu aendern. Vier PRs (1-4) mit klar abgegrenzten mechanischen Transformationen, optional PR 5 danach.

# 1. Objective

Reduce the largest possible number of SonarQube findings without changing application behavior, public APIs, control flow, or architecture.

Every implementation task must follow these rules:

1. Do not redesign functions.
2. Do not change public method signatures.
3. Do not rename Qt callback methods.
4. Do not combine unrelated SonarQube rules in the same pull request.
5. Do not add new abstractions unless SonarQube specifically requests a constant.
6. Run the complete test suite after every pull request.
7. Stop immediately if a transformation changes runtime behavior or requires understanding complex business logic.

# 2. Baseline and expected result

The supplied export contains:

* 617 total open issues.
* 500 issue records in the exported page.
* 3,707 minutes of total estimated remediation effort.
* 193 findings for `python:S7498`.
* 112 findings for `python:S2208`.
* 67 findings for `python:S3776`.
* 30 findings for `python:S1192`.

The safe code-change batches below should remove approximately **249 of the 500 exported findings**.

When the `qtpy` directory is confirmed as vendored third-party code, the analysis-scope change should remove another **116 findings**.

Expected total reduction:

* Code-only quick fixes: approximately **249 findings**.
* Code fixes plus justified `qtpy` exclusion: approximately **365 findings**.
* Expected reduction from the exported page: approximately **73%**.

These are target values, not guarantees. SonarQube may combine, move, or recalculate findings after each analysis.

---

# Pull Request 0 -- Establish the Safety Baseline

## Purpose

Ensure that later mechanical changes can be proven not to alter behavior.

## Steps

1. **Branch existiert bereits** als `sonarqube/findings-2/minimax-M3` auf Basis von `dev` (`dc150fc3`). Kein neuer Branch noetig; falls die Vier-PR-Aufteilung spaeter rekonstruiert wird, wird der erste Commit dieses PR der Initial-Commit von `chore/sonar-quick-fix-baseline`.

2. Run the complete existing test suite without changing any source files.

3. Run at least:

```bash
python -m compileall -q cola qtpy docs
python -m pytest
git diff --check
```

4. Record:

```text
Tests passed:
Tests failed:
SonarQube total:
Critical:
Major:
Minor:
```

5. Do not begin the following pull requests unless the existing test suite passes.

## Acceptance criteria

* No source files changed.
* Existing test failures are documented.
* A baseline SonarQube analysis is stored for comparison.

---

# Pull Request 1 -- Correct the SonarQube Scope for Vendored QtPy Code

## Impact

Expected removal from the supplied export:

* 112 `python:S2208` findings.
* 3 `python:S1542` findings.
* 1 `python:S7504` finding.
* Total: **116 findings**.

## Important gate

Perform this pull request only when `qtpy/` is treated as copied, vendored, or upstream-synchronized third-party compatibility code.

Do not exclude `qtpy/` when this project intentionally maintains and develops that package as first-party product code.

SonarQube recommends excluding library or generated source code that the project does not actively maintain.

## Implementation

Open:

```text
sonar-project.properties
```

The file currently contains only:

```properties
sonar.projectKey=git-fanta
```

Add `sonar.exclusions` as a new property (no existing one to merge into):

```properties
sonar.projectKey=git-fanta
sonar.exclusions=qtpy/**/*
```

Do not use a broad pattern such as:

```properties
**/qtpy/**/*
```

The broad pattern could unintentionally exclude test fixtures or unrelated nested directories.

## Do not implement this alternative

Do not replace the wildcard imports inside `qtpy` with manually enumerated imports. The package is a compatibility facade, and changing its exported names may break consumers.

## Verification

Run:

```bash
python -c "import qtpy; from qtpy import QtCore, QtGui, QtWidgets"
python -m pytest
```

Run SonarQube again and verify:

1. Files under `qtpy/` are excluded.
2. Files under `cola/` remain analyzed.
3. Approximately 116 findings disappear.
4. No import test fails.

## Acceptance criteria

* Only SonarQube configuration changes.
* No Python source file changes.
* No directory except `qtpy/` disappears from analysis.
* The reason for the exclusion is documented in the pull-request description.

---

# Pull Request 2 -- Replace Duplicated Literals with File-Local Constants

## SonarQube rule

```text
python:S1192
```

## Impact

Expected removal:

```text
30 critical findings
```

## Branch

```text
sonarqube/findings-2/minimax-M3
```

(Urspruenglich `refactor/sonar-s1192-constants`. Da wir linear auf einem Branch arbeiten, nur der Commit-Titel enthaelt den PR-Namen.)

## General implementation rule

For each reported literal:

1. Search the complete file for the exact literal.
2. Confirm that every occurrence has the same meaning.
3. Add one uppercase constant near the existing module constants.
4. Replace only occurrences with that exact meaning.
5. Keep the constant inside the same module.
6. Do not create a shared constants module.
7. Do not create a generic string dictionary.

Example:

```python
SAFE_MODE_CONFIG_KEY = 'fanta.safemode'
```

Replace:

```python
config.get('fanta.safemode')
config.set('fanta.safemode', value)
```

with:

```python
config.get(SAFE_MODE_CONFIG_KEY)
config.set(SAFE_MODE_CONFIG_KEY, value)
```

## Translation strings

For strings wrapped in `N_()`, place the translation marker in the constant definition:

```python
JAPANESE_TRANSLATION = N_('Japanese translation')
```

Then use:

```python
title=JAPANESE_TRANSLATION
```

Do not use this pattern:

```python
JAPANESE_TRANSLATION = 'Japanese translation'
title=N_(JAPANESE_TRANSLATION)
```

Translation extraction tools may require the literal to appear directly inside `N_()`.

## Exact findings to process

### `cola/cmds.py`

* Line 675: `'git reset'`, repeated 3 times.
* Line 719: `'Reset and Restore'`, repeated 3 times.
* Line 832: `'Undo Last Commit'`, repeated 3 times.
* Line 1121: `'Sync out failed'`, repeated 4 times.
* Line 2981: `'fanta.safemode'`, repeated 3 times.

Suggested names:

```python
GIT_RESET_COMMAND
RESET_AND_RESTORE_LABEL
UNDO_LAST_COMMIT_LABEL
SYNC_OUT_FAILED_MESSAGE
SAFE_MODE_CONFIG_KEY
```

### `cola/guicmds.py`

* Line 386: `'HEAD^'`, repeated 6 times.
* Line 408: `'Reset and Restore'`, repeated 3 times.

Suggested names:

```python
HEAD_PARENT_REVISION
RESET_AND_RESTORE_LABEL
```

### `cola/icons.py`

* Line 17: `'file-code.svg'`, repeated 26 times.
* Line 138: `'circle-slash-red.svg'`, repeated 3 times.
* Line 153: `'modified.svg'`, repeated 4 times.
* Line 155: `'git-compare.svg'`, repeated 3 times.

Suggested names:

```python
FILE_CODE_ICON
CIRCLE_SLASH_RED_ICON
MODIFIED_ICON
GIT_COMPARE_ICON
```

### `cola/main.py`

* Line 135: `'<ref>'`, repeated 3 times.
* Line 178: `'<args>'`, repeated 3 times.
* Line 395: `"passed to 'git apply' by 'git rebase'"`, repeated 3 times.

Suggested names:

```python
REF_PLACEHOLDER
ARGS_PLACEHOLDER
GIT_REBASE_APPLY_DESCRIPTION
```

### `cola/models/stash.py`

* Line 74: `'git stash '`, repeated 3 times.

Suggested name:

```python
GIT_STASH_PREFIX
```

### `cola/widgets/about.py`

* Line 433: `'Traditional Chinese (Taiwan) translation'`, repeated 3 times.
* Line 437: `'French translation'`, repeated 3 times.
* Line 438: `'Spanish translation'`, repeated 3 times.
* Line 440: `'Brazilian translation'`, repeated 3 times.
* Line 442: `'Japanese translation'`, repeated 4 times.
* Line 449: `'Turkish translation'`, repeated 3 times.
* Line 458: `'German translation'`, repeated 3 times.

Suggested names:

```python
TRADITIONAL_CHINESE_TAIWAN_TRANSLATION
FRENCH_TRANSLATION
SPANISH_TRANSLATION
BRAZILIAN_TRANSLATION
JAPANESE_TRANSLATION
TURKISH_TRANSLATION
GERMAN_TRANSLATION
```

### `cola/widgets/completion.py`

* Line 834: `'<branch>'`, repeated 3 times.
* Line 842: `'<path>'`, repeated 3 times.

Suggested names:

```python
BRANCH_PLACEHOLDER
PATH_PLACEHOLDER
```

### `cola/widgets/createbranch.py`

* Line 84: `'Create Branch'`, repeated 3 times.

Suggested name:

```python
CREATE_BRANCH_LABEL
```

### `cola/widgets/dag.py`

* Line 1545: `'Zoom to Fit'`, repeated 3 times.

Suggested name:

```python
ZOOM_TO_FIT_LABEL
```

### `cola/widgets/main.py`

* Line 468: `'<commit>'`, repeated 6 times.

Suggested name:

```python
COMMIT_PLACEHOLDER
```

### `cola/widgets/status.py`

* Line 840: `'Unstage Selected'`, repeated 3 times.
* Line 889: `'Stage Selected'`, repeated 3 times.

Suggested names:

```python
UNSTAGE_SELECTED_LABEL
STAGE_SELECTED_LABEL
```

### `cola/widgets/toolbarcmds.py`

* Line 129: `'<commit>'`, repeated 5 times.

Suggested name:

```python
COMMIT_PLACEHOLDER
```

## Verification

```bash
python -m compileall -q cola
python -m pytest
git diff --check
```

Search for each literal after implementation. Every remaining duplicate must either:

* Have a different semantic meaning, or
* Be replaced by the new constant.

## Acceptance criteria

* Zero remaining `python:S1192` findings from this batch.
* Exactly one constant per duplicated meaning per file.
* No constants shared across unrelated modules.
* No UI text changes.
* No translation text changes.
* No method signatures changed.

---

# Pull Request 3 -- Replace Constructor Calls with Literals

## SonarQube rule

```text
python:S7498
```

## Impact

Expected removal:

```text
193 minor findings
```

## Branch

```text
sonarqube/findings-2/minimax-M3
```

(Urspruenglich `refactor/sonar-s7498-literals`.)

## Files and expected issue counts

```text
cola/widgets/about.py       182
docs/conf.py                  5
cola/models/main.py           3
cola/display.py               2
cola/widgets/filelist.py      1
                            ---
Total                       193
```

## Allowed transformations

Apply only these direct transformations:

```python
dict()       -> {}
list()       -> []
tuple()      -> ()
str()        -> ''
bytes()      -> b''
```

For keyword-only dictionaries:

```python
dict(name='Daniel Harding', title=N_('Developer'))
```

becomes:

```python
{'name': 'Daniel Harding', 'title': N_('Developer')}
```

The current `about.py` author and translator collections contain many keyword-based `dict(...)` entries matching this pattern.

For a multiline dictionary:

```python
dict(
    name='David Aguilar',
    title=N_('Maintainer'),
    email=email,
)
```

use:

```python
{
    'name': 'David Aguilar',
    'title': N_('Maintainer'),
    'email': email,
}
```

## Mandatory formatting rules

1. Use single quotes because the surrounding project code uses single quotes.
2. Preserve the original key order.
3. Preserve trailing commas in multiline literals.
4. Do not move entries.
5. Do not reorder authors or translators.
6. Do not change string contents.
7. Do not combine this work with duplicate-string constants.
8. Run the formatter only on touched files.

## Forbidden transformations

Do not automatically transform:

```python
set()
frozenset()
dict(existing_mapping)
dict(existing_mapping, key=value)
list(generator)
tuple(generator)
```

These cases either lack an equivalent literal or can have different evaluation and error behavior.

Also do not transform a call when `dict`, `list`, `tuple`, `str`, or `bytes` has been shadowed by a local variable or imported name.

## Implementation order

1. Fix `cola/widgets/about.py`.
2. Compile and test.
3. Fix `docs/conf.py`.
4. Compile documentation.
5. Fix the remaining three application files.
6. Run the complete test suite.
7. Run SonarQube.

## Verification

```bash
python -m compileall -q cola docs
python -m pytest
git diff --check
```

Inspect the diff using:

```bash
git diff --word-diff
```

The word diff must show only constructor syntax changing into literal syntax.

## Acceptance criteria

* All 193 exported `python:S7498` findings are resolved.
* No collection contents change.
* No collection type changes.
* No names, strings, translations, or ordering change.
* All tests pass.

---

# Pull Request 4 -- Mechanical Dead-Code and Expression Cleanup

## Impact

Expected removal:

```text
Approximately 26 findings
```

## Branch

```text
sonarqube/findings-2/minimax-M3
```

(Urspruenglich `chore/sonar-mechanical-cleanup`. Jeder Task wird als einzelner Commit committed, damit eine fehlerhafte Transformation unabhaengig revertierbar bleibt.)

Each rule should be committed separately inside the branch so an incorrect transformation can be reverted independently.

## Task 4.1 -- Remove redundant control-flow statements

Rule:

```text
python:S3626
```

Locations:

```text
cola/cmds.py                122, 3042
cola/fsmonitor.py           117
cola/sequenceeditor.py      366
cola/widgets/standard.py    616
cola/widgets/text.py        254, 258, 262
```

Implementation:

* Delete a final `return` only when reaching the end of the function returns the same value, normally `None`.
* Delete a `continue` only when the loop would continue immediately without executing another statement.
* Do not delete `return value`.
* Do not delete a return inside `try`, `finally`, or context-manager cleanup without manually verifying behavior.

Expected reduction:

```text
8 findings
```

## Task 4.2 -- Merge implicit string concatenations

Rule:

```text
python:S5799
```

Locations:

```text
cola/main.py                              312, 358, 370, 377
extras/sphinxtogithub/sphinxtogithub.py   277
```

Implementation:

Replace adjacent literals with one literal while preserving the exact final value.

Before:

```python
'first part '
'second part'
```

After:

```python
'first part second part'
```

Use a quick assertion when the string is nontrivial:

```python
assert new_value == old_expected_value
```

Expected reduction:

```text
5 findings
```

## Task 4.3 -- Use `startswith()`

Rule:

```text
python:S6659
```

Locations:

```text
cola/gitcmds.py   599
cola/polib.py     1458, 1467
```

Typical transformation:

```python
value[: len(prefix)] == prefix
```

becomes:

```python
value.startswith(prefix)
```

Do not change case sensitivity.

Expected reduction:

```text
3 findings
```

## Task 4.4 -- Remove unused assignments

Rule:

```text
python:S1854
```

Locations:

```text
cola/widgets/prefs.py     343
cola/widgets/toolbar.py   250
```

Implementation:

When the right-hand side is a literal or pure expression, remove the complete assignment.

Before:

```python
tooltip = 'Some text'
```

After:

```python
# Assignment removed.
```

When the right-hand side calls a function that may have side effects, preserve the call:

```python
unused = perform_action()
```

becomes:

```python
perform_action()
```

Expected reduction:

```text
2 findings
```

## Task 4.5 -- Replace unused unpacked values with `_`

Rule:

```text
python:S1481
```

Locations:

```text
cola/gitcmds.py       1187: status
cola/models/main.py    803: err
```

Before:

```python
status, output = command()
```

After:

```python
_, output = command()
```

Do not alter the number of unpacked values.

Expected reduction:

```text
2 findings
```

## Task 4.6 -- Delete commented-out code

Rule:

```text
python:S125
```

Locations:

```text
bin/_activate_fanta.py       29
cola/widgets/imageview.py   440
```

Delete only executable code that was commented out.

Keep comments that explain:

* Why the code exists.
* Platform limitations.
* Workarounds.
* External compatibility requirements.
* Non-obvious behavior.

Expected reduction:

```text
2 findings
```

## Task 4.7 -- Remove unnecessary `list()` wrappers

Rule:

```text
python:S7504
```

Locations:

```text
cola/widgets/main.py   1048
qtpy/uic.py             203
```

When Pull Request 1 excludes `qtpy`, only change `cola/widgets/main.py`.

Before:

```python
for item in list(existing_iterable):
```

After:

```python
for item in existing_iterable:
```

Do not remove `list()` when the underlying collection is mutated during iteration.

Expected reduction:

```text
1 or 2 findings
```

## Task 4.8 -- Remove redundant calls

Rule:

```text
python:S7508
```

Locations:

```text
cola/models/selection.py          39
cola/widgets/diff_intraline.py   288
```

If the same pure function is called twice with identical arguments, evaluate it once:

```python
value = calculate_value(argument)
```

Then reuse `value`.

Do not simply delete a call when it may have side effects.

Expected reduction:

```text
2 findings
```

## Verification

After each task:

```bash
python -m compileall -q cola
python -m pytest
git diff --check
```

## Acceptance criteria

* No public method signature changes.
* No control-flow redesign.
* No new helper functions.
* No output string changes.
* No changes to exception handling.
* Every removed statement is proven redundant by tests or direct equivalence.

---

# Pull Request 5 -- Optional Small Reliability Fixes

Do this only after Pull Requests 1-4 have passed.

## Floating-point comparisons

Rule:

```text
python:S1244
```

Locations from the report:

```text
cola/widgets/dag.py   1134
cola/widgets/dag.py   1399
```

Replace comparisons against zero with an explicit tolerance:

```python
math.isclose(value, 0.0, rel_tol=0.0, abs_tol=1e-9)
```

For example:

```python
if self._expand_progress == 0.0:
```

becomes:

```python
if math.isclose(
    self._expand_progress,
    0.0,
    rel_tol=0.0,
    abs_tol=1e-9,
):
```

The current module already imports `math`, so no new dependency is required.

Add or update tests covering:

1. Exact zero.
2. A very small positive value.
3. A normal animation value such as `0.5`.
4. The final hover-state cleanup.

Expected reduction:

```text
2 major bug findings
```

Do not include these changes in the bulk mechanical pull requests because tolerance selection is a behavioral decision.

---

# Findings Explicitly Excluded from This Plan

## Cognitive complexity

Rule:

```text
python:S3776
```

Count in export:

```text
67 findings
```

Do not ask a basic AI agent to fix these automatically. These changes require extracting helpers, understanding state, and verifying complex control flow.

Especially avoid automated refactoring of:

```text
cola/models/graph.py
cola/widgets/filelist.py
cola/intraline_diff.py
cola/diffparse.py
cola/polib.py
cola/cmds.py
cola/widgets/dag.py
```

## Constant-condition and constant-return findings

Do not automatically modify:

```text
python:S3516
python:S5797
```

These findings can indicate real logic defects. Deleting the condition may hide the underlying bug.

## Type-contract findings

Do not automatically modify:

```text
python:S5655
python:S5886
python:S5890
python:S1226
```

These require determining the intended runtime type rather than merely changing annotations.

## Framework callback naming

Do not rename methods such as:

```text
activeWindow
dragEnterEvent
dragMoveEvent
dragLeaveEvent
dropEvent
resizeEvent
showEvent
changeEvent
```

Qt invokes or overrides these names according to its framework API. Renaming them to satisfy snake-case rules can break runtime behavior.

Mark confirmed framework callbacks as accepted exceptions in SonarQube rather than changing the names.

## HTTP findings

Do not blindly replace HTTP with HTTPS for `python:S5332`.

First verify that:

1. The server supports HTTPS.
2. Redirects behave correctly.
3. Certificate validation succeeds.
4. Tests do not depend on the exact URL.

## TODO comments

Do not remove TODO comments merely to reduce the issue count. Either implement the described task or mark it as intentionally deferred with a tracking issue.

---

# Required Pull-Request Template

Use this description for every quick-fix pull request:

```text
## SonarQube rule

<rule key>

## Scope

<files changed>

## Mechanical transformation

<exact before/after transformation>

## Expected issue reduction

<number>

## Behavior changes

None expected.

## API changes

None.

## Verification

- [ ] Python compilation passed
- [ ] Unit tests passed
- [ ] Existing CI passed
- [ ] git diff --check passed
- [ ] SonarQube analysis completed
- [ ] Target findings disappeared
- [ ] No unrelated findings were introduced
```

# Final completion criteria

The quick-fix initiative is complete when:

1. Pull Requests 1-4 are merged independently.
2. The full test suite passes after every merge.
3. A new SonarQube export is generated.
4. The second page of the original 617 findings is reviewed.
5. No `python:S1192` finding remains in the targeted files.
6. No `python:S7498` finding remains in the targeted files.
7. No first-party source directory was accidentally excluded.
8. No Qt callback or public API was renamed.
9. Cognitive-complexity work remains in a separate backlog.

# Lokale Toolings (Erinnerung)

Aus frueheren Erfahrungen (siehe Memory): Vor jedem Commit muss **beides** lokal laufen, sonst reisst CI:

```bash
# cercis
/tmp/cercis-env/bin/cercis cola/ docs/

# isort (mit den projektspezifischen Flags aus garden.yaml)
/tmp/cercis-env/bin/isort --force-single-line-imports --py=39 --no-lines-before=STDLIB cola/ docs/
```

Nicht mit dem Projektvenv mischen -- `cercis` 0.2.5 und `isort` 8.0.1 liegen ausschliesslich in `/tmp/cercis-env/`.
