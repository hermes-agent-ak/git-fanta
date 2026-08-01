"""The macOS bundle metadata identifies Git Fanta and nothing else.

The .app bundle is what macOS uses to tell two installed applications apart,
so contrib/darwin/Info.plist has to be unambiguous. It is copied verbatim into
the bundle by "garden macos/app"; only the two version placeholders are
substituted at build time.
"""

import collections
import pathlib
import plistlib
import xml.etree.ElementTree as ET

INFO_PLIST = pathlib.Path(__file__).resolve().parent.parent / 'contrib/darwin/Info.plist'


def _plist():
    with INFO_PLIST.open('rb') as handle:
        return plistlib.load(handle)


def _keys_in_document_order():
    """Return every top-level <key> as it appears in the file.

    plistlib silently collapses duplicate keys into one dict entry, so reading
    the parsed plist cannot detect a duplicate. The XML has to be inspected.
    """
    root = ET.parse(INFO_PLIST).getroot()
    top_level_dict = root.find('dict')
    return [element.text for element in top_level_dict.findall('key')]


def test_no_key_is_defined_twice():
    """A second CFBundleName silently wins over the first one."""
    duplicates = [
        key for key, count in collections.Counter(_keys_in_document_order()).items()
        if count > 1
    ]

    assert not duplicates, f'Info.plist defines these keys twice: {duplicates}'


def test_the_bundle_is_named_git_fanta():
    plist = _plist()

    assert plist['CFBundleName'] == 'Git Fanta'
    assert plist['CFBundleDisplayName'] == 'Git Fanta'
    assert plist['CFBundleIdentifier'] == 'com.justroots.git-fanta'
    assert plist['CFBundleExecutable'] == 'git-fanta'


def test_the_obsolete_creator_code_is_gone():
    """CFBundleSignature is a four-character code from the Classic Mac OS era.

    Modern macOS ignores it, and the value carried over from the project this
    was forked from named that project instead of this one.
    """
    assert 'CFBundleSignature' not in _plist()


def test_the_version_placeholders_survive_for_the_build_to_substitute():
    """garden macos/app rewrites these two values with the real version."""
    plist = _plist()

    assert plist['CFBundleVersion'] == '0.0.0.0'
    assert plist['CFBundleShortVersionString'] == '0.0.0'
