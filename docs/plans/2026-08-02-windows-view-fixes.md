# Default layout and the Windows item-view rendering

**Created:** 2026-08-02
**Branch:** commit onto whatever branch is checked out when you start. **Never onto `main`** —
check with `git rev-parse --abbrev-ref HEAD` before Task 1 and create a feature branch first if it
says `main` or `dev`. This plan does not switch branches.
**Baseline:** every reference below was verified against `79c5c8a8`. Re-verify a line number
before you edit it — run the `grep` given with each task rather than trusting the number.
**Affects:** `fanta/widgets/main.py` (dock arrangement), `fanta/themes.py` (item-view styling),
`fanta/widgets/dag.py` (the history controls row and the graph delegate), plus four test files.

---

## 0. How to read this plan

Each task is **RED → GREEN → VERIFY**. Write the failing test first, watch it fail for the stated
reason, then make it pass. Do not skip the RED step: several of these tests would pass by accident
against the current code if written after the change.

**Everything you write is English** — code comments, test names, test docstrings and commit
messages. The conversation may be German; the artifacts are not.

**Run tests like this** (the repository needs `python`, not just `python3`, on `PATH`, and
`test/widgets_main_history_test.py` must run in its own process — see
`docs/plans/2026-08-02-release-readiness.md`):

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/<file> -p no:ruff -q
```

If `env3/` does not exist yet:

```bash
python3 -m venv --system-site-packages env3
```

**Bundle the commits.** The maintainer asked for fewer, larger commits. Make **two** commits
total: one for Task 1, one for Tasks 2–5. Do not commit after every task.

---

## 1. What is actually wrong

Five defects, one layout change. Everything below was read out of the tree, not assumed.

### 1.1 The item-view defects share one root cause

`fanta/themes.py:583` `style_sheet_default()` — the stylesheet for the **Default** theme, which is
what a fresh install uses — styles splitters, separators, checkboxes and radios, and **nothing
else**. It contains no `QAbstractItemView` rule at all. Confirm:

```bash
sed -n '583,672p' fanta/themes.py | grep -c "QAbstractItemView"
```

**Expected: `0`.**

So with the default theme every tree and list is painted by the **platform style**: Fusion or
Breeze on Linux, `windowsvista` on Windows. Those two disagree about item painting, and the
Windows one is what the maintainer is seeing:

| Reported symptom | What windowsvista does |
|---|---|
| a dotted border around the selected file | draws the focus rectangle as a dotted outline |
| the blue background has padding all round it | insets the selection rect inside the item rect |
| ~2 px above and below, white in between | that inset leaves the row background showing |
| hover paints a blue background in every table | draws a hover gradient on `State_MouseOver` |

The *same* stylesheet mechanism already solves this for the **Flat** themes at
`fanta/themes.py:167-172`, which set `QAbstractItemView::item:selected` and `::item:hover`
explicitly. **Reuse those rules.** Do not write a new delegate, do not subclass `QStyle`, and do
not branch on `utils.is_win32()`: rules built from the palette make both platforms agree, and the
maintainer's stated goal is that Windows should look like Linux.

### 1.2 The history rows have a second, independent cause

`fanta/widgets/dag.py:2144` installs `GraphDelegate` **only on the Summary column**:

```python
self.setItemDelegateForColumn(CommitTreeWidgetItem.SUMMARY, delegate)
```

Columns are `SUMMARY = 0`, `AUTHOR = 1`, `OID = 2`, `DATE = 3` (`dag.py:2011-2014`). So Author,
Hash and Date are painted by the default delegate and Summary by ours. Two consequences:

- **Selection.** `GraphDelegate.paint()` fills the whole rect (`dag.py:1636-1638`):

  ```python
  selected = bool(option.state & QtWidgets.QStyle.State_Selected)
  if selected:
      painter.fillRect(rect, option.palette.highlight())
  ```

  The other three columns get the platform's inset selection. On Windows the Summary column is
  filled edge to edge while its neighbours are not, which is what makes the summary row look
  taller than the rest. **It is not a row-height difference.** All four columns are in the same row; only the
  fill differs. Task 3's stylesheet rule removes the inset and makes them match.

- **Hover.** `dag.py:2073-2074` turns on mouse tracking:

  ```python
  self.setMouseTracking(True)
  self.viewport().setMouseTracking(True)
  ```

  which is what produces `State_MouseOver`. `GraphDelegate.paint()` never reads that flag, so
  Summary stays unpainted while Author/Hash/Date light up, which is the reported effect of the
  author column and everything right of it looking selected. Mouse tracking is **load-bearing**:
  `dag.py` uses it for
  the label hit-testing (`_label_hit_test`, `dag.py:1917`). **Do not turn it off.** Task 4 makes
  the delegate honour hover so all four columns agree.

### 1.3 The history filter row is cramped

`fanta/widgets/dag.py:2437-2440`:

```python
self.revtext = GitDagLineEdit(context)
self.revtext.setText(ref)
self.maxresults = standard.SpinBox(digits=None, maxi=9999999, wrap=True)
```

`standard.SpinBox` already knows how to size itself — `fanta/widgets/standard.py:906-909`:

```python
if digits is not None:
    text_width = qtutils.text_width(self.font(), 'M' * digits)
    width = max(self.minimumWidth(), text_width)
    self.setMinimumWidth(width)
```

Passing `digits=None` **switches that off**, so the spin box falls back to the platform's minimum,
which on Windows is narrow enough that the number touches the buttons. The height comes from
`dag.py:2936`:

```python
self.maxresults.setMinimumHeight(self.revtext.sizeHint().height())
```

so the spin box inherits whatever the line edit reports — and on Windows `QLineEdit.sizeHint()` is
several pixels shorter than on Linux, which is the missing padding around `--all`.

**The fix is to use the parameter that already exists**, plus one font-derived minimum height for
both widgets. Do not add a stylesheet for this and do not hard-code pixel values.

### 1.4 The default dock layout

`fanta/widgets/main.py:928-951` arranges the docks. Today:

```
top    = status, history, commit (browser tabbed onto commit),
         branch (submodules, bookmarks, recent tabbed onto it)
bottom = diff, actions (log tabbed onto it)
```

Wanted:

```
┌──────────────────────────┬──────────┐
│        History           │ Branches │
│        (large)           │          │
├─────────┬────────┬───────┴──────────┤
│ Status  │  Diff  │ Commit message   │
└─────────┴────────┴──────────────────┘
```

Actions and Log stay hidden, exactly as now (`qtutils.hide_dock` at `main.py:108` and `:211`).

**Do not bump `widget_version`.** It is `2` and three tests assert that:
`test/widgets_main_history_test.py:300`, `test/widgets_main_history_test.py:1498`,
`test/widgets_dag_history_test.py:1989`. Bumping it would also discard every existing user's saved
layout. You do not need to: `MainWindow.init_state()` captures the arranged layout as
`default_state` (`fanta/widgets/standard.py:230-233`), and `apply_state()` only overrides it when
the user has a saved `windowstate` (`standard.py:267-285`). Changing the arrangement therefore
changes the default for new users and leaves existing users alone — which is exactly what is
wanted.

---

## 2. What you cannot verify here, and what to do about it

**CI runs Linux (offscreen) and macOS. There is no Windows runner.** Every acceptance criterion in
this plan is therefore written as something a Linux offscreen test can assert — the *stylesheet
text*, the *delegate's behaviour given a state flag*, the *widget's minimum size*, the *dock
areas*. None of them is a screenshot comparison.

That means Tasks 2–5 are verified as "the rule is present and the code honours it", not as "it
looks right on Windows". Section 8 lists the manual Windows checks that close that gap. **Do not
mark this plan completed until those have been run**, and record the result in the frontmatter's
`manual_verification` field.

---

## Task 1 — The default dock layout

### RED

Add to `test/widgets_main_history_test.py`. Copy the fixtures already at the top of that file
(`qapp`, `main_context`, `managed_qobject`, `_show`) — do **not** write new ones.

```python
def test_the_default_layout_puts_history_and_branches_side_by_side(
    qapp, main_context, managed_qobject
):
    """A fresh install gets the maintainer's arrangement, not the inherited one.

    Existing users keep their saved layout: apply_state() only overrides the
    arrangement when a windowstate was stored.
    """
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)

    top = QtCore.Qt.TopDockWidgetArea
    bottom = QtCore.Qt.BottomDockWidgetArea

    assert window.dockWidgetArea(window.historydock) == top
    assert window.dockWidgetArea(window.branchdock) == top
    assert window.dockWidgetArea(window.statusdock) == bottom
    assert window.dockWidgetArea(window.diffdock) == bottom
    assert window.dockWidgetArea(window.commitdock) == bottom


def test_the_default_layout_does_not_tab_history_behind_anything(
    qapp, main_context, managed_qobject
):
    """History is the largest pane; a tab would hide it behind Branches."""
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)

    assert window.tabifiedDockWidgets(window.historydock) == []
    assert window.historydock.isVisible()


def test_the_default_layout_gives_history_the_most_room(
    qapp, main_context, managed_qobject
):
    """History is the pane the maintainer works in; it gets the largest share.

    Compare against the live geometry, never against pixel constants: the
    offscreen platform and a real desktop lay out at different sizes.
    """
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    qapp.processEvents()

    assert window.historydock.width() > window.branchdock.width()
    assert window.historydock.height() > window.statusdock.height()


def test_the_bottom_row_stays_draggable(qapp, main_context, managed_qobject):
    """The initial height cap must be lifted, or the splitter is stuck."""
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    qapp.processEvents()
    QtTest.QTest.qWait(10)
    qapp.processEvents()

    for dock in (window.statusdock, window.diffdock, window.commitdock):
        assert dock.widget().maximumHeight() >= defs.max_size


def test_the_default_layout_keeps_actions_and_log_hidden(
    qapp, main_context, managed_qobject
):
    """Characterization: these two were hidden before and stay hidden."""
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)

    assert not window.actionsdock.isVisible()
    assert not window.logdock.isVisible()
```

Run it:

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_main_history_test.py -p no:ruff -q -k default_layout
```

**Expected failure:** the first test fails on `dockWidgetArea(window.statusdock) == bottom` —
status is currently in the **top** area (`main.py:931`). If it fails on a different assertion,
stop and re-read `main.py:928-951`; the tree has moved.

`test_the_bottom_row_stays_draggable` needs `defs` and `QtTest`; check the file's imports first
and add only what is missing:

```bash
grep -n "from fanta.widgets import defs\|from qtpy import QtTest" test/widgets_main_history_test.py
```

### GREEN

Find the block:

```bash
grep -n "Arrange dock widgets" fanta/widgets/main.py
```

Replace everything from `# Arrange dock widgets` up to and including `self.branchdock.raise_()`
and the three `addDockWidget(bottom, ...)` lines plus the `tabifyDockWidget(self.actionsdock,
self.logdock)` line with:

```python
        # Arrange dock widgets
        #
        # ┌──────────────────────────┬──────────┐
        # │        History           │ Branches │
        # ├─────────┬────────┬───────┴──────────┤
        # │ Status  │  Diff  │ Commit message   │
        # └─────────┴────────┴──────────────────┘
        #
        # This is the default for a fresh install only. A user with a saved
        # windowstate keeps it: MainWindow.apply_state() restores that instead
        # (cola/widgets/standard.py). Changing the arrangement therefore needs
        # no widget_version bump -- and bumping it would discard every saved
        # layout and break three tests that assert widget_version == 2.
        bottom = Qt.BottomDockWidgetArea
        top = Qt.TopDockWidgetArea

        # Top row: History fills the left, Branches sits to its right.
        self.addDockWidget(top, self.historydock)
        self.addDockWidget(top, self.branchdock)
        self.splitDockWidget(self.historydock, self.branchdock, Qt.Horizontal)

        # The Branches dock keeps its companions as tabs.
        self.addDockWidget(top, self.submodulesdock)
        self.addDockWidget(top, self.bookmarksdock)
        self.addDockWidget(top, self.recentdock)
        self.tabifyDockWidget(self.branchdock, self.submodulesdock)
        self.tabifyDockWidget(self.submodulesdock, self.bookmarksdock)
        self.tabifyDockWidget(self.bookmarksdock, self.recentdock)
        self.branchdock.raise_()

        # Bottom row: the current changes, left to right.
        self.addDockWidget(bottom, self.statusdock)
        self.addDockWidget(bottom, self.diffdock)
        self.addDockWidget(bottom, self.commitdock)
        self.splitDockWidget(self.statusdock, self.diffdock, Qt.Horizontal)
        self.splitDockWidget(self.diffdock, self.commitdock, Qt.Horizontal)
        if self.browser_dockable:
            self.addDockWidget(bottom, self.browserdock)
            self.tabifyDockWidget(self.browserdock, self.commitdock)
            self.commitdock.raise_()

        self.addDockWidget(bottom, self.actionsdock)
        self.addDockWidget(bottom, self.logdock)
        self.tabifyDockWidget(self.actionsdock, self.logdock)
```

Then give the rows and columns their proportions. **Read this paragraph before you write the
code — the obvious approach does not work.**

`resizeDocks(..., Qt.Horizontal)` works and is what sets the column widths. `resizeDocks(...,
Qt.Vertical)` across the **top and bottom dock areas does nothing at all** — measured on PyQt5
5.15.18, offscreen, both before and after `show()`:

```
resizeDocks([history, status], [2, 1], Qt.Vertical)
  ->  History h=397   Status h=397      (unchanged; the requested 2:1 is ignored)
resizeDocks([history, branches], [3, 1], Qt.Horizontal)
  ->  History b=896   Branches b=298    (works)
```

Qt only resizes docks that share an area. The height split between the top and bottom rows comes
from what the docks in each row ask for, so the lever is a temporary maximum height on the bottom
row, released once the first layout has happened. Measured with that lever: History `h=528`,
Status `h=266` — the intended 2:1.

Add to `set_initial_size` (`fanta/widgets/main.py:1033`), after the existing `self.resize(...)`
line. `init_state` calls it only when there is no saved layout, which is exactly when the default
should apply:

**Block 1 — append these lines to the body of `set_initial_size`**, at the same indentation as the
`self.resize(...)` line already there (8 spaces):

```python
        # Column widths. resizeDocks() takes relative weights, not pixels.
        self.resizeDocks([self.historydock, self.branchdock], [3, 1], Qt.Horizontal)
        self.resizeDocks(
            [self.statusdock, self.diffdock, self.commitdock], [1, 2, 1], Qt.Horizontal
        )
        # Row heights. resizeDocks(..., Qt.Vertical) cannot do this: it only
        # resizes docks that share a dock area, and these are in the top and
        # bottom areas. Measured -- it leaves both rows at exactly half the
        # window. Capping the bottom row instead makes Qt give the rest to
        # History; the cap is lifted again on the next event-loop turn so the
        # user can still drag the splitter anywhere.
        bottom_row = (self.statusdock, self.diffdock, self.commitdock)
        for dock in bottom_row:
            dock.widget().setMaximumHeight(self._initial_bottom_row_height())
        QtCore.QTimer.singleShot(0, lambda: self._release_bottom_row_height(bottom_row))
```

**Block 2 — add these as two new methods on `MainView`**, siblings of `set_initial_size`, directly
below it (4 spaces, i.e. the same indentation as `def set_initial_size`):

```python
    def _initial_bottom_row_height(self):
        """Return the height the bottom row starts at, in pixels"""
        return max(200, self.height() // 3)

    def _release_bottom_row_height(self, docks):
        """Lift the temporary cap so the splitter is draggable again"""
        for dock in docks:
            widget = dock.widget()
            if widget is not None:
                widget.setMaximumHeight(defs.max_size)
```

`defs.max_size` is `scale(4096)` (`fanta/widgets/defs.py:37`) and is what this project already
uses for "no limit"; do not write `16777215`. Check that `defs` and `QtCore` are imported in
`main.py` before you use them:

```bash
grep -n "^from .widgets import defs\|import defs\|from qtpy import QtCore" fanta/widgets/main.py
```

### VERIFY

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_main_history_test.py -p no:ruff -q
```

**All tests in the file must pass**, including `test_mainview_restores_a_legacy_v2_layout...`
around line 285, which restores a stored v2 layout. If *that* one breaks you have bumped
`widget_version` or renamed a dock — undo it.

**Commit now** (this is commit 1 of 2):

```
feat: make the history-first arrangement the default layout
```

---

## Task 2 — The history filter row

### RED

Add to `test/widgets_dag_history_test.py`, reusing its `qapp`, `app_context` and
`managed_qobject` fixtures.

```python
def test_the_history_filter_row_is_readable(qapp, app_context, managed_qobject):
    """The revision field and the count both need room for their text.

    standard.SpinBox sizes itself from a digit count, and passing digits=None
    turns that off -- on Windows the number then touches the spin buttons.
    """
    widget = managed_qobject(CommitHistoryWidget(app_context))
    _show(qapp, widget)

    line_height = widget.revtext.fontMetrics().height()

    assert widget.maxresults.minimumWidth() > 0
    assert widget.revtext.minimumHeight() >= line_height
    assert widget.maxresults.minimumHeight() >= line_height
```

Run:

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py -p no:ruff -q -k filter_row
```

**Expected failure:** `assert widget.maxresults.minimumWidth() > 0` — `digits=None` means no
minimum width is ever set.

`CommitHistoryWidget` is imported in that file (`test/widgets_dag_history_test.py:23`) and
`QtCore`, `QtGui`, `QtTest` and `QtWidgets` are all available (`:44-47`). **`_show` is not** — it
lives in `test/widgets_main_history_test.py`. Either copy that helper verbatim into the DAG test
file or replace `_show(qapp, widget)` with the `widget.show()` + `qapp.processEvents()` pair the
neighbouring tests in that file already use; check what they do first:

```bash
grep -n "\.show()" test/widgets_dag_history_test.py | head -5
```

### GREEN

Two edits in `fanta/widgets/dag.py`.

1. Give the spin box the digit count it already supports. Find it:

```bash
grep -n "standard.SpinBox(digits=None" fanta/widgets/dag.py
```

Replace that line with:

```python
        # 7 digits matches the maximum below. Passing digits=None skips the
        # minimum-width calculation in standard.SpinBox, which leaves the
        # number touching the spin buttons on Windows.
        self.maxresults = standard.SpinBox(digits=7, maxi=9999999, wrap=True)
```

2. Replace the height rule in `showEvent`. Find it:

```bash
grep -n "setMinimumHeight(self.revtext.sizeHint().height())" fanta/widgets/dag.py
```

Replace that line **and the two comment lines above it** with:

```python
            # Size the controls row from the font rather than from whatever
            # QLineEdit.sizeHint() reports -- that hint is several pixels
            # shorter on Windows than on Linux, which is what made the row
            # look cramped around "--all".
            row_height = self.revtext.fontMetrics().height() + 2 * defs.margin
            row_height = max(row_height, self.revtext.sizeHint().height())
            self.revtext.setMinimumHeight(row_height)
            self.maxresults.setMinimumHeight(row_height)
```

`defs` is already imported in `dag.py` (`grep -n "^from .* import defs\|import defs" fanta/widgets/dag.py`).

### VERIFY

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py -p no:ruff -q
```

---

## Task 3 — One item-view appearance on every platform

### RED

Add to `test/appearance_test.py`, reusing its `qapp` fixture and `_make_palette` helper.

```python
def test_the_default_theme_styles_item_views():
    """Without these rules the platform style paints items.

    windowsvista insets the selection inside the item rect, draws a dotted
    focus rectangle and paints a hover gradient; Fusion and Breeze do none of
    that. The Flat themes already carry the same three rules
    (fanta/themes.py), so this makes the Default theme agree with them.
    """
    from fanta import themes

    palette = _make_palette(dark=False)
    style_sheet = themes.style_sheet_default(palette, bold_fonts=False)

    assert 'QAbstractItemView::item:selected' in style_sheet
    assert 'QAbstractItemView::item:hover' in style_sheet
    assert 'outline: none' in style_sheet


def test_the_selected_item_color_comes_from_the_palette():
    """A hard-coded colour would be wrong in one of light or dark mode.

    Assert on the rule body, not on the whole sheet: the highlight colour is
    already in it via QSplitter::handle:hover, so a sheet-wide search would
    pass without any item rule existing.
    """
    import re

    from fanta import qtutils
    from fanta import themes

    palette = _make_palette(dark=False)
    highlight = qtutils.rgb_css(palette.color(QtGui.QPalette.Highlight))
    style_sheet = themes.style_sheet_default(palette, bold_fonts=False)

    match = re.search(
        r'QAbstractItemView::item:selected\s*\{([^}]*)\}', style_sheet
    )

    assert match, 'no QAbstractItemView::item:selected rule'
    assert highlight in match.group(1)
```

Run:

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/appearance_test.py -p no:ruff -q -k item
```

**Expected failure:** both, on the missing `QAbstractItemView::item:selected`. (`highlight_rgb` is
already in the sheet via the splitter rule, so the second test fails only on the first assertion
list — check the failure message names the item rule, not the colour.)

### GREEN

In `fanta/themes.py`, inside `style_sheet_default()`, add to the concatenated `style_sheet`
string — put it directly **before** the `QSplitter::handle:hover` block:

```python
        + """
        /* Item views are painted by the platform style unless we say
           otherwise, and the platforms disagree. windowsvista insets the
           selection inside the item rect, which leaves the row background
           showing above and below it, draws the focus rectangle as a dotted
           outline, and paints a hover gradient. Fusion and Breeze do none of
           that. These three rules make every platform paint the way Linux
           already did. The Flat themes carry the same rules. */
        QAbstractItemView {{
            outline: none;
            show-decoration-selected: 1;
        }}
        QAbstractItemView::item:selected {{
            background-color: {highlight_rgb};
            color: {highlighted_text_rgb};
        }}
        QAbstractItemView::item:hover:!selected {{
            background-color: {hover_rgb};
        }}

        """
```

and extend the `.format(...)` call at the end of the function with the two new names:

```python
        highlighted_text_rgb=highlighted_text_rgb,
        hover_rgb=hover_rgb,
```

Compute them next to the existing colour lookups at the top of the function (`themes.py:584-590`):

```python
    highlighted_text = palette.color(QtGui.QPalette.HighlightedText)
    highlighted_text_rgb = qtutils.rgb_css(highlighted_text)
    # A hover that is a lighter highlight reads as "you are about to select
    # this" without competing with an actual selection.
    hover = QtGui.QColor(highlight)
    hover.setAlpha(defs.hover_alpha)
    hover_rgb = qtutils.rgba_css(hover)
```

`defs.hover_alpha` does not exist yet. Add it to `fanta/widgets/defs.py` next to the other
appearance constants (after `border` at `defs.py:39`), **not** as a literal in two files —
`GraphDelegate` in Task 4 needs exactly the same value, and two copies of one design value drift:

```python
# How strongly a hovered row tints, 0-255. Shared by the stylesheet rule in
# fanta/themes.py and by GraphDelegate, which paints its own column.
hover_alpha = 64
```

`defs.py` is imported by `themes.py` already (`grep -n "import defs" fanta/themes.py`).

**Before you write `qtutils.rgba_css`, check whether it exists:**

```bash
grep -n "def rgba_css\|def rgb_css" fanta/qtutils.py
```

At the baseline only `rgb_css` exists (`fanta/qtutils.py:1458`). Read it, then add `rgba_css`
beside it in the same style — a four-argument `rgba(...)` instead of `rgb(...)`. This is the
**only** new function this plan adds; everything else reuses what is there.

Add a test for it in `test/appearance_test.py`:

```python
def test_rgba_css_carries_the_alpha_channel():
    from fanta import qtutils

    color = QtGui.QColor(1, 2, 3)
    color.setAlpha(64)

    assert qtutils.rgba_css(color) == 'rgba(1, 2, 3, 64)'
```

### VERIFY

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/appearance_test.py -p no:ruff -q
```

Then confirm the rule actually reaches the pixels. **Do not rely on Qt's parse warning for
this.** Measured on PyQt5 5.15.18: an unbalanced brace produces `Could not parse application
stylesheet`, but a bad property value (`background-color: ;`) produces **no warning at all** — Qt
drops that one declaration in silence. A typo in a colour is exactly the mistake this task can
make, and the warning would not catch it.

Render a selected row and read the pixel instead:

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 - <<'PROBE'
import sys
from qtpy import QtWidgets, QtGui, QtCore
app = QtWidgets.QApplication(sys.argv[:1])
from fanta import themes
app.setStyleSheet(themes.style_sheet_default(app.palette(), False))

view = QtWidgets.QTreeWidget()
view.setHeaderHidden(True)
item = QtWidgets.QTreeWidgetItem(['selected row'])
view.addTopLevelItem(item)
view.resize(300, 80)
view.show()
app.processEvents()
item.setSelected(True)
app.processEvents()

pixmap = view.viewport().grab()
image = pixmap.toImage()
rect = view.visualItemRect(item)
sampled = image.pixelColor(rect.center())
expected = app.palette().highlight().color()
print('sampled ', sampled.name(), ' expected', expected.name())
assert sampled == expected, 'the item:selected rule did not reach the pixels'
print('OK: the selection is painted by our rule, edge to edge')
PROBE
```

**If the assertion fires**, the rule was dropped. Re-read the string you added for a missing
semicolon or an empty value — not for a missing brace, which would have warned.

---

## Task 4 — The graph delegate honours hover

### RED

Add to `test/widgets_dag_history_test.py`.

```python
def test_the_graph_delegate_paints_hover_like_the_other_columns(
    qapp, app_context, managed_qobject
):
    """Only the Summary column uses GraphDelegate; the rest use the default one.

    The tree has mouse tracking on for label hit-testing, so hovering a row
    sets State_MouseOver. The default delegate paints that and GraphDelegate
    did not, which lit up Author, Hash and Date but not Summary.
    """
    from fanta.widgets.dag import GraphDelegate

    delegate = managed_qobject(GraphDelegate(None))
    option = QtWidgets.QStyleOptionViewItem()
    option.state = QtWidgets.QStyle.State_MouseOver

    assert delegate.background_brush(option) is not None


def test_selection_wins_over_hover(qapp, managed_qobject):
    """A hovered *and* selected row must not paint the hover colour."""
    from fanta.widgets.dag import GraphDelegate

    delegate = managed_qobject(GraphDelegate(None))
    option = QtWidgets.QStyleOptionViewItem()
    option.palette = QtGui.QPalette()
    option.state = (
        QtWidgets.QStyle.State_MouseOver | QtWidgets.QStyle.State_Selected
    )

    brush = delegate.background_brush(option)

    assert brush.color() == option.palette.highlight().color()


def test_an_idle_row_paints_no_background(qapp, managed_qobject):
    from fanta.widgets.dag import GraphDelegate

    delegate = managed_qobject(GraphDelegate(None))
    option = QtWidgets.QStyleOptionViewItem()
    option.state = QtWidgets.QStyle.State_Enabled

    assert delegate.background_brush(option) is None
```

**`GraphDelegate(None)` must work** — check its `__init__` signature first with
`grep -n "class GraphDelegate" -A 20 fanta/widgets/dag.py`. If it requires a parent, pass the
tree widget the way the neighbouring tests in that file already do.

Run:

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py -p no:ruff -q -k "hover or idle_row"
```

**Expected failure:** `AttributeError: 'GraphDelegate' object has no attribute
'background_brush'`.

### GREEN

In `fanta/widgets/dag.py`, add the method to `GraphDelegate` directly above `paint()`
(`grep -n "    def paint(self, painter, option, index):" fanta/widgets/dag.py` — take the **first**
hit, inside `GraphDelegate`):

```python
    def background_brush(self, option):
        """Return the row background for this state, or None to paint nothing

        Only the Summary column uses this delegate; Author, Hash and Date are
        painted by the default one. Anything this method does not paint shows
        up as those three columns highlighting while Summary stays blank.
        """
        state = option.state
        if state & QtWidgets.QStyle.State_Selected:
            return option.palette.highlight()
        if state & QtWidgets.QStyle.State_MouseOver:
            # The same tint the QAbstractItemView::item:hover rule in
            # fanta/themes.py applies to the other three columns.
            hover = QtGui.QColor(option.palette.highlight().color())
            hover.setAlpha(defs.hover_alpha)
            return QtGui.QBrush(hover)
        return None
```

`defs` is imported in `dag.py` already; confirm with `grep -n "import defs" fanta/widgets/dag.py`.

Then replace the three-line selection block inside `paint()`:

```python
        selected = bool(option.state & QtWidgets.QStyle.State_Selected)
        if selected:
            painter.fillRect(rect, option.palette.highlight())
```

with:

```python
        selected = bool(option.state & QtWidgets.QStyle.State_Selected)
        background = self.background_brush(option)
        if background is not None:
            painter.fillRect(rect, background)
```

**Keep the `selected` variable** — grep for it first; the rest of `paint()` uses it to choose text
and chip colours, and deleting it breaks the row rendering:

```bash
sed -n '1621,1890p' fanta/widgets/dag.py | grep -n "selected"
```

### VERIFY

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_dag_history_test.py -p no:ruff -q
```

The semantic paint smoke tests in that file must still pass — they assert pixel colours around the
commit node. If one fails, your hover alpha is bleeding into a sampled pixel; check the failure's
coordinates against `test/widgets_dag_history_test.py` before changing the alpha.

---

## Task 5 — The file list picks up the same rules

No production change is expected here: the file list is a `TreeWidget`
(`fanta/widgets/filelist.py:15`) and Task 3's stylesheet is applied application-wide by
`fanta/app.py:289-290`. This task **proves** that, so a later change cannot quietly exclude it.

### RED

Add to `test/widgets_history_filelist_test.py`, reusing its fixtures.

```python
def test_the_file_list_is_covered_by_the_item_view_rules(qapp):
    """The reported hover problem was not specific to the history table.

    QAbstractItemView::item covers every tree and list, so the file list needs
    no rules of its own -- but nothing said so, and a later per-widget
    stylesheet would silently take it back out.
    """
    from qtpy import QtWidgets

    from fanta import themes
    from fanta.widgets.filelist import FileWidget

    style_sheet = themes.style_sheet_default(qapp.palette(), bold_fonts=False)

    assert issubclass(FileWidget, QtWidgets.QAbstractItemView)
    assert 'QAbstractItemView::item:hover' in style_sheet


def test_the_file_list_has_no_stylesheet_of_its_own(qapp, managed_qobject):
    """A per-widget stylesheet would override the application-wide rules."""
    from fanta.widgets.filelist import FileWidget

    widget = managed_qobject(FileWidget(None))

    assert widget.styleSheet() == ''
```

**Do not call `qapp.setStyleSheet()` in a test.** `qapp` is module-scoped and the first module to
run creates the one instance the whole session shares, so a stylesheet set here would still be
applied when the semantic paint smoke tests sample pixels later. Assert on the generated string.

`test/widgets_history_filelist_test.py` does **not** import `QtWidgets` at the baseline — the test
above imports it locally for that reason. Check before adding a module-level import:

```bash
grep -n "from qtpy import" test/widgets_history_filelist_test.py
```

`FileWidget(None)` must accept a bare parent; check its signature with
`grep -n "class FileWidget" -A 6 fanta/widgets/filelist.py` and pass whatever the neighbouring
tests in that file pass if it needs more.

`FileWidget` extends `TreeWidget`; confirm the chain reaches `QAbstractItemView` with:

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -c "
import sys
from qtpy import QtWidgets
app = QtWidgets.QApplication(sys.argv[:1])
from fanta.widgets.filelist import FileWidget
print([c.__name__ for c in FileWidget.__mro__])
"
```

If `QAbstractItemView` is **not** in that list, drop the `issubclass` assertion and assert on the
concrete base you find instead. Do not change `filelist.py` to make the assertion true.

### VERIFY

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest test/widgets_history_filelist_test.py -p no:ruff -q
```

---

## 6. Full verification

Run everything, in the split form `garden test` uses:

```bash
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q fanta test --ignore=test/widgets_main_history_test.py
PATH="$PWD/env3/bin:$PATH" QT_QPA_PLATFORM=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_main_history_test.py
```

Both must be green. Then the lint and type gates:

```bash
garden fmt
garden check/fmt
garden check/pyupgrade
garden check/mypy
```

Without `garden`, use the tools directly:

```bash
cercis bin bin/git-* fanta test extras/sphinxtogithub contrib
isort --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* fanta test extras/sphinxtogithub contrib
pyupgrade --py39-plus bin/git-* bin/*.py fanta/*.py fanta/*/*.py
python3 -m mypy --config-file pyproject.toml bin fanta
```

**Commit now** (this is commit 2 of 2):

```
fix: make item views look the same on Windows as on Linux
```

---

## 7. Traps specific to this work

| Trap | Why it bites |
|---|---|
| **Bumping `widget_version`** | Three tests assert `== 2`, and every user's saved layout is discarded. The default layout does not need it — `default_state` is captured from the arrangement itself. |
| **Turning off `setMouseTracking`** | It looks like the cause of the hover problem. It is also what `_label_hit_test` needs to know which chip the cursor is over. Removing it kills the chip tooltips. |
| **Deleting the `selected` variable in `paint()`** | The rest of the method reads it for text and chip colours. Replace the *fill*, keep the flag. |
| **A malformed QSS rule is silent** | Qt logs `Could not parse stylesheet` to stderr and then ignores the whole sheet — everything reverts to platform painting and the change looks like it did nothing. Run the parse check in Task 3. |
| **`--doctest-modules` is on** | A `>>>` in any docstring you add becomes a test case. Do not put REPL examples in the new docstrings. |
| **`app_context.settings` is a `Mock`, and a `Mock` is truthy** | Any widget calling `init_state(context.settings, ...)` raises at construction unless the test sets `get_gui_state.return_value = {}`. The `main_context` fixture already does this — use it, do not build your own. |
| **Selection signals are queued** | After `setCurrentItem()` you must pump the event loop before asserting. |

---

## 8. Manual verification on Windows

CI cannot do this. Build the installer, install it on the Windows machine and check each item.
Record pass/fail in the frontmatter.

1. **Default layout.** Rename `%APPDATA%\git-fanta\settings` to force a fresh start, launch, and
   confirm the arrangement matches the diagram in section 1.4. Then restore the file and confirm
   your own saved layout comes back untouched.
2. **Filter row.** The `--all` field and the count next to it have visible padding around their
   text, and the number does not touch the spin buttons.
3. **Selected commit row.** The highlight runs edge to edge across all four columns, with no white
   gap above or below and no step between Summary and Author.
4. **Hovered commit row.** All four columns tint together, more faintly than a selection. Moving
   onto a selected row does not change its colour.
5. **Selected file, bottom right of the history view.** No dotted outline, and the blue background
   fills the row without an inset.
6. **The Files view.** Same hover and selection behaviour as the history table.

If 3, 4 or 5 still look wrong, the likely cause is the stylesheet not being applied — check for
`Could not parse stylesheet` on stderr, which on Windows means launching the console build
(`git-fanta.exe` from a terminal) rather than the shortcut.

---

## 9. Definition of done

- [ ] All tests green in both halves of the split run.
- [ ] `check/fmt`, `check/pyupgrade`, `check/mypy` clean.
- [ ] Exactly two commits.
- [ ] Section 8 run on a real Windows install, results written into the frontmatter.
- [ ] Frontmatter added with `status: completed`, `completed_at`, `implementation_branch`,
      `implementation_head`, `ci_run` and `manual_verification`.
- [ ] `.claude/skills/project-brief/references/fork-history.md` gains a work-package section
      recording the decisions here: the default layout needs no `widget_version` bump, mouse
      tracking is load-bearing, and the item-view rules live in `style_sheet_default` rather than
      in per-widget stylesheets.
