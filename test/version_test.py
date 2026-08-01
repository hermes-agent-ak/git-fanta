"""Every packaging file states the same, fork-owned version.

This repository carries the upstream project's git history, so a version that
looks like one of that project's releases is not obviously wrong to a reader --
it just quietly ships. The three literals below are the ones a build can pick
up, and they have to agree with each other and with the fork's own tags.
"""

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _builtin_version():
    """Read VERSION out of fanta/_version.py, the single source of truth."""
    text = (REPO_ROOT / 'fanta' / '_version.py').read_text(encoding='utf-8')
    match = re.search(r"^VERSION\s*=\s*'([^']+)'", text, re.MULTILINE)
    assert match, 'fanta/_version.py has no VERSION assignment'
    return match.group(1)


def _pyproject_fallback_version():
    """setuptools_scm uses this whenever no tag describes the checkout."""
    text = (REPO_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    match = re.search(r'^fallback_version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, 'pyproject.toml has no setuptools_scm fallback_version'
    return match.group(1)


def _pynsist_version():
    """The version baked into the Windows installer."""
    text = (REPO_ROOT / 'pynsist.cfg').read_text(encoding='utf-8')
    match = re.search(r'^version=(.+)$', text, re.MULTILINE)
    assert match, 'pynsist.cfg has no version'
    return match.group(1).strip()


def test_the_version_is_the_forks_own():
    """4.x is the upstream numbering; this fork started its own at 1.0.0."""
    version = _builtin_version()

    major = int(version.split('.')[0])
    assert major < 4, (
        f'{version} reads as a release of the project this was forked from. '
        'The fork numbers its own releases starting at 1.0.0.'
    )


def test_the_packaging_files_agree_on_the_version():
    """A build must not report a different version depending on how it was made."""
    version = _builtin_version()

    assert _pyproject_fallback_version() == version
    assert _pynsist_version() == version


def test_the_version_is_a_release_number():
    version = _builtin_version()

    assert re.fullmatch(r'\d+\.\d+\.\d+', version), version
