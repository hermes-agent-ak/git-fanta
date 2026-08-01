"""Tests fuer die Umbenennung des prepare-commit-msg-Hooks."""

import os

from fanta import gitcmds

from . import helper
from .helper import app_context

# Prevent unused imports lint errors.
assert app_context is not None


def _write_hook(context, name):
    """Lege einen ausfuehrbaren Hook mit dem angegebenen Namen an."""
    path = context.cfg.hooks_path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    helper.write_file(path, '#!/bin/sh\nexit 0\n')
    os.chmod(path, 0o755)
    return path


def test_prefers_the_new_hook_name(app_context):
    """Existiert der fanta-Hook, wird er benutzt."""
    expect = _write_hook(app_context, 'fanta-prepare-commit-msg')
    app_context.cfg.reset()

    assert gitcmds.prepare_commit_message_hook(app_context) == expect


def test_a_cola_hook_is_not_run(app_context):
    """A hook is executable code installed for the other application."""
    _write_hook(app_context, 'cola-prepare-commit-msg')
    app_context.cfg.reset()

    assert gitcmds.prepare_commit_message_hook(app_context).endswith(
        'fanta-prepare-commit-msg'
    )


def test_returns_the_new_name_when_no_hook_exists(app_context):
    """Ohne Hook wird der neue Standardpfad zurueckgegeben."""
    app_context.cfg.reset()

    result = gitcmds.prepare_commit_message_hook(app_context)

    assert result.endswith('fanta-prepare-commit-msg')
