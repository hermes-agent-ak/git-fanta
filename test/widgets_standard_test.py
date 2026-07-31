import sys

"""Tests for cola.widgets.standard helpers."""
import pytest

from cola import qtutils
from cola.widgets import defs
from cola.widgets.standard import MessageBox
from cola.widgets.standard import _strip_maximized_geometry_flag
from qtpy import QtCore
from qtpy import QtWidgets

from .helper import app_context

# Real saveGeometry() blob captured from a maximised git-fanta main window on
# macOS 15 (recorded from ~/.config/git-fanta/settings). The byte at offset 44
# is 0x02 ("maximized" flag). Qt does not always write 0x01 here.
_MAXIMIZED_BLOB_B64 = b'AdnQywADAAAAAAAAAAAAJgAABecAAAPVAAAAAAAAAEIAAAXl' b'AAAD0wAAAAACAAAABegAAAAAAAAAQgAABecAAAPV'

# Real saveGeometry() blob captured from a non-maximised window (byte 44 is 0).
_NORMAL_BLOB_B64 = b'AdnQywADAAAAAAHgAAAAGQAAB38AAAQ1AAAB4AAAADUAAAd/' b'AAAENQAAAAAAAAAAB4AAAAHgAAAANQAAB38AAAQ1'


def _maximized_byte(blob):
    """Return the byte at the well-known maximized-flag offset."""
    return bytes(blob)[44]


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for offscreen widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-fanta-test']
        )
    yield instance


def test_strip_clears_the_maximized_flag():
    """A blob with the maximized flag set comes back with byte 44 zeroed."""
    blob_in = QtCore.QByteArray.fromBase64(_MAXIMIZED_BLOB_B64)
    assert _maximized_byte(blob_in) != 0

    blob_out, was_maximized = _strip_maximized_geometry_flag(blob_in)

    assert was_maximized is True
    assert _maximized_byte(blob_out) == 0


def test_strip_preserves_every_other_byte():
    """Only the maximized-flag byte changes; the rest is byte-identical."""
    blob_in = QtCore.QByteArray.fromBase64(_MAXIMIZED_BLOB_B64)
    blob_out, _ = _strip_maximized_geometry_flag(blob_in)

    raw_in = bytes(blob_in)
    raw_out = bytes(blob_out)
    assert len(raw_in) == len(raw_out)
    assert raw_in[:44] == raw_out[:44]
    assert raw_in[45:] == raw_out[45:]


def test_strip_passes_through_normal_geometry_unchanged():
    """A blob that is not maximized comes back as the same object."""
    blob_in = QtCore.QByteArray.fromBase64(_NORMAL_BLOB_B64)
    assert _maximized_byte(blob_in) == 0

    blob_out, was_maximized = _strip_maximized_geometry_flag(blob_in)

    assert was_maximized is False
    assert blob_out is blob_in


def test_strip_ignores_blobs_without_the_qwidget_geometry_magic():
    """Junk bytes that don't start with the QWidget magic are not modified."""
    junk = QtCore.QByteArray(b'\x00\x00\x00\x00not-a-geometry-blob' + b'\xff' * 60)
    out, was_maximized = _strip_maximized_geometry_flag(junk)
    assert was_maximized is False
    assert out is junk


def test_strip_ignores_truncated_blobs():
    """A blob shorter than the maximized-flag offset is left alone."""
    short = QtCore.QByteArray(b'\x01\xd9\xd0\xcb\x00\x00')
    out, was_maximized = _strip_maximized_geometry_flag(short)
    assert was_maximized is False
    assert out is short


def test_strip_treats_any_non_zero_byte_as_maximized():
    """Qt's saveGeometry() has been observed to write 0x02 at this offset,
    so the helper must accept any non-zero value as 'maximized'."""
    raw = bytearray(bytes(QtCore.QByteArray.fromBase64(_NORMAL_BLOB_B64)))
    raw[44] = 0x02
    blob_in = QtCore.QByteArray(bytes(raw))

    blob_out, was_maximized = _strip_maximized_geometry_flag(blob_in)

    assert was_maximized is True
    assert _maximized_byte(blob_out) == 0


def test_message_box_is_not_wider_than_the_fixed_legacy_width(qapp, app_context):
    """A one-line question must not open at the full 720px dialog width."""
    box = MessageBox(
        parent=None,
        title='Create Remote?',
        text='Create a remote branch too?',
        info='',
        ok_text='Create',
    )

    box.set_initial_size()

    assert box.width() < defs.dialog_w
    box.deleteLater()


def test_plain_confirm_box_uses_a_tighter_target_size(qapp, app_context):
    """A short question with no logo and no details pane stays small."""
    box = MessageBox(parent=None, title='t', text='short', ok_text='OK')

    box.set_initial_size()

    assert box.width() == defs.confirm_w
    assert box.height() == defs.confirm_h
    box.deleteLater()


def test_message_box_is_wide_enough_for_its_text(qapp, app_context):
    """Shrinking must not cut the content off.

    Width is capped at defs.dialog_w so a very wide content wraps instead of
    pushing the box off-screen. Height must still reach the minimumSizeHint.
    """
    box = MessageBox(
        parent=None, title='Long', text='x' * 200, info='y' * 200, ok_text='OK'
    )

    box.set_initial_size()

    assert box.width() <= defs.dialog_w
    assert box.width() >= defs.dialog_w // 2
    assert box.height() >= box.minimumSizeHint().height()
    box.deleteLater()


def test_message_box_with_details_keeps_room_for_them(qapp, app_context):
    """A box showing a details pane still needs the taller layout."""
    small = MessageBox(parent=None, title='t', text='short', ok_text='OK')
    large = MessageBox(
        parent=None,
        title='t',
        text='short',
        details='line\n' * 40,
        ok_text='OK',
        expand_details=True,
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
        parent=None,
        title='t',
        text='short',
        details='line\n' * 5000,
        ok_text='OK',
        expand_details=True,
    )

    box.set_initial_size()

    assert box.width() <= desktop_width
    assert box.height() <= desktop_height
    box.deleteLater()
