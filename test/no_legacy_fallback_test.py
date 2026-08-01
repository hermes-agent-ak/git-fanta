"""Nothing a git-cola installation leaves behind reaches Git Fanta.

Git Fanta is a fork that installs alongside git-cola. While it was still
thought of as a rename it accepted the other project's names everywhere as a
fallback: `cola.` config keys, `GIT_COLA_*` environment variables, a
`.git/GIT_COLA_MSG` commit message and a `cola-prepare-commit-msg` hook. Every
one of those let a git-cola setup change how Git Fanta behaves, which is the
opposite of two applications a user can install side by side.

The `git fanta cola` sub-command alias went with them: the fork does not answer
to the other project's name.
"""

import os

import pytest

from fanta import compat
from fanta import gitcfg
from fanta import gitcmds
from fanta import main

from . import helper
from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


def test_the_environment_helper_reads_only_the_fanta_name(monkeypatch):
    monkeypatch.setenv('GIT_FANTA_TRACE', 'fanta')
    monkeypatch.setenv('GIT_COLA_TRACE', 'cola')

    assert compat.getenv('GIT_FANTA_TRACE') == 'fanta'


def test_a_git_cola_environment_variable_is_ignored(monkeypatch):
    monkeypatch.delenv('GIT_FANTA_TRACE', raising=False)
    monkeypatch.setenv('GIT_COLA_TRACE', 'cola')

    assert compat.getenv('GIT_FANTA_TRACE', 'default') == 'default'


def test_the_legacy_environment_helpers_are_gone():
    """Guard: bringing the fallback back must break a test, not just a review."""
    assert not hasattr(compat, 'getenv_with_legacy')
    assert not hasattr(compat, 'legacy_env_name')


def test_a_cola_config_key_does_not_reach_git_fanta(app_context):
    """`cola.icontheme` in ~/.gitconfig used to configure both applications."""
    app_context.git.config('cola.icontheme', 'dark')
    config = gitcfg.GitConfig(app_context)
    config.update()

    assert config.get('fanta.icontheme', default='light') == 'light'


def test_a_fanta_config_key_still_works(app_context):
    app_context.git.config('fanta.icontheme', 'dark')
    config = gitcfg.GitConfig(app_context)
    config.update()

    assert config.get('fanta.icontheme', default='light') == 'dark'


def test_the_legacy_config_helpers_are_gone():
    assert not hasattr(gitcfg, 'legacy_config_key')
    assert not hasattr(gitcfg, 'LEGACY_CONFIG_PREFIX')


def test_commit_message_path_uses_the_fanta_file(app_context):
    path = app_context.git.git_path('GIT_FANTA_MSG')
    helper.write_file(path, 'a message')

    assert gitcmds.commit_message_path(app_context) == path


def test_a_git_cola_commit_message_file_is_ignored(app_context):
    """.git/GIT_COLA_MSG belongs to the other application's session."""
    helper.write_file(app_context.git.git_path('GIT_COLA_MSG'), 'their message')

    assert gitcmds.commit_message_path(app_context) is None


def test_commit_message_path_returns_none_without_a_file(app_context):
    assert gitcmds.commit_message_path(app_context) is None


def test_save_commitmsg_writes_the_fanta_file(app_context):
    from fanta import core

    path = app_context.model.save_commitmsg('hello')

    assert path.endswith('GIT_FANTA_MSG')
    assert core.read(path) == 'hello\n'


def test_a_cola_prepare_commit_msg_hook_is_ignored(app_context):
    """The hook is executable code; running the other project's is not ours."""
    hooks_path = app_context.cfg.hooks_path('cola-prepare-commit-msg')
    os.makedirs(os.path.dirname(hooks_path), exist_ok=True)
    helper.write_file(hooks_path, '#!/bin/sh\n')

    assert gitcmds.prepare_commit_message_hook(app_context).endswith(
        'fanta-prepare-commit-msg'
    )


def test_the_fanta_sub_command_still_parses():
    """Characterization: `git fanta fanta` is how main() routes the default."""
    args = main.parse_args(['fanta'])

    assert args.func is not None


@pytest.mark.parametrize('argv', [['cola'], ['cola', '--prompt']])
def test_git_fanta_cola_is_rejected(argv, capsys):
    """`git fanta cola` answered to the other project's name."""
    with pytest.raises(SystemExit):
        main.parse_args(argv)

    assert 'invalid choice' in capsys.readouterr().err
