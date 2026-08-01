---
status: completed
completed_at: 2026-08-02
plan_commit: n/a (executed directly from a review brief, documented afterwards)
implementation_branch: cicd/opus5
implementation_head: see the commits listed below
ci_run: pending -- three consecutive green runs are the release gate
manual_verification: |
  - fed the generated pynsist config to pynsist's own read_and_validate()
  - ran bin/git-fanta --version, bin/git-fanta-dag --version and python -m fanta --version
  - measured the whole-suite segfault 38 times across four configurations
---

# Release readiness

**Created:** 2026-08-02
**Branch:** `cicd/opus5`
**Baseline:** `a04568af`, i.e. after `docs/plans/2026-08-01-deployment-separation.md`.

Second design record. The first work package made Git Fanta installable next to git-cola; this
one removes what was left between that and a public release.

---

## 1. The Windows installer job was broken by the previous work package

`garden pynsist` substituted the version with `sed -e 's/^version=.*/version=X/'`. pynsist.cfg has
**two** `version=` keys -- `[Application] version` and `[Python] version` -- so the generated
config claimed Python 1.0.0 and pynsist refused it:

```
Error in config values:
'1.0.0' is not valid for py_version, expected Python >= 3.5.0
```

The substitution lives in `contrib/win32/generate-pynsist-config.py` now. It tracks the current
section and passes every other line through byte for byte, comments included.
`test/version_test.py` pins that `[Python] version` survives.

## 2. The intermittent segfault

**Not fixed. Bounded.** The full suite printed `Fatal Python error: Segmentation fault` in roughly
one run in four, which is why a release workflow could not depend on it.

| Configuration | Crashes |
|---|---|
| shared process, branch under development | 4/10 |
| shared process, merge base | 2/10 |
| shared process, merge base + only the branch's new test files | 1/6 |
| shared process, QtWebEngine import blocked | 2/10 |
| shared process, every teardown closing its widgets | 3/12 |
| `test/widgets_main_history_test.py` alone | 0/15 |
| **split into two pytest processes** | **0/7** |

Every attributable crash lands in `test/widgets_main_history_test.py`, but at a different place
each time: `widgets/dag.py` `__init__`, `widgets/main.py` `__init__`,
`widgets/text.py:_refresh_rect` via `diff.py:resizeEvent`, once inside `subprocess._execute_child`.
A moving crash site with a fixed file is not a bug in that file's assertions.

Two hypotheses were tested and refuted:

- **QtWebEngine.** `fanta/app.py` imports `QtWebEngineWidgets` at module import time, and a
  Chromium-initialising process that also `fork()`s is a known source of exactly this. Blocking
  the import changed nothing.
- **Teardown.** Four test files deleted their widgets without closing them first, while two
  closed them. Unifying them changed nothing.

`garden test` is therefore two invocations: everything except that file, then that file. This is
the containment the review sanctioned, not an explanation. **Do not merge the two invocations
back together without re-measuring.** The teardown unification was kept regardless, because
`managed_qobject` is documented as closing widgets and four files did not.

Both CI workflows now set `timeout-minutes`, so a hung job fails instead of holding a runner --
one earlier run sat "in progress" for two hours.

## 3. garden.yaml described the upstream project, not this one

The main tree cloned from GitLab as `git-fanta/git-cola.git`, carried 79 of the upstream
project's contributor remotes, and set `remote.origin.pushurl` and `remote.publish.pushurl` to
git-cola repositories. `garden grow` writes those into `.git/config` verbatim.

Worse, the `pages` tree pushed to `git-cola/git-cola.gitlab.io` and `git-cola/git-cola.github.io`
-- the upstream project's own website repositories -- and its `publish` command runs `git push`.
The `deb`, `fedora` and `flatpak` trees named repositories that do not exist for this fork.

The main tree now clones from `github.com/hermes-agent-ak/git-fanta` with a single fetch-only
`upstream` remote. The packaging and website trees are gone until there are real, fork-owned
repositories to name. `garden publish` (a `twine upload` to PyPI) and `garden release` (which
called `./todo/release`, a script that does not exist here) are gone with them.

Three tests in `test/rename_guard_test.py` replace the old assertion that upstream remotes are
*present*: no tree may clone from or push to a git-cola URL, the only git-cola reference is the
fetch remote, and there is no publish command.

## 4. Everything user-visible named the wrong project

- **`--version`** printed `cola version 1.0.1` from `version.cola_version()`. All three launchers
  and the startup dialog's logo did. It is `fanta_version()` and prints `git-fanta version X`.
- **The README** opened with `git clone https://github.com/git-cola/git-cola.git`, showed the
  upstream project's CI badge, OpenSSF badge, pre-commit.ci badge and issue counters, linked its
  screenshots, downloads, hotkeys and readthedocs pages, told macOS users to `brew install
  git-cola`, told everyone to `pip install git-fanta` from PyPI where this fork is not published,
  and listed apt/dnf/emerge/zypper/AUR/SlackBuilds/FreeBSD packages that do not exist.
  Attribution moved into a **Based on git-cola** section that says what the relationship is.
- **`python -m fanta`** did nothing. The package rename stripped everything but the docstring out
  of `fanta/__main__.py`, so it exited 0 and printed nothing -- while the README documented it.

The rename guard used to pin the wrong clone URL *as an upstream reference to preserve*. A guard
can encode a mistake; this one did.

## 5. The git-cola compatibility fallbacks are gone

Removed on the maintainer's decision, to make the fork genuinely independent:

| Fallback | What it let happen |
|---|---|
| `cola.` git-config prefix | one `~/.gitconfig` configured both applications |
| `GIT_COLA_*` environment variables | `GIT_COLA_TRACE`, `GIT_COLA_ICON_THEME` reached this application |
| `.git/GIT_COLA_MSG` | the other application's unsaved commit message for that repository |
| `cola-prepare-commit-msg` hook | executable code installed for a different application |
| `git fanta cola` alias | the fork answered to the other project's name |

The first three were named in the review; the commit-message file and the hook are the same class
and went with them. `test/no_legacy_fallback_test.py` pins all five and guards against the helper
functions coming back.

**`icons.cola()` and `ColaApplication` stay.** They are internal names, not user-visible, and
renaming `icons.cola()` removes a toolbar icon silently -- see the gotchas.

## 6. Version and release pipeline

`v1.0.0` is tagged on `main` and a build of this branch reported `1.0.1.dev...`, so this work
cannot ship as 1.0.0 again. It is **1.0.1**: a technical release, no user-visible features.

Four sources have to move together, and now do:

```
fanta/_version.py
pyproject.toml       [tool.setuptools_scm] fallback_version
pynsist.cfg          [Application] version
share/metainfo/*.metainfo.xml   the newest <release version="...">
```

`test/version_test.py` holds all four to the same value; the AppStream entries were a fourth
source of truth that nothing was watching.

**`fallback_version` is not used verbatim.** setuptools_scm applies the version scheme to it, so
an untagged build off this branch reports `1.0.2.dev<distance>+g<sha>` -- the next dev version
after 1.0.1, which is what an untagged commit after a release is. Measured: building from a clone
with `v1.0.1` tagged on HEAD produces exactly `git_fanta-1.0.1`, and that wheel installed next to
git-cola 4.19.0 gives eight distinct console scripts, `import cola` and `import fanta` both
resolving, `bin/git-dag` importing `cola.dag`, `bin/git-fanta-dag` importing `fanta.dag`, and
`git-fanta --version` printing `git-fanta version 1.0.1`.

`.github/workflows/release.yml` builds sdist, wheel, the Windows installer and the macOS bundle
from a `v*` tag, writes `SHA256SUMS` and publishes a GitHub Release. Its first job **refuses a tag
that disagrees with `fanta/_version.py`**, so a release cannot ship artifacts whose reported
version is not the one people downloaded.

## Still open

- **Signing and notarization.** The macOS bundle and the Windows installer are unsigned; that
  needs certificates this repository does not hold. The release notes say so and tell macOS users
  about the quarantine attribute.
- **PyPI.** Deliberately not wired up. If it ever is, it belongs in `release.yml` behind a token
  secret, not back in `garden.yaml`.
- **The real coexistence gate** with built Windows, macOS and Linux packages installed next to
  git-cola. The one-virtualenv check in the previous work package is not a substitute for testing
  `/usr/bin`, the `.desktop` files and the Start menu.
- **The segfault itself.** Bounded, not understood.
- **`developer_name`** in both AppStream components still names the upstream author. Changing
  attribution is the maintainer's decision.
- **62 Sphinx heading-underline warnings** in `docs/git-fanta.rst`, left over from the
  `cola.` -> `fanta.` key rename. The build succeeds.
