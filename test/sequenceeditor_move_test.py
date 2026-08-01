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
        if isinstance(obj, QtWidgets.QWidget):
            obj.close()
    qapp.processEvents()
    for obj in reversed(objects):
        obj.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    qapp.processEvents()


def _rebase_tree(managed_qobject, count):
    """A rebase widget holding `count` pick rows."""
    tree = managed_qobject(RebaseTreeWidget(None, '#', None))
    # The production tree wires itemSelectionChanged to selection_changed, which
    # dereferences self.context. These tests pass context=None; disconnecting
    # keeps the slot from segfaulting on every selection change, including
    # the one shift_down() and move() trigger via setCurrentItem().
    try:
        tree.itemSelectionChanged.disconnect()
    except (TypeError, RuntimeError):
        pass
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
