# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Characterization tests for FileWidget as used by the history file panel."""

import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from cola import icons
from cola.models import dag
from cola.widgets.filelist import FileTreeWidgetItem
from cola.widgets.filelist import FileWidget
from cola.widgets.filelist import merge_numstat_rows
from cola.widgets.filelist import parse_status_and_numstat
from qtpy import QtCore
from qtpy import QtWidgets

from .helper import app_context

assert app_context is not None


@pytest.fixture(scope='module')
def qapp():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-fanta-test']
        )
    yield instance


@pytest.fixture
def managed_qobject(qapp):
    objects = []

    def manage(obj):
        objects.append(obj)
        return obj

    yield manage

    qapp.processEvents()
    for obj in reversed(objects):
        if isinstance(obj, QtWidgets.QWidget):
            obj.close()
    qapp.processEvents()
    for obj in reversed(objects):
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qapp.processEvents()


def test_list_files_creates_file_tree_items(qapp, app_context, managed_qobject):
    """list_files() builds FileTreeWidgetItem rows with path and +/- columns."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.list_files(['3\t1\tsrc/a.py', '0\t10\tsrc/b.py'])

    assert widget.topLevelItemCount() == 2
    item = widget.topLevelItem(0)
    assert isinstance(item, FileTreeWidgetItem)
    assert item.path == 'src/a.py'
    assert item.text(0) == 'src/a.py'
    assert item.text(1) == '3'
    assert item.text(2) == '1'


def test_empty_commit_selection_clears_the_list(qapp, app_context, managed_qobject):
    """An empty selection clears the widget without running git."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.list_files(['1\t0\tsrc/a.py'])

    widget.commits_selected([])

    assert widget.topLevelItemCount() == 0


def test_selection_emits_selected_paths(qapp, app_context, managed_qobject):
    """itemSelectionChanged emits files_selected with the selected paths."""
    widget = managed_qobject(FileWidget(app_context, None))
    emitted = []
    widget.files_selected.connect(emitted.append)
    widget.list_files(['3\t1\tsrc/a.py', '0\t10\tsrc/b.py'])

    widget.setCurrentItem(widget.topLevelItem(0))

    assert emitted == [['src/a.py']]


def test_parser_splits_nul_separated_raw_and_numstat():
    """ "git show --raw --numstat -z" yields a status map plus numstat rows."""
    out = ':100644 100644 aaa bbb M\0cola/main.py\0' ':000000 100644 000 ccc A\0cola/new.py\0' '33\t0\tcola/main.py\0' '10\t0\tcola/new.py\0'

    status_by_path, numstat = parse_status_and_numstat(out, '\0')

    assert status_by_path == {'cola/main.py': 'M', 'cola/new.py': 'A'}
    assert numstat == ['33\t0\tcola/main.py', '10\t0\tcola/new.py']


def test_parser_splits_newline_separated_raw_and_numstat():
    """ "git diff-index --raw --numstat" keeps the path inline, newline separated."""
    out = ':100644 100644 aaa bbb M\ta.py\n' ':000000 100644 000 ccc A\tb.py\n' '1\t0\ta.py\n' '1\t0\tb.py\n'

    status_by_path, numstat = parse_status_and_numstat(out, '\n')

    assert status_by_path == {'a.py': 'M', 'b.py': 'A'}
    assert numstat == ['1\t0\ta.py', '1\t0\tb.py']


def test_parser_tolerates_numstat_without_raw():
    """Merge commits emit numstat only; the status map stays empty."""
    status_by_path, numstat = parse_status_and_numstat('1\t0\tt.py\0', '\0')

    assert status_by_path == {}
    assert numstat == ['1\t0\tt.py']


@pytest.mark.parametrize(
    ('status', 'expected'),
    (
        ('A', 'plus.svg'),
        ('M', 'modified.svg'),
        ('D', 'circle-slash-red.svg'),
        ('T', 'modified.svg'),
        ('R', 'git-compare.svg'),
        ('C', 'git-compare.svg'),
        ('X', 'file-text.svg'),
        ('', 'file-text.svg'),
    ),
)
def test_diff_status_basename_maps_known_codes(status, expected):
    """Each git status code maps to the documented icon basename."""
    assert icons.diff_status_basename(status, 'src/Makefile') == expected


def _fake_commit(oid, summary='summary'):
    """Ein Commit-Stellvertreter mit den Feldern, die die Diff-Ansicht liest."""
    commit = MagicMock()
    commit.oid = oid
    commit.author = 'A U Thor'
    commit.email = 'author@example.com'
    commit.authdate = '2026-01-01'
    commit.summary = summary
    return commit


def test_commits_selected_remembers_the_commits(qapp, app_context, managed_qobject):
    """Die angezeigten Dateien gehoeren zu einem Commit - der wird gemerkt."""
    widget = managed_qobject(FileWidget(app_context, None))
    commit = _fake_commit('a' * 40)

    widget.commits_selected([commit])

    assert widget.commits == [commit]


def test_empty_selection_forgets_the_commits(qapp, app_context, managed_qobject):
    """Ohne Auswahl bleibt kein Commit uebrig, an dem ein Doppelklick haengt."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.commits_selected([_fake_commit('a' * 40)])

    widget.commits_selected([])

    assert widget.commits == []


def test_new_widget_starts_without_commits(qapp, app_context, managed_qobject):
    widget = managed_qobject(FileWidget(app_context, None))

    assert widget.commits == []


def _double_click_first_item(widget):
    """Loest den Doppelklick so aus, wie Qt es beim Anwender tun wuerde."""
    item = widget.topLevelItem(0)
    widget.itemDoubleClicked.emit(item, 0)
    return item


def test_double_click_requests_the_file_diff(qapp, app_context, managed_qobject):
    """Ein Doppelklick meldet Commits und Pfad nach aussen."""
    widget = managed_qobject(FileWidget(app_context, None))
    commit = _fake_commit('a' * 40)
    widget.commits_selected([commit])
    widget.list_files(['3\t1\tsrc/a.py'])
    received = []
    widget.file_diff_requested.connect(
        lambda commits, path: received.append((commits, path))
    )

    _double_click_first_item(widget)
    qapp.processEvents()

    assert received == [([commit], 'src/a.py')]


def test_double_click_without_commits_is_ignored(qapp, app_context, managed_qobject):
    """Ohne bekannten Commit gibt es nichts zu diffen - kein Signal."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.list_files(['3\t1\tsrc/a.py'])
    received = []
    widget.file_diff_requested.connect(
        lambda commits, path: received.append((commits, path))
    )

    _double_click_first_item(widget)
    qapp.processEvents()

    assert received == []


def test_double_click_emits_a_copy_of_the_commits(qapp, app_context, managed_qobject):
    """Der Empfaenger bekommt eine Kopie, keine Referenz auf den Widget-Zustand."""
    widget = managed_qobject(FileWidget(app_context, None))
    widget.commits_selected([_fake_commit('a' * 40)])
    widget.list_files(['3\t1\tsrc/a.py'])
    received = []
    widget.file_diff_requested.connect(lambda commits, path: received.append(commits))

    _double_click_first_item(widget)
    qapp.processEvents()

    assert received[0] is not widget.commits


def test_all_paths_reports_every_listed_file(qapp, app_context, managed_qobject):
    """Die Beschreibung braucht alle Pfade, nicht nur die markierten."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.list_files(['3\t1\tsrc/a.py', '0\t2\tsrc/b.py'])

    assert widget.all_paths() == ['src/a.py', 'src/b.py']


def test_all_paths_is_empty_without_files(qapp, app_context, managed_qobject):
    widget = managed_qobject(FileWidget(app_context, None))

    assert widget.all_paths() == []


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

    widget.commits_selected([
        _fake_commit(history_repo['a_again']),
        _fake_commit(dag.STAGE),
        _fake_commit(dag.WORKTREE),
    ])

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
