# ruff: noqa: I001  # Garden enforces force-single-line imports.
"""The merge dialog opens with a ref already chosen, in every field that shows it."""

import subprocess
import sys

import pytest

from fanta.qtutils import get
from fanta.widgets.merge import Merge
from fanta.widgets.merge import local_merge
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
