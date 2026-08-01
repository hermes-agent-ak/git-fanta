# Gotchas

Non-obvious behavior in this codebase and its toolchain, each with the evidence that established
it. These were found the expensive way. Re-verify before leaning on one — line numbers drift.

## Qt state persistence

**`QMainWindow.saveState()` covers dock and toolbar topology only.** Splitters, column widths and
anything inside a dock's widget are not in that blob. Consequences:

- Adding or removing a **dock** requires bumping `widget_version` (`cola/widgets/main.py`,
  `cola/widgets/dag.py` — both currently `2`).
- Adding a splitter, a pane, or a child widget does **not**.
- Bumping the version discards every user's saved geometry and breaks hard-coded assertions in
  the test suite. Check what actually gets serialized before proposing a migration.

**Composite widgets nest their children's state.** `MainView.export_state()` puts the history
widget's state under `state['history']`; `CommitHistoryWidget` puts the tree's under
`state['log']`. Adding a key to a nested exporter breaks every exact-dict assertion in the tests
that compare whole state blobs — grep for `== {` in `test/` before changing an exporter.

**`is_valid_state()` returns early.** `CommitHistoryWidget.is_valid_state` returns `True` as soon
as it sees no `'log'` key. Validation for new keys must go *above* that, or it silently never
runs for exactly the legacy states it was written for.

## Qt widget behavior

**`qtutils.add_action_bool` connects `triggered[bool]`, not `toggled`.** Calling `setChecked()`
during construction therefore does **not** invoke the handler. Existing code (the
`display_inline_graph` and `display_files` actions in `cola/widgets/dag.py`) calls the handler
explicitly right after creating the action. Copy that; don't rely on the signal.

**Shortcuts are widget-scoped.** `qtutils._add_action` sets `Qt.WidgetWithChildrenShortcut`, so
two instances of the same widget in one window do not produce ambiguous-shortcut warnings.

**Tree selection signals are queued.** `CommitTreeWidget` connects `itemSelectionChanged` with
`type=Qt.QueuedConnection`. In tests, `setCurrentItem()` does nothing observable until the event
loop is pumped.

**`QSplitter.addWidget()` does not override visibility** set before or after the call, and inside
a parent's `showEvent` the children already report `isVisible() == True` — Qt shows children
before delivering the parent's show event. Both verified offscreen under PyQt5.

**Instance-level method shadowing works on Qt objects** (`splitter.setSizes = spy`), which makes
`monkeypatch.setattr(obj, 'method', ...)` a usable test technique here.

**Splitter sizes are meaningless before the first layout.** A never-shown splitter reports `[0,0]`
or hint values depending on the binding. Never assert against fixed pixel numbers; compare
against the live value, or spy on `setSizes`.

**`CommitDiffWidget.commits_selected()` arms a 100 ms debounce that fires later and wins.**
Calling it and then `files_selected(['path'])` shows the single-file diff — until the timer fires
and reloads the whole-commit diff over it (measured: `filename=None`, two git calls). To show one
file's diff, set `oid` / `oid_start` / `oid_end` directly and call `files_selected()` once, the
way `CommitFileDiffWindow.set_commit_file()` does.

**A `standard.Widget` with a parent is not a window.** `isWindow()` is `False` until you call
`setWindowFlags(Qt.Window)`; without it the widget silently becomes a child in the parent's
layout. `standard.Dialog` is a window straight away. Both persist geometry on close — `Widget`
via `WidgetMixin.closeEvent`, `Dialog` via `closeEvent → reject()` — so state saving is *not*
what distinguishes them.

**Qt destroys child widgets without sending a close event.** A window that saves its state in
`closeEvent` therefore loses it when the parent goes away. Hosts close such children explicitly:
see the `browser_windows` loop and the `commit_file_diff_window` line in `MainView.closeEvent`.


**`_prepare_labels()` drops `'HEAD'`,** so a detached HEAD row has no chip at all — measured:
`_prepare_labels(['HEAD']) == []`. `GraphDelegate._row_labels()` puts it back when no branch chip
on the row was marked current.

**`commit.tags` cannot distinguish an attached from a detached HEAD.** Both read
`['HEAD', 'heads/main']` on a branch tip — measured through `dag.RepoReader`. Only
`model.currentbranch` knows, and it is the literal string `'HEAD'` when detached
(`cola/gitcmds.py:241`). Git refuses a branch named `HEAD`, so `'heads/' + currentbranch` needs no
special case.

**The inline HEAD node cannot grow past an outer radius of 8 px.** The semantic paint test's
tightest sample (`incoming_y`) sits 9 px from the node center and asserts `> node_guard`.


**`MonoTextEdit` and `PlainTextEdit` start with `NoWrap`.** `BaseTextEditExtension` sets it
(`cola/widgets/text.py:102`); the constructor's `line_wrap_mode` only takes effect through
`set_word_wrapping(True)` (`:337`). A read-only text view that forgets this gets a horizontal
scrollbar.

**Hiding a parent `QSplitter` hides its children.** `child.isVisible()` becomes `False` - measured
on the history's nested splitters. Visibility guards written against a child keep working when the
parent becomes the thing that is toggled.

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

**A `QSyntaxHighlighter`'s formats are invisible to `QTextCursor.charFormat()`.** They live as
additional formats in the layout; read them with `block.layout().formats()`.


**The inline graph's chip color names are misleading.** `chip_head` paints **local** branches
(`heads/…`), `chip_other` is the fallback that **remote** branches land in, `chip_tag` paints
tags, and `chip_remote` paints nothing but the `HEAD` chip. See `cola/widgets/dag.py` where the
brush is chosen. There are **four** chip colors; `_distinct_chip_backgrounds()` and
`readable_chip_fills()` both have to keep producing four distinct ones.

**An invalid `QColor` and opaque black report the same `rgba()`** — both `0xff000000`. Measured.
Anything that keys on a color has to carry `isValid()` as well, because `_opaque_color()`
synthesizes mid-grey for the invalid one and leaves black alone.

**`inline_graph_style()` is memoized on the palette.** It returns a shared frozen instance, so an
equal palette hands back the *same object* — a test that asserts `is not` between two calls is
asserting the old, uncached behavior. A different palette is a different key; nothing invalidates.

**Contrast ratio is luminance-only, so it cannot assert that two colors look different.** Forcing
several fills to the same contrast floor against the same background necessarily puts them at the
same luminance, which reads as "contrast 1.0" between them while they stay clearly different
hues. Assert distinctness on hue.

**`MessageBox` is shared by `confirm()`, `critical()` and `information()`.** A change to its size
or position is felt in every dialog in the application.


**`ViewerMixin.menu_actions` is `None` until something assigns it.** Only `GitDAG` calls
`viewer_actions()`; a bare `CommitTreeWidget` has `None` and `update_menu_actions()` raises
`TypeError`. Tests must assign `viewer_actions(tree, tree)` themselves.

**The history's action set is asserted exactly.**
`test_mainview_history_context_actions_are_composed_once_and_disable_off_item` compares the key
set and the count twice. Adding a context-menu action means editing `VIEWER_ACTION_KEYS` and two
literals in the same file.

**Radio buttons wired with `qtutils.connect_released` do not react to `setChecked()`.** `released`
is a user gesture; changing the state in code has to run the same update by hand.

## Git output

**`git show --raw` prints nothing for merge commits**, while `--numstat` still prints the combined
diff. Any parser reading both must tolerate numstat entries with no raw block — and the codebase
relies on that path, because several DAG tests monkeypatch `git.show` to return numstat only.

**`--raw` and `--numstat` can be requested together** in one invocation, for `show`, `diff`,
`diff-index` and `diff-files`. Git emits the raw block first, then numstat. With `-z` the raw path
is its own NUL-separated field; without `-z` it follows the info field after a tab.
`cola/widgets/filelist.py:parse_status_and_numstat()` handles both.

**`git diff-files` and `git diff-index` do not emit NUL separators between entries** even with
`-z` — there is a comment about this in `filelist.py`. Those two paths split on newline.

**Numstat field order is `adds<TAB>dels<TAB>path`.** `FileTreeWidgetItem` relies on it. Getting
this backwards produces test data that looks plausible and asserts nothing.

**The `git` wrapper turns kwargs into flags** (`cola/git.py:transform_kwargs`): `raw=True` →
`--raw`, `no_renames=True` → `--no-renames`, `foo=False` is dropped, `foo='bar'` → `--foo=bar`.
Single-character keys get one dash. `_readonly=True` is a wrapper hint, not a git flag.


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


**`git rev-list --no-walk <oids> -- <path>` answers "which of these commits touched this file".**
It does not walk ancestors, so a commit outside the list can never be the answer, and its default
ordering is by commit date, newest first -- `--max-count=1` therefore yields the newest toucher.
An empty result is exit status 0 with empty output, not an error. Beware when probing this in a
script-built repository: commits made in the same second fall back to argument order and make the
ordering look input-driven.

**Plain `git checkout <name>` is not a safe way to materialise a remote branch.** It depends on
`checkout.guess` being enabled, and when a local branch of the same name already exists elsewhere
it silently checks that one out. Use `git checkout -b <name> --track <remote>/<name>`.


**`git merge-base --is-ancestor` does not answer "can I merge this".** It reports a diverged
branch as not an ancestor, although a diverged branch is the ordinary merge case. Count instead:
`git rev-list --count HEAD..<ref>` is greater than zero exactly when there is something to merge.
A ref that does not resolve exits 128 with empty output.

## Icons

**`cola/icons.py` is the only file that names icon assets** — that is stated in its module
docstring, and it is a rule worth keeping. Add a lookup table plus a small function there rather
than spreading basenames across widgets.

**Icons do not resolve in tests.** `icons.install()` registers the `icons:` search path and is
only called from `cola/app.py`. In a test, `QIcon('icons:plus.svg')` is null. Assert on the data
(a status field, the basename returned by a pure function), never on the rendered icon.

**Check the asset exists** in `cola/icons/` before referencing a basename. The set is small and
does not include everything you would expect.

## Tests

**`app_context` gives you a real repository.** It creates a temp dir, `chdir`s in, runs
`initialize_repo()` (files `A` and `B`, staged, branch `main`, gpgsign off) and yields a `Mock()`
context wired to a real `git`, `cfg` and `MainModel`. Building your own repo or monkeypatching
`context.git` is almost always redundant work.

**There is no `conftest.py`.** `qapp`, `managed_qobject` and `main_context` are defined
per test file. Copy them from a neighbouring widget test verbatim instead of writing variants.

**`app_context.settings` is a raw `Mock`, and a `Mock` is truthy.** Any widget that calls
`init_state(context.settings, ...)` therefore takes the restore branch and hands `Mock` objects
to `QByteArray.fromBase64()` — a `TypeError` at construction time, with a message that says
nothing about your test. Set `app_context.settings.get_gui_state.return_value = {}` first; that
is what `main_context` and every `GitDAG` test already do.

**`--doctest-modules` is on and `garden test` collects `cola/` too.** A `>>>` in any production
docstring becomes a test case.

**`pytest-ruff` runs by default** via `pytest-enabler`; focused runs pass `-p no:ruff`, matching
CI, and lint is a separate step.

**Test names can encode contracts.** `test_public_selection_reaches_all_standalone_consumers_
synchronously` and `test_history_widget_owns_history_state_without_window_children` are
architectural decisions written down as tests. Violating one is a design change requiring
justification, not a test to be edited into agreement.


**`Interaction.confirm` is the console implementation in tests.** `standard.install()` runs only
from `cola/app.py`, so a confirmation in a test writes to stdout and reads `sys.stdin` — under
pytest capture that is an error, not a `False`. Monkeypatch it in every test that can reach one.

**`cmds.do()` swallows exceptions** into `Interaction.critical` (`cola/cmds.py:3591`). A broken
command does not fail a test by itself; assert on the git state or the model instead.

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

## Toolchain

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

**The formatter is `cercis`, not black** (`[tool.cercis]` in `pyproject.toml`, plus the
pre-commit hook). Line length 88, `function-definition-extra-indent = false`.

**isort runs with `--force-single-line-imports --py=39 --no-lines-before=STDLIB`.** One import per
line. Some test files carry `# ruff: noqa: I001` at the top because of this — keep it when editing
those files.

**mypy is pinned to 1.19.1** and configured leniently (`disallow_untyped_defs = false`, several
error codes disabled). It checks `bin` and `cola`, not `test`.

**Python 3.9 is the floor**, enforced by `pyupgrade --py39-plus` in CI and pre-commit.

## The git-fanta rename

**`icons.cola()` keeps its name on purpose.** `cola/widgets/toolbar.py:254` resolves icon names
with `getattr(icons, name, None)` and `cola/widgets/toolbarcmds.py:283`/`:285` pass `'icon':
'cola'`. Renaming the function removes the toolbar icon silently — no exception, no log entry.
The asset it returns is `git-fanta.svg`; the function name is not user-visible.

**`cola/version.py` asks `metadata.version('git-fanta')`,** which must match `name` in
`pyproject.toml`. If the two drift, `importlib.metadata` raises `PackageNotFoundError` and the
version display falls back to the builtin value without saying so.
`test_distribution_name_matches_pyproject` guards it.

**`brew install git-cola` in `.github/workflows/ci.yml` is not a leftover.** It installs the real
upstream Homebrew formula as a dependency of the macOS job. Renaming it breaks that job.

**A forgotten `'cola.<key>'` literal will not turn a test red.** `cola/gitcfg.py` falls back to
the old prefix by design, so the stale key keeps working and the rename is quietly incomplete.
`test_no_legacy_config_key_literals` in `test/rename_guard_test.py` is the only thing that
notices — there are 34 such literals outside `cola/models/prefs.py`, spread over 16 files.

**The upstream references are load-bearing.** `CHANGES.rst`, the `github.com/git-cola/...` links
in code comments, and the remotes in `garden.yaml` point at a project that still exists.
`test_upstream_references_are_preserved` fails if a future rename sweep eats them.
