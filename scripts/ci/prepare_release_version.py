#!/usr/bin/env python3
"""Inject the Git tag version into non-Python build files."""

from __future__ import annotations

import re
import sys
from pathlib import Path


VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def replace_once(
    path: Path,
    pattern: re.Pattern[str],
    replacement: str,
) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(replacement, text, count=1)

    if count != 1:
        raise RuntimeError(
            f"Expected exactly one matching version in {path}, found {count}"
        )

    path.write_text(updated, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: prepare_release_version.py VERSION",
            file=sys.stderr,
        )
        return 2

    version = sys.argv[1]

    if not VERSION_PATTERN.fullmatch(version):
        print(
            f"Invalid release version: {version!r}",
            file=sys.stderr,
        )
        return 2

    replace_once(
        Path("pynsist.cfg"),
        re.compile(r"(?m)^(version\s*=\s*).+$"),
        rf"\g<1>{version}",
    )

    Path("fanta/_version.py").write_text(
        '"""Generated fallback version for packaged applications."""\n\n'
        f'VERSION = "{version}"\n',
        encoding="utf-8",
    )

    print(f"Prepared build files for version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
