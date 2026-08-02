"""Every packaging file states the same, fork-owned version.

This repository carries the upstream project's git history, so a version that
looks like one of that project's releases is not obviously wrong to a reader --
it just quietly ships. The three literals below are the ones a build can pick
up, and they have to agree with each other and with the fork's own tags.
"""

import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _builtin_version():
    """Read the committed fallback version from fanta/_version.py."""
    text = (REPO_ROOT / 'fanta' / '_version.py').read_text(encoding='utf-8')
    match = re.search(
        r"""^VERSION\s*=\s*(['"])([^'"]+)\1\s*$""",
        text,
        re.MULTILINE,
    )
    assert match, 'fanta/_version.py has no VERSION assignment'
    return match.group(2)

def _pyproject_fallback_version():
    """setuptools_scm uses this whenever no tag describes the checkout."""
    text = (REPO_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    match = re.search(r'^fallback_version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, 'pyproject.toml has no setuptools_scm fallback_version'
    return match.group(1)


def _pynsist_value(section, key, text=None):
    """Read one key out of one section of a pynsist config.

    pynsist.cfg has two `version` keys -- the application's and the Python
    interpreter's -- so anything that reads or writes one of them has to say
    which section it means.
    """
    if text is None:
        text = (REPO_ROOT / 'pynsist.cfg').read_text(encoding='utf-8')
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            current = stripped
        elif current == section:
            match = re.match(rf'{key}\s*=\s*(.*)$', stripped)
            if match:
                return match.group(1).strip()
    raise AssertionError(f'pynsist.cfg has no {key} in {section}')


def _pynsist_version():
    """The version baked into the Windows installer."""
    return _pynsist_value('[Application]', 'version')


def _generator():
    """Import contrib/win32/generate-pynsist-config.py by path."""
    import importlib.util

    path = REPO_ROOT / 'contrib' / 'win32' / 'generate-pynsist-config.py'
    spec = importlib.util.spec_from_file_location('generate_pynsist_config', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_version_is_the_forks_own():
    """4.x is the upstream numbering; this fork started its own at 1.0.0."""
    version = _builtin_version()

    major = int(version.split('.')[0])
    assert major < 4, (
        f'{version} reads as a release of the project this was forked from. '
        'The fork numbers its own releases starting at 1.0.0.'
    )


def test_repository_uses_neutral_version_placeholders():
    """Release versions come from Git tags, not committed version literals."""
    assert _builtin_version() == '0.0.0'
    assert _pyproject_fallback_version() == '0.0.0'
    assert _pynsist_version() == '0.0.0'

def test_the_version_is_a_release_number():
    version = _builtin_version()

    assert re.fullmatch(r'\d+\.\d+\.\d+', version), version


def test_the_generated_installer_config_carries_the_application_version():
    """`garden pynsist` builds from the generated file, not from pynsist.cfg."""
    generator = _generator()
    source = (REPO_ROOT / 'pynsist.cfg').read_text(encoding='utf-8')

    generated = generator.substitute(source, '9.9.9')

    assert _pynsist_value('[Application]', 'version', text=generated) == '9.9.9'


def test_the_generated_installer_config_keeps_the_python_version():
    """Regression: a plain `sed -e 's/^version=.*/'` rewrites both version keys.

    pynsist then rejects the config with "'1.0.0' is not valid for py_version"
    and the Windows installer job fails.
    """
    generator = _generator()
    source = (REPO_ROOT / 'pynsist.cfg').read_text(encoding='utf-8')
    python_version = _pynsist_value('[Python]', 'version', text=source)

    generated = generator.substitute(source, '9.9.9')

    assert _pynsist_value('[Python]', 'version', text=generated) == python_version


def test_the_generator_changes_nothing_else():
    """Every other line, comments included, is passed through untouched."""
    generator = _generator()
    source = (REPO_ROOT / 'pynsist.cfg').read_text(encoding='utf-8')

    generated = generator.substitute(source, _builtin_version())

    assert generated == source


def test_the_version_output_names_git_fanta():
    """Git Fanta installs alongside git-cola, so the name in --version matters.

    A support ticket, a log line or a release check that says "cola version
    1.0.1" names the wrong application.
    """
    from fanta import version as version_module

    assert version_module.fanta_version().startswith('git-fanta version ')
    assert not hasattr(version_module, 'cola_version')


def test_the_version_command_prints_the_fork_name(capsys):
    from fanta import version as version_module

    version_module.print_version()

    assert capsys.readouterr().out.startswith('git-fanta version ')


def test_the_launcher_reports_the_fork_name():
    """End to end, through argparse and app.py, the way a user sees it."""
    import os
    import subprocess

    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / 'bin' / 'git-fanta'), '--version'],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
        env=env,
    )

    assert result.stdout.startswith('git-fanta version ')


def test_the_module_entry_point_runs():
    """`python -m fanta --version` is documented in the README.

    The rename from cola to fanta stripped everything but the docstring out of
    fanta/__main__.py, so the module ran, printed nothing and exited 0.
    """
    import os
    import subprocess

    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    result = subprocess.run(
        [sys.executable, '-m', 'fanta', '--version'],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO_ROOT),
        env=env,
    )

    assert result.stdout.startswith('git-fanta version ')


def _appstream_versions():
    """The <release version="..."> entries software centres display."""
    import xml.etree.ElementTree as ET

    versions = {}
    for path in sorted((REPO_ROOT / 'share' / 'metainfo').glob('*.metainfo.xml')):
        releases = ET.parse(path).getroot().find('releases')
        versions[path.name] = [
            release.get('version') for release in releases.findall('release')
        ]
    return versions


def test_the_appstream_metadata_has_valid_release_versions():
    """AppStream contains real releases, not the neutral build placeholder."""
    per_file = _appstream_versions()

    assert per_file, 'no AppStream metainfo files found'

    for name, versions in per_file.items():
        assert versions, f'{name} contains no releases'

        for version in versions:
            assert re.fullmatch(
                r'\d+\.\d+\.\d+',
                version,
            ), f'{name} contains invalid release version {version!r}'

        assert versions[0] != '0.0.0', (
            f'{name} uses the neutral build placeholder as a real release'
        )
