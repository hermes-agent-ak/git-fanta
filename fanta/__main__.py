"""Run git-fanta as a Python module.

Usage: python -m fanta
"""

from fanta import main


def run() -> None:
    """Start the command-line interface."""
    main.main()


if __name__ == '__main__':
    run()
