#!/usr/bin/env python3
"""Write pynsist.generated.cfg with the application version filled in.

pynsist cannot interpolate values, so the version has to be substituted before
the build. Doing that with `sed -e 's/^version=.*/...'` is wrong: pynsist.cfg
has two `version=` keys, `[Application] version` and `[Python] version`, and
rewriting both hands pynsist a py_version of 1.0.0 and fails the build.

Usage: generate-pynsist-config.py <input.cfg> <output.cfg>

The version comes from fanta/_version.py, the single source of truth that
test/version_test.py holds pyproject.toml and pynsist.cfg to.
"""
from __future__ import annotations
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def application_version() -> str:
    """Read VERSION out of fanta/_version.py."""
    text = (REPO_ROOT / 'fanta' / '_version.py').read_text(encoding='utf-8')
    match = re.search(r"^VERSION\s*=\s*'([^']+)'", text, re.MULTILINE)
    if not match:
        raise SystemExit('fanta/_version.py has no VERSION assignment')
    return match.group(1)


def substitute(config: str, version: str) -> str:
    """Return `config` with [Application] version set to `version`.

    Every other line, including [Python] version and all comments, is passed
    through unchanged.
    """
    section = None
    lines = []
    for line in config.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            section = stripped
        elif section == '[Application]' and re.match(r'version\s*=', stripped):
            line = f'version={version}\n'
        lines.append(line)
    return ''.join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit(f'usage: {sys.argv[0]} <input.cfg> <output.cfg>')
    source, destination = (pathlib.Path(path) for path in argv)
    config = source.read_text(encoding='utf-8')
    destination.write_text(substitute(config, application_version()), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
