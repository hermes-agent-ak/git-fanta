# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""Der Doppelklick in der Commit-Liste und seine Checkout-Regeln."""

import subprocess
import sys
from unittest.mock import Mock

import pytest

from fanta import cmds
from fanta.interaction import Interaction
from fanta.models import dag
from fanta.widgets import dag as dagwidget
from fanta.widgets import defs
from fanta.widgets.dag import CommitTreeWidget
from fanta.widgets.dag import CommitTreeWidgetItem
from qtpy import QtCore
from qtpy import QtGui
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
    """Wie in test/widgets_main_history_test.py: mit strip()."""
    return subprocess.run(
        ('git', *args), check=True, text=True, capture_output=True
    ).stdout.strip()


def _repo_with_topic(context):
    """Zwei Commits, zwei Branches, HEAD auf main."""
    _git('commit', '-m', 'base')
    base_oid = _git('rev-parse', 'HEAD')
    _git('checkout', '-b', 'topic')
    _git('commit', '--allow-empty', '-m', 'topic')
    topic_oid = _git('rev-parse', 'HEAD')
    _git('checkout', 'main')
    context.model.update_status()
    return base_oid, topic_oid


def _fake_commit(oid, branches=(), tags=()):
    """Ein Commit-Stellvertreter mit genau den Feldern, die die Regel liest."""
    commit = dag.Commit(None, dag.CommitFactory(), oid=oid)
    commit.summary = 'summary'
    commit.author = 'A U Thor'
    commit.authdate = '2026-07-31'
    commit.branches = list(branches)
    commit.tags = list(tags)
    return commit


@pytest.fixture
def checkout_context(app_context):
    """app_context plus das eine Attribut, das cmds.Command.do() numerisch vergleicht."""
    app_context.timestamp = 0.0
    return app_context


def _tree(context, managed_qobject):
    return managed_qobject(CommitTreeWidget(context, None))


def _never_confirm(monkeypatch):
    """Interaction.confirm ist im Test die Konsolenvariante und liest stdin."""
    calls = []

    def record(*args, **kwargs):
        calls.append((args, kwargs))
        return False

    monkeypatch.setattr(Interaction, 'confirm', staticmethod(record))
    return calls


def _always_confirm(monkeypatch):
    calls = []

    def record(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(Interaction, 'confirm', staticmethod(record))
    return calls


def test_double_click_on_a_branch_tip_checks_out_that_branch(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Die Spitze genau eines lokalen Branches wird ohne Rueckfrage ausgecheckt."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(topic_oid, branches=['topic']))

    assert _git('rev-parse', '--abbrev-ref', 'HEAD') == 'topic'
    assert checkout_context.model.currentbranch == 'topic'
    assert confirmed == []


def test_double_click_on_the_current_branch_tip_runs_no_git_command(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Wer schon auf dem Branch steht, loest keinen Checkout aus."""
    base_oid, _topic = _repo_with_topic(checkout_context)
    checkouts = []
    monkeypatch.setattr(
        checkout_context.git, 'checkout', lambda *a, **kw: checkouts.append((a, kw))
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(base_oid, branches=['main'], tags=['HEAD']))

    assert checkouts == []
    assert confirmed == []


def test_double_click_on_a_plain_commit_asks_before_detaching(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Ohne Branch-Spitze wird gefragt - und ein Nein laesst HEAD stehen."""
    base_oid, _topic = _repo_with_topic(checkout_context)
    head_before = _git('rev-parse', 'HEAD')
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(base_oid))

    assert len(confirmed) == 1
    args, kwargs = confirmed[0]
    assert base_oid[:7] in args[1]
    assert 'detach' in (args[1] + args[2]).lower()
    assert kwargs['default'] is False
    assert _git('rev-parse', 'HEAD') == head_before


def test_confirmed_detached_checkout_moves_head(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Ein Ja loest HEAD ab und setzt ihn auf den Commit."""
    base_oid, _topic = _repo_with_topic(checkout_context)
    _always_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(base_oid))

    assert _git('rev-parse', 'HEAD') == base_oid
    assert _git('rev-parse', '--symbolic-full-name', 'HEAD') == 'HEAD'


def test_detached_head_on_a_branch_tip_reattaches_to_the_branch(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Aus dem abgeloesten Zustand haengt der Doppelklick HEAD wieder an."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    _git('checkout', '--detach', 'topic')
    checkout_context.model.update_status()
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(
        _fake_commit(topic_oid, branches=['topic'], tags=['HEAD', 'heads/topic'])
    )

    assert _git('rev-parse', '--abbrev-ref', 'HEAD') == 'topic'
    assert confirmed == []


def test_detached_head_on_a_plain_commit_does_not_ask_again(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Wer schon abgeloest auf diesem Commit steht, wird nicht gefragt."""
    base_oid, _topic = _repo_with_topic(checkout_context)
    _git('checkout', '--detach', base_oid)
    checkout_context.model.update_status()
    checkouts = []
    monkeypatch.setattr(
        checkout_context.git, 'checkout', lambda *a, **kw: checkouts.append((a, kw))
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(base_oid, tags=['HEAD']))

    assert confirmed == []
    assert checkouts == []


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


@pytest.mark.parametrize('oid', (dag.STAGE, dag.WORKTREE))
def test_pseudo_commits_are_never_checked_out(
    qapp, checkout_context, managed_qobject, monkeypatch, oid
):
    """WORKTREE und STAGE sind keine Commits."""
    _repo_with_topic(checkout_context)
    checkouts = []
    monkeypatch.setattr(
        checkout_context.git, 'checkout', lambda *a, **kw: checkouts.append((a, kw))
    )
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(_fake_commit(oid))

    assert checkouts == []
    assert confirmed == []


def test_none_is_ignored(qapp, checkout_context, managed_qobject, monkeypatch):
    """Ein Doppelklick ins Leere darf nicht knallen."""
    _repo_with_topic(checkout_context)
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)

    tree.checkout_commit(None)

    assert confirmed == []


def _double_click_first_item(tree):
    item = tree.topLevelItem(0)
    tree.itemDoubleClicked.emit(item, 0)
    return item


def test_double_click_in_the_tree_checks_out_the_branch(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Der Doppelklick auf die Zeile loest den Checkout aus."""
    _base, topic_oid = _repo_with_topic(checkout_context)
    _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)
    tree.addTopLevelItem(
        CommitTreeWidgetItem(_fake_commit(topic_oid, branches=['topic']))
    )

    _double_click_first_item(tree)
    qapp.processEvents()

    assert _git('rev-parse', '--abbrev-ref', 'HEAD') == 'topic'


def test_double_click_on_a_row_without_a_commit_is_ignored(
    qapp, checkout_context, managed_qobject, monkeypatch
):
    """Fremde Items ohne .commit duerfen nichts ausloesen."""
    _repo_with_topic(checkout_context)
    confirmed = _never_confirm(monkeypatch)
    tree = _tree(checkout_context, managed_qobject)
    tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(['no commit']))

    _double_click_first_item(tree)
    qapp.processEvents()

    assert confirmed == []


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

    assert recorded == [(
        cmds.Checkout,
        (['-b', 'feature', '--track', 'origin/feature'],),
        {'checkout_branch': True},
    )]


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


def _tree_with_actions(context, managed_qobject):
    """A commit tree that owns its menu actions, the way GitDAG builds them."""
    tree = _tree(context, managed_qobject)
    tree.menu_actions = dagwidget.viewer_actions(tree, tree)
    return tree


def _context_menu_event():
    position = QtCore.QPoint(-1, -1)
    return QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, position, position)


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


def test_the_branch_dialog_sizes_itself_to_fit_its_branches(qapp, managed_qobject):
    """The default must follow the branches, not the parent window."""
    dialog = _branch_dialog(managed_qobject, ['main'])

    metrics = dialog.branch_list.fontMetrics()
    text_width = metrics.horizontalAdvance('main')
    item_height = dialog.branch_list.sizeHintForRow(0)
    # Width: text + branch-list padding + 2 px slack on each side.
    expected_width = text_width + 2 * defs.button_spacing + 32
    # Height: label + 1 item + buttons + outer margin.
    expected_height = (
        dialog.label.sizeHint().height()
        + item_height
        + dialog.checkout_button.sizeHint().height()
        + 3 * defs.margin
    )

    assert dialog.width() < 420, dialog.width()
    assert dialog.width() >= expected_width, (dialog.width(), expected_width)
    assert dialog.height() < 280, dialog.height()
    assert dialog.height() >= expected_height, (dialog.height(), expected_height)


def test_the_branch_dialog_grows_with_more_branches(qapp, managed_qobject):
    """Adding branches must grow the row that holds them."""
    small = _branch_dialog(managed_qobject, ['a'])
    tall = _branch_dialog(managed_qobject, ['a'] * 8)

    assert tall.height() > small.height()
    assert tall.height() >= small.height() + 7 * tall.branch_list.sizeHintForRow(0)


def test_the_branch_dialog_sizes_for_the_longest_branch_name(qapp, managed_qobject):
    """The widest branch name decides the width."""
    dialog = _branch_dialog(managed_qobject, ['main', 'a-very-long-branch-name'])

    metrics = dialog.branch_list.fontMetrics()
    expected_min = metrics.horizontalAdvance('a-very-long-branch-name') + 32
    assert dialog.width() >= expected_min, (dialog.width(), expected_min)
