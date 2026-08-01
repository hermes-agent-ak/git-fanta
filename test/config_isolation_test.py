"""Git Fanta keeps its configuration strictly separate from git-cola's.

Git Fanta is a fork that is meant to be installed alongside git-cola, not a
drop-in replacement for it. Silently adopting ~/.config/git-cola would make
one application's themes, layouts, bookmarks and sessions leak into the other,
and a fault in the adopted configuration would look like a Git Fanta bug.

Importing git-cola's settings is therefore a decision for the user to make
explicitly, not something that happens behind their back on first start.
"""

from fanta import app
from fanta import resources
from fanta.settings import Settings


def test_the_config_home_is_git_fanta(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))

    assert resources.config_home('settings') == str(tmp_path / 'git-fanta' / 'settings')


def test_startup_does_not_copy_the_git_cola_config_directory(monkeypatch, tmp_path):
    """A git-cola installation on the same machine is left completely alone."""
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    legacy = tmp_path / 'git-cola'
    legacy.mkdir()
    (legacy / 'settings').write_text('{"recent": []}', encoding='utf-8')

    app.initialize()

    assert not (tmp_path / 'git-fanta').exists()
    # And the git-cola directory itself is untouched.
    assert (legacy / 'settings').read_text(encoding='utf-8') == '{"recent": []}'


def _isolate_settings(monkeypatch, tmp_path):
    """Point Settings at an empty configuration directory under tmp_path.

    Settings.config_path is a class attribute resolved at import time, so
    setting XDG_CONFIG_HOME alone would leave it pointing at the real
    ~/.config/git-fanta.
    """
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(
        Settings, 'config_path', str(tmp_path / 'git-fanta' / 'settings')
    )


def test_settings_ignore_the_git_cola_settings_file(monkeypatch, tmp_path):
    """Bookmarks and recent repositories do not cross over from git-cola."""
    _isolate_settings(monkeypatch, tmp_path)
    legacy = tmp_path / 'git-cola'
    legacy.mkdir()
    (legacy / 'settings').write_text(
        '{"bookmarks": [{"name": "cola", "path": "/tmp/cola"}]}', encoding='utf-8'
    )

    settings = Settings()

    assert settings.asdict() == {}


def test_settings_ignore_the_dot_cola_file(monkeypatch, tmp_path):
    """The pre-XDG ~/.cola file belongs to git-cola too."""
    _isolate_settings(monkeypatch, tmp_path)
    (tmp_path / '.cola').write_text(
        '{"bookmarks": [{"name": "cola", "path": "/tmp/cola"}]}', encoding='utf-8'
    )

    settings = Settings()

    assert settings.asdict() == {}


def test_no_migration_helpers_remain():
    """Guard: re-adding a silent migration must break a test, not just a review."""
    assert not hasattr(resources, 'migrate_config_home')
    assert not hasattr(resources, 'legacy_config_home')
    assert not hasattr(resources, 'LEGACY_CONFIG_DIRNAME')
