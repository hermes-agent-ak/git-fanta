"""Guard tests for the git-cola -> git-fanta rename.

Two invariants are pinned down here:

1. References to the upstream project (github.com/git-cola/git-cola and
   friends) stay as they are, because they point at a real project that still
   exists.
2. The product name "git-cola" appears nowhere else in the tracked sources --
   this fork calls itself git-fanta.
"""

import pathlib
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Lines carrying one of these markers are upstream references and are never
# renamed.
UPSTREAM_MARKERS = (
    'github.com/git-cola',
    'gitlab.com/git-cola',
    'git-cola.github.io',
    'git-cola.gitlab.io',
    'git-cola.readthedocs.io',
    'pypi.org/project/git-cola',
    'src.fedoraproject.org/rpms/git-cola',
    'results.pre-commit.ci',
    'flathub/com.github.git_cola',
    'brew install git-cola',
    # Deliberate mentions of the predecessor project in prose. Anyone who needs
    # to name it in a line of documentation uses exactly one of these phrasings,
    # so that the intent is readable from the sentence itself.
    'fork of git-cola',
    'renamed from git-cola',
    # Git Fanta is installed next to git-cola rather than replacing it, so the
    # sources have to talk about the other application on purpose.
    'alongside git-cola',
    # The README section that credits the project this was forked from.
    'Based on git-cola',
)

# These files and prefixes are skipped entirely.
EXEMPT_FILES = frozenset({
    'CHANGES.rst',
    'garden.yaml',
    'test/rename_guard_test.py',
    'test/config_isolation_test.py',
    'test/env_rename_test.py',
    'test/prepare_commit_msg_hook_test.py',
})
EXEMPT_PREFIXES = ('fanta/i18n/', 'docs/plans/', 'qtpy/')

# The old product name in every spelling that occurs in the repository.
LEGACY_PRODUCT_NAMES = ('git-cola', 'git_cola', 'Git Cola', 'git cola')

# Concrete upstream references that must survive the rename.
# Format: (path relative to the repository root, expected substring)
PROTECTED_REFERENCES = (
    ('README.md', 'https://github.com/git-cola/git-cola'),
    ('fanta/gravatar.py', 'https://git-cola.github.io/images/git-64x64.jpg'),
    ('fanta/widgets/about.py', 'https://git-cola.gitlab.io/share/doc/git-cola/'),
    ('fanta/widgets/log.py', 'https://git-cola.readthedocs.io/en/latest/'),
    ('fanta/settings.py', 'https://github.com/git-cola/git-cola/issues/1241'),
    ('fanta/themes.py', 'https://github.com/git-cola/git-cola/issues/905'),
    ('docs/conf.py', 'https://gitlab.com/git-cola/git-cola'),
    ('test/gravatar_test.py', 'git-cola.github.io'),
)


def tracked_text_files():
    """Yield (path, content) for every tracked text file outside the exemptions."""
    listing = subprocess.run(
        ['git', 'ls-files', '-z'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for name in listing.split('\0'):
        if not name or name in EXEMPT_FILES or name.startswith(EXEMPT_PREFIXES):
            continue
        path = REPO_ROOT / name
        if path.is_symlink() or not path.is_file():
            continue
        try:
            yield name, path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue


def test_upstream_references_are_preserved():
    """Characterization: references to the upstream project are kept."""
    missing = []
    for name, needle in PROTECTED_REFERENCES:
        path = REPO_ROOT / name
        if not path.is_file():
            missing.append(f'{name}: file is missing')
            continue
        if needle not in path.read_text(encoding='utf-8'):
            missing.append(f'{name}: "{needle}" is missing')

    assert not missing, 'Upstream references were destroyed:\n' + '\n'.join(missing)


def test_changes_rst_history_is_untouched():
    """Characterization: the upstream release history is not rewritten."""
    text = (REPO_ROOT / 'CHANGES.rst').read_text(encoding='utf-8')
    assert 'git-cola' in text
    assert 'git-fanta' not in text


def test_product_name_is_git_fanta():
    """The old product name no longer occurs outside the upstream references."""
    offenders = []
    for name, text in tracked_text_files():
        for number, line in enumerate(text.splitlines(), start=1):
            if any(marker in line for marker in UPSTREAM_MARKERS):
                continue
            if any(legacy in line for legacy in LEGACY_PRODUCT_NAMES):
                offenders.append(f'{name}:{number}: {line.strip()[:100]}')

    assert (
        not offenders
    ), f'{len(offenders)} lines still carry the old product name:\n' + '\n'.join(
        offenders[:40]
    )


def test_no_legacy_product_name_in_tracked_filenames():
    """No tracked filename still contains "git-cola" or "_activate_cola"."""
    listing = subprocess.run(
        ['git', 'ls-files', '-z'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    offenders = [
        name
        for name in listing.split('\0')
        if name
        and not name.startswith(('fanta/i18n/', 'docs/plans/'))
        and ('git-cola' in name or '_activate_cola' in name)
    ]

    assert not offenders, 'These files must be renamed:\n' + '\n'.join(offenders)


def test_garden_build_commands_use_git_fanta():
    """The fork's build commands are renamed."""
    text = (REPO_ROOT / 'garden.yaml').read_text(encoding='utf-8')

    assert './bin/git-fanta' in text
    assert 'fanta/icons/git-fanta.svg' in text
    assert './bin/git-cola' not in text


def test_garden_never_pushes_to_a_repository_the_fork_does_not_own():
    """garden.yaml is a list of remotes; a wrong one pushes to a real project.

    It arrived from the upstream project carrying that project's contributor
    remotes, its GitLab origin, and Debian/Fedora/Flatpak/website trees whose
    push URLs pointed at repositories this fork does not own -- including the
    upstream website. `garden grow` writes those into .git/config verbatim.
    """
    import yaml

    config = yaml.safe_load((REPO_ROOT / 'garden.yaml').read_text(encoding='utf-8'))

    for name, tree in config['trees'].items():
        url = tree.get('url', '')
        assert 'git-cola' not in url, f'tree {name} clones from {url}'

        gitconfig = tree.get('gitconfig') or {}
        for key, value in gitconfig.items():
            if not key.endswith('pushurl'):
                continue
            targets = value if isinstance(value, list) else [value]
            for target in targets:
                assert 'git-cola' not in target, f'tree {name}.{key} pushes to {target}'


def test_garden_only_references_the_upstream_as_a_fetch_remote():
    """The one allowed git-cola reference is a remote nobody pushes to."""
    import yaml

    config = yaml.safe_load((REPO_ROOT / 'garden.yaml').read_text(encoding='utf-8'))
    remotes = config['trees']['git-fanta']['remotes']

    assert remotes == {'upstream': '${gh-https}/git-cola/git-cola.git'}


def test_garden_has_no_publish_command():
    """Releases come from a tag through .github/workflows/release.yml.

    A `twine upload` sitting in garden.yaml uploads whatever is in dist/ to
    PyPI under this project's name, with no tag and no review.
    """
    text = (REPO_ROOT / 'garden.yaml').read_text(encoding='utf-8')

    assert 'twine upload' not in text
    assert (REPO_ROOT / '.github' / 'workflows' / 'release.yml').is_file()


def test_distribution_name_matches_pyproject():
    """version.py queries importlib.metadata with exactly the pyproject name.

    If the two drift apart, importlib.metadata raises PackageNotFoundError and
    the version display silently falls back to the built-in value.
    """
    import re

    pyproject = (REPO_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    match = re.search(r'^name\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match, 'pyproject.toml has no name entry'
    distribution = match.group(1)

    version_py = (REPO_ROOT / 'fanta' / 'version.py').read_text(encoding='utf-8')
    assert (
        f"metadata.version('{distribution}')" in version_py
    ), f'fanta/version.py does not ask for "{distribution}"'
    assert distribution == 'git-fanta'


def test_no_legacy_config_key_literals():
    """No source literal uses the old cola. config prefix any more.

    The fallback in fanta/gitcfg.py keeps forgotten keys working without ever
    turning a test red. This test is the only thing that notices them.
    """
    import re

    pattern = re.compile(r"'cola\.[a-z]")
    offenders = []
    for name, text in tracked_text_files():
        if not name.startswith(('fanta/', 'bin/')):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f'{name}:{number}: {line.strip()[:100]}')

    assert (
        not offenders
    ), 'These literals still use the old config prefix:\n' + '\n'.join(offenders)


def test_translation_template_uses_the_new_product_name():
    """The user-visible msgid strings carry the new product name."""
    pot = REPO_ROOT / 'fanta' / 'i18n' / 'git-fanta.pot'
    assert pot.is_file(), 'fanta/i18n/git-fanta.pot is missing'

    msgids = [
        line
        for line in pot.read_text(encoding='utf-8').splitlines()
        if line.startswith('msgid')
    ]
    offenders = [line for line in msgids if 'cola' in line.lower()]

    assert not offenders, 'msgid strings still carry the old name:\n' + '\n'.join(
        offenders
    )
