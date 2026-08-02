---
status: completed
completed_at: 2026-08-01
plan_commit: n/a (executed directly from a review brief, documented afterwards)
implementation_branch: cicd/opus5
implementation_head: see git log for the seven commits listed below
ci_run: not run (verified locally)
manual_verification: |
  - built a wheel with `python -m build --wheel` and read its entry points and version
  - installed git-cola 4.19.0 and that wheel into one virtualenv and compared bin/
  - ran `python -m sphinx -b man` and confirmed git-fanta-dag.1 is produced
  - simulated the Info.plist version substitution the macOS build performs
---

# Git Fanta installs alongside git-cola

**Created:** 2026-08-01
**Branch:** `cicd/opus5`
**Baseline:** `7fd6cd7b`, i.e. after the `cola` -> `fanta` Python package rename of
`docs/plans/2026-08-01-paint-performance-and-fanta-module.md`.

This is a design record written after the work, not a plan that was executed. It exists so that a
later reader can see which of these decisions are load-bearing.

---

## The problem

The Python package rename removed the biggest obstacle: `pyproject.toml` packages only `fanta`
and `fanta.*`, so `import cola` and `import fanta` can coexist in one environment. What remained
were the names the two projects present to the *outside*: installed commands, desktop files,
AppStream ids, the Qt application name, the configuration directory, and the version number.

Git Fanta is meant to be installed **next to** git-cola, as a separate desktop application. Every
name it claims must therefore be its own.

## What changed

### 1. `git-dag` became `git-fanta-dag`

`git-dag` was the last shared name, and it was shared in five places at once: the console script,
`/usr/bin/git-dag`, `git-dag.desktop`, the AppStream id `git-dag.desktop`, and the Windows
installer command. Installing both projects meant the last one to be installed won the launcher,
and `dpkg`/`rpm` would report a file conflict.

Everything the fork installs is now `git-fanta-dag`: the entry point, `bin/git-fanta-dag`,
`share/applications/git-fanta-dag.desktop`, `share/metainfo/git-fanta-dag.metainfo.xml`, the
pynsist shortcut and command, and the `git-fanta-dag.1` man page.

**No `git-dag` compatibility alias is installed.** That alias *is* the collision — installing it
"for compatibility" reintroduces exactly the bug. The `git fanta dag` sub-command is the
in-application spelling and is unaffected.

Two related repairs came with it, both in the uninstall path:

- `make uninstall` removed `$prefix/bin/cola`, which is git-cola's launcher and was never
  installed by this fork. It removes `bin/fanta` now.
- It also removed `git-dag.desktop` and `git-dag.appdata.xml`, i.e. files git-cola owns.

Both metainfo files moved to the modern `.metainfo.xml` extension while the DAG one was being
renamed anyway. The Makefile and `garden.yaml` install them by glob, so only the uninstall lines
name them.

### 2. The DAG window has its own application name

`enforce_single_instance()` (`fanta/app.py`) derives the `QSystemSemaphore` key and the shared
memory id from `context.app_name`. Both projects used `app_name='Git DAG'`, so with
`--single-instance` each one attached to the other's shared memory segment and refused to start,
reporting that it was already running in that directory.

Both entry points -- `fanta/dag.py:cmd_dag` and `fanta/main.py:cmd_dag` -- now pass
`'Git Fanta DAG'`. `test/dag_test.py` pins both, because a name that only one of the two launch
paths uses is a name that drifts.

### 3. git-cola's configuration is never adopted

Two code paths pulled the other application's state in silently:

- `app.initialize()` called `resources.migrate_config_home()`, which copied
  `~/.config/git-cola` to `~/.config/git-fanta` on first run.
- `Settings.asdict()` fell back to `~/.config/git-cola/settings`, and failing that to the much
  older `~/.cola`, whenever no Git Fanta settings file existed.

Both were correct for a *rename* and wrong for a *fork that installs alongside* the original. The
effect was that Git Fanta inherited themes, layouts, bookmarks and sessions unasked, and a fault
in the adopted configuration looked like a Git Fanta bug.

`resources.migrate_config_home()`, `resources.legacy_config_home()` and
`resources.LEGACY_CONFIG_DIRNAME` are gone. `test/config_isolation_test.py` asserts their absence,
so re-adding a silent migration turns a test red rather than passing review.

**What deliberately stayed:** the read-only `cola.*` git-config fallback in `fanta/gitcfg.py`.
A `fanta.<key>` always wins over a `cola.<key>` of the same name and Git Fanta never *writes* a
`cola.` key. It is now documented as transitional in the CONFIGURATION VARIABLES section of
`docs/git-fanta.rst`, including the consequence: with both applications installed, a `cola.<key>`
in `~/.gitconfig` influences both, so Git Fanta settings should be spelled `fanta.<key>`.

A visible "Import settings from git-cola" action is the right successor feature. It is not
implemented here, because the point of this work package is that nothing happens behind the
user's back.

### 4. The macOS CI job installs only Git Fanta's dependencies

The job ran `brew install git-cola` before building the bundle. That made a green macOS job prove
less than it appeared to: any dependency Git Fanta failed to declare was supplied by that
formula, a git-cola tool could be picked up from Homebrew during the build, and a coexistence
test run in that environment would be meaningless. The job now sets up Python explicitly and
installs `git`.

The two orientation notes that recorded the brew line as deliberate were corrected in the same
commit. They were right when they were written and wrong afterwards, which is the failure mode
worth guarding against.

### 5. The metadata points at this fork

`homepage`, `bugtracker` and `vcs-browser` in both AppStream components, and `bug_url` in the
About dialog, pointed at git-cola. Bug reports filed from Git Fanta's About dialog landed on the
wrong project's tracker.

The screenshot was a git-cola screenshot captioned "Git Fanta running on Linux". It was dropped
rather than re-captioned; add a real one when one is hosted.

The README told macOS users that the easy way to install Git Fanta is `brew install git-cola`,
and the Windows section linked to git-cola's releases page. There is no Homebrew formula for this
fork.

### 6. The macOS bundle is unambiguous

`Info.plist` defined `CFBundleName` twice, "Git Fanta" and then "git-fanta". A plist dict with a
duplicate key is invalid and the last definition wins, so the bundle announced itself under the
lowercase command name. There is one `CFBundleName` now, plus `CFBundleDisplayName`.

`CFBundleSignature` was still the four-character creator code of the upstream project. Modern
macOS ignores the field and `PkgInfo` already carries the neutral `APPL????`, so it was dropped
rather than renamed.

The two version placeholders stay, because `garden macos/app` and the `git-fanta.app` Makefile
target substitute them. **The four-part `CFBundleVersion` must be substituted before the
three-part `CFBundleShortVersionString`**, because `sed`'s `.` matches any character; the file
comment records this.

`test/macos_bundle_test.py` pins all of it. The duplicate-key check reads the XML directly:
`plistlib` collapses duplicate keys into one dict entry and cannot detect them.

### 7. The version is the fork's own

`fanta/_version.py`, `[tool.setuptools_scm] fallback_version` and `pynsist.cfg` all said `4.19.0`.
Because this repository carries the upstream git history, a build reporting `4.19.0` does not look
wrong to a reader -- it just ships and looks like an official upstream release. All three now say
`1.0.0`, matching the `v1.0.0` tag on `main`.

pynsist cannot interpolate its version, so `garden pynsist` substitutes it from
`fanta/_version.py` into `pynsist.generated.cfg`. **That file has to sit next to `pynsist.cfg`**,
not under `build/`: every path inside a pynsist config is resolved relative to the config file's
own directory.

`test/version_test.py` keeps the three literals from drifting apart and rejects a 4.x number
outright.

## Measured, not assumed

Built with `python -m build --wheel` off `ead3bfb3`:

```
Version: 1.0.1.dev9507+gead3bfb34.d20260801

[console_scripts]
fanta = fanta.main:main
git-fanta = fanta.main:main
git-fanta-dag = fanta.dag:main
git-fanta-sequence-editor = fanta.sequenceeditor:main
```

Installed into one virtualenv together with `git-cola 4.19.0`:

```
cola                        git-fanta
fanta                       git-fanta-dag
git-cola                    git-fanta-sequence-editor
git-cola-sequence-editor
git-dag
```

Eight scripts, no overlap. `bin/git-dag` imports `cola.dag`, `bin/git-fanta-dag` imports
`fanta.dag`, and both `import cola` and `import fanta` resolve.

## Still open

- **The real coexistence gate.** The check above covers one Python environment on Linux. Building
  the Windows installer, the macOS bundle and a Linux package and installing them next to
  git-cola is the test that would prove the desktop-integration half -- the `.desktop` files, the
  AppStream ids, `/usr/bin`, the Start menu. That belongs in GitHub Actions as the last gate
  before a release.
- **No tag was created.** `v1.0.0` already exists on `main` but does not describe `dev`. Deciding
  what the next tag is and where it goes is a release decision.
- **`developer_name` in both AppStream components still names the upstream author.** Changing
  attribution is a decision for the maintainer, not a packaging fix.
- **The hotkeys fallback URL** in `fanta/widgets/about.py` still points at the upstream docs site.
  It is a content fallback for a missing local file, not an identity claim, and this fork hosts
  no replacement yet.
- **62 Sphinx heading-underline warnings** in `docs/git-fanta.rst`. They date from the
  `cola.` -> `fanta.` config-key rename, which made every key two characters longer than its
  underline. The build succeeds; fixing them is a separate mechanical pass.
