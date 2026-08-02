"""Tests for runtime appearance refresh behavior."""
import sys
from unittest.mock import MagicMock

import pytest

from fanta import app as cola_app
from fanta.widgets.diff import DiffSyntaxHighlighter
from qtpy import QtGui
from qtpy import QtWidgets


@pytest.fixture(scope='module')
def qapp():
    """Provide a QApplication for widget tests."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(
            sys.argv[:1] if sys.argv else ['git-fanta-test']
        )
    yield instance


def _make_palette(*, dark: bool) -> QtGui.QPalette:
    palette = QtGui.QPalette()
    base = QtGui.QColor('#202025' if dark else '#ffffff')
    palette.setColor(QtGui.QPalette.Base, base)
    return palette


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )


def _make_context():
    context = MagicMock()
    context.cfg.color.side_effect = lambda _key, default: _hex_to_rgb(default)
    return context


def test_refresh_system_appearance_rebuilds_default_theme():
    """The default theme follows the system palette and must be rebuilt."""
    cola = cola_app.ColaApplication.__new__(cola_app.ColaApplication)
    cola.context = MagicMock()
    cola.context.cfg.get.return_value = 'default'
    cola._install_style = MagicMock()

    cola.refresh_system_appearance()

    cola._install_style.assert_called_once_with(None)


def test_refresh_system_appearance_skips_non_default_theme():
    """User-selected themes replace the palette and must not be overridden."""
    cola = cola_app.ColaApplication.__new__(cola_app.ColaApplication)
    cola.context = MagicMock()
    cola.context.cfg.get.return_value = 'flat-dark-blue'
    cola._install_style = MagicMock()

    cola.refresh_system_appearance()

    cola._install_style.assert_not_called()


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

    match = re.search(r'QAbstractItemView::item:selected\s*\{([^}]*)\}', style_sheet)

    assert match, 'no QAbstractItemView::item:selected rule'
    assert highlight in match.group(1)


def test_rgba_css_carries_the_alpha_channel():
    from fanta import qtutils

    color = QtGui.QColor(1, 2, 3)
    color.setAlpha(64)

    assert qtutils.rgba_css(color) == 'rgba(1, 2, 3, 64)'


def test_diff_syntax_highlighter_uses_light_palette_defaults(qapp):
    context = _make_context()
    doc = QtGui.QTextDocument()
    highlighter = DiffSyntaxHighlighter(context, doc)

    highlighter._configure_colors(context, _make_palette(dark=False))

    assert highlighter.color_add.red() == 0xD2
    assert highlighter.color_add.green() == 0xFF
    assert highlighter.color_add.blue() == 0xE4
    assert highlighter.color_remove.red() == 0xFE
    assert highlighter.color_remove.green() == 0xE0
    assert highlighter.color_remove.blue() == 0xE4


def test_diff_syntax_highlighter_uses_dark_palette_defaults(qapp):
    context = _make_context()
    doc = QtGui.QTextDocument()
    highlighter = DiffSyntaxHighlighter(context, doc)

    highlighter._configure_colors(context, _make_palette(dark=True))

    assert highlighter.color_add.red() == 0x77
    assert highlighter.color_add.green() == 0xAA
    assert highlighter.color_add.blue() == 0x77
    assert highlighter.color_remove.red() == 0xAA
    assert highlighter.color_remove.green() == 0x77
    assert highlighter.color_remove.blue() == 0x77


def test_diff_syntax_highlighter_refresh_palette_rehighlights(qapp):
    context = _make_context()
    doc = QtGui.QTextDocument()
    highlighter = DiffSyntaxHighlighter(context, doc)
    highlighter.rehighlight = MagicMock()

    highlighter.refresh_palette(context)

    highlighter.rehighlight.assert_called_once()
