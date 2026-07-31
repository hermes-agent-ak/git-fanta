---
status: open
---

# Mehrfachauswahl in der History: alle betroffenen Dateien

**Erstellt:** 2026-07-31
**Branch:** Die Tasks committen auf den Branch, der beim Start ausgecheckt ist. **Niemals auf
`main`** — das Muster für Feature-Arbeit ist `tree-ui/<agent>/<modell>/<thema>`. Vor Task 1
prüfen: `git rev-parse --abbrev-ref HEAD`. Steht dort `main`, vorher einen Branch anlegen.
Dieser Plan legt selbst **keinen** an.
**Betrifft:** `FileWidget` in `cola/widgets/filelist.py` und damit **drei** Hosts: das Datei-Panel
der History im Hauptfenster, den `Files`-Dock des eigenständigen DAG-Fensters und den
Rebase-Sequenzeditor (`cola/sequenceeditor.py:227`).

---

## 0. Wie dieser Plan zu lesen ist

Der Plan ist so geschrieben, dass er **ohne Vorwissen und ohne eigene Entscheidungen**
ausgeführt werden kann.

- **Tasks strikt in der Reihenfolge 0 → 3.** Nichts überspringen.
- **Ein Task = ein Commit.** Die Commit-Message steht am Ende jedes Tasks wörtlich da und ist
  **auf Englisch** — der Plan ist deutsch, die Git-Historie nicht. Übernimm sie wörtlich.
- **Jeder Task hat RED → GREEN → VERIFIKATION.** Steht beim RED-Schritt eine erwartete
  Fehlermeldung, muss die tatsächliche Ausgabe dazu passen. Passt sie nicht: **stoppen und
  melden**, nicht weitermachen.
- **Zeilennummern sind Orientierung, nicht Wahrheit.** Vor jedem Edit steht ein `grep`, der den
  Anker findet. Benutze den `grep`, nicht die Zeilennummer.
- **Nach jedem Task ist die volle Test-Suite grün.**
- Schlägt ein Befehl fehl und der Plan nennt keinen Ausweg: **stoppen und melden.**

**Arbeitsverzeichnis.** Alle Befehle laufen im **Wurzelverzeichnis des Repositorys** — dort, wo
`pyproject.toml` und `garden.yaml` liegen. Der Plan enthält keine absoluten Pfade.

Standard-Testbefehle:

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test
```

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py
```

---

## 1. Was gebaut wird

Wählt der Anwender **mehrere** Commits aus, zeigt die Dateiliste **die Vereinigung der Dateien,
die diese Commits anfassen** — je Datei genau eine Zeile.

Heute versucht der Mehrfach-Zweig stattdessen eine **Spanne** (`git diff commits[0]~
commits[-1]`) und stürzt dabei ab, bevor irgendetwas angezeigt wird (Falle **F1**).

Festgelegte Entscheidungen:

| Frage | Entscheidung |
|---|---|
| Spanne oder Vereinigung? | **Vereinigung.** Vom Anwender so entschieden. Eine Spanne zeigt bei nicht zusammenhängender Auswahl Dateien, die nie gewählt wurden, verschluckt Änderungen, die sich innerhalb der Spanne aufheben, und liefert für jede Auswahl mit dem Root-Commit ein leeres Panel. Belege in §2. |
| Wie wird die Vereinigung geholt? | Mit **einem** Aufruf: `git show <oid1> <oid2> … --format= --numstat --raw --no-renames -z`. `git show` nimmt mehrere Revisionen und liefert je Revision einen raw+numstat-Block in der übergebenen Reihenfolge — **exakt das Format, das `parse_status_and_numstat` bereits parst** (Falle **F3**). Der Parser wird **nicht** angefasst. |
| Datei von mehreren Commits berührt? | **Eine** Zeile. Die Zahlen unter `+` und `-` werden **summiert**; Binärdateien behalten das `-`, das git statt einer Zahl schreibt (Falle **F7**). |
| Welche Reihenfolge? | **Erstes Auftreten.** Für einen einzelnen Commit ist das buchstäblich die Ausgabe von git wie heute — die Einzelauswahl ändert ihr Verhalten damit **um kein Zeichen**. Alphabetisch zu sortieren wäre eine Verhaltensänderung für den Einzelfall und ist deshalb ein Nicht-Ziel (§3). |
| Welches Statuszeichen (`A`/`M`/`D`)? | Das des **jüngsten** ausgewählten Commits, der die Datei anfasst. Ergibt sich von selbst: die Auswahl kommt nach `sort_by_generation` (`cola/widgets/dag.py:1597`) von alt nach jung, und `dict.update()` gewinnt zuletzt. |
| `STAGE`/`WORKTREE` in der Auswahl? | Kommen mit. Es sind keine Revisionen, sie brauchen ihre eigenen Befehle (`git diff-index` / `git diff-files`) und **kein** `-z`. Macht **höchstens drei** git-Aufrufe, unabhängig davon, wie viele Commits ausgewählt sind. |
| Eine Quelle scheitert? | Wird übersprungen, statt die ganze Liste zu leeren. Scheitern **alle**, ist die Liste leer — genau wie heute. |
| Wo lebt der Code? | Alles in `cola/widgets/filelist.py`. Das Widget ist geteiltes Gut dreier Hosts; die Regel gehört ins Widget, nicht in die Hosts. |

## 2. Warum Vereinigung — die Belege

Gemessen an einem eigens gebauten Repository (`C1` Root, `C2` legt `a.txt` an, `C3` legt
`middle.txt` an, `C4` legt `tmp.txt` an, `C5` löscht `tmp.txt`):

| Auswahl | Spanne (`git diff C[0]~ C[-1]`) | Vereinigung |
|---|---|---|
| `C2` + `C4`, `C3` übersprungen | `a.txt`, **`middle.txt`**, `tmp.txt` — `middle.txt` war nie ausgewählt | `a.txt`, `tmp.txt` |
| `C4` + `C5` (legt an, löscht wieder) | **leer** — die Änderungen heben sich auf | `tmp.txt` (`+1`/`-1`) |
| `C1` + `C3` (mit Root) | **leer** — `C1~` gibt es nicht, Exit 128 | `A`, `B`, `middle.txt` |

Der Root-Fall ist zugleich der Grund, warum der Absturz aus Falle **F1** so lange unbemerkt blieb:
er tritt **nur bei gültiger Spanne** auf. Bei ungültiger Spanne greift der `status != 0`-Ausstieg
vorher, und man sieht bloß ein leeres Panel.

## 3. Nicht-Ziele

- **Keine Änderung an `parse_status_and_numstat`.** Sie parst die Ausgabe von `git show` über
  mehrere Revisionen bereits richtig — gemessen, siehe Falle **F3**.
- **Keine Änderung an `list_files` oder `FileTreeWidgetItem`.** Die neue Funktion liefert genau
  das Zeilenformat `adds\tdels\tpath`, das beide schon erwarten.
- **Keine alphabetische Sortierung der Dateiliste.** Sie wäre eine Verhaltensänderung für die
  Einzelauswahl (heute: git-Reihenfolge) und ist nicht Teil des Auftrags.
- **Keine Änderung am Beschreibungs-Panel.** Dessen Regel „bei Mehrfachauswahl den jüngsten
  Commit zeigen" steht bereits richtig in `docs/plans/2026-08-01-commit-description-panel.md`.
  Siehe §6.
- **Keine Änderung an `cola/widgets/dag.py`, `cola/widgets/main.py` oder
  `cola/sequenceeditor.py`.** Alle drei rufen `commits_selected(commits)` unverändert auf.
- **Keine Behandlung von Tabulatoren in Pfaden.** `list_files` und `FileTreeWidgetItem` nehmen
  seit jeher `path = texts[2]` nach `split('\t')`; die neue Funktion tut dasselbe. Ein Pfad mit
  einem echten Tabulator wäre schon heute falsch dargestellt — das ist ein eigenständiges Thema.
- **Kein `widget_version`-Bump**, kein neuer Zustandsschlüssel, keine neue Menü-Aktion.

## 4. Fallen — alle empirisch verifiziert

| # | Falle | Beleg |
|---|---|---|
| **F1** | **Der heutige Mehrfach-Zweig stürzt ab.** `oid` wird nur im Einzel-Commit-Zweig zugewiesen (`cola/widgets/filelist.py:130`), aber nach dem `if`/`else` unbedingt gelesen (`:159`). | Gemessen an einem echten Repo, Auswahl zweier Commits über gültige Spanne: `UnboundLocalError: cannot access local variable 'oid' where it is not associated with a value`, geworfen in `cola/widgets/filelist.py:159` |
| **F2** | **`--numstat -z` lässt den Pfad tabgetrennt.** Man könnte erwarten, dass `-z` auch die numstat-Felder NUL-trennt („use NULs as output field terminators"). Tut es **nicht** für den Pfad: die Zeile bleibt `adds\tdels\tpath`, nur der Datensatz endet auf NUL. Deshalb funktioniert `parse_status_and_numstat` unverändert. | Gemessen mit git 2.53.0: `git show <oid> --format= --numstat --raw --no-renames -z` → `:100644 100644 5626abf 9a72323 M<NUL>one.txt<NUL>1<TAB>0<TAB>one.txt<NUL>` |
| **F3** | **`git show` nimmt mehrere Revisionen** und liefert je Revision einen eigenen raw+numstat-Block, **in der übergebenen Reihenfolge**, im selben NUL-Format wie für eine. Das ist der ganze Trick dieses Plans. | Gemessen: `git show C1 C2 …` → `:…A<NUL>a.txt<NUL>1<TAB>0<TAB>a.txt<NUL>:…M<NUL>f.txt<NUL>1<TAB>0<TAB>f.txt<NUL>`. `git show C2 C1` liefert dieselben Blöcke in umgekehrter Reihenfolge, sortiert also **nicht** um. |
| **F4** | **Ein Merge-Commit liefert numstat ohne raw.** Der Statusteil fehlt komplett; `status_by_path` bleibt für diese Pfade leer und das Icon fällt auf den Dateinamen zurück. Das ist heute schon so und bleibt so. | Gemessen: `git show <merge> --format= --numstat --raw --no-renames -z` → nur `1<TAB>0<TAB>side.txt<NUL>`. Abgedeckt von `test_parser_tolerates_numstat_without_raw` |
| **F5** | **`git show <root>` funktioniert, `<root>~` nicht.** Genau deshalb ist die Vereinigung für den Root-Commit richtig und die Spanne leer. | Gemessen: `git show <root> --format= --numstat --raw -z` → `:000000 100644 0000000 4286f42 A<NUL>root.txt<NUL>1<TAB>0<TAB>root.txt<NUL>`; `git diff <root>~ …` → Exit 128, `fatal: ambiguous argument …` |
| **F6** | **Ein Test zählt die `git show`-Aufrufe.** `test_public_selection_reaches_all_standalone_consumers_synchronously` (`test/widgets_dag_history_test.py:371`) monkeypatcht `git.show` und prüft `len(show_calls) == 1` (`:399`) — bei Einzelauswahl. Der Ein-Aufruf-Entwurf dieses Plans hält das ein; „ein `show` je Commit" hätte es gebrochen. | `test/widgets_dag_history_test.py:399`; gemessen mit der neuen Implementierung: Einzelauswahl → 1 Aufruf, sechs Commits → **ebenfalls 1** |
| **F7** | **Binärdateien haben `-` statt einer Zahl.** Wer die Zahlen summiert, muss das aushalten, sonst fliegt `ValueError` in `int()`. | Gemessen: `git show <oid> … -z` für eine Binärdatei → `-<TAB>-<TAB>b.bin<NUL>` |
| **F8** | **Der Wortlaut des `UnboundLocalError` hängt von der Python-Version ab.** Ab 3.11 heißt es `cannot access local variable 'oid' where it is not associated with a value`, davor `local variable 'oid' referenced before assignment`. Der Fehler**typ** ist in beiden Fällen `UnboundLocalError` — darauf prüfen, nicht auf den Text. | Der lange Wortlaut gemessen unter Python 3.14.4. Der kurze Wortlaut ist **nicht** gemessen (keine 3.9/3.10 vorhanden) und stammt aus der bekannten CPython-Änderung |
| **F9** | **`cola/widgets/filelist.py` benutzt keine Typannotationen** und hat kein `from __future__ import annotations`. Neuer Code darf deshalb **keine** Annotationen mitbringen: `int \| None` wäre unter dem Zielinterpreter 3.9 ein Laufzeitfehler. | Gemessen: `grep -c "def .*) ->" cola/widgets/filelist.py` → `0`; `grep -n "from __future__" cola/widgets/filelist.py` → kein Treffer (`cola/git.py:1` und `cola/core.py:6` haben ihn, `filelist.py` nicht) |
| **F10** | **`pytest.ini` setzt `--doctest-modules`.** Ein `\t` in einem Docstring ist ein echter Tabulator; im Docstring **`\\t`** schreiben, so wie es `parse_status_and_numstat` bereits tut (`cola/widgets/filelist.py:292`). Ein `>>>` würde zum Test. | `pytest.ini:3`; `cola/widgets/filelist.py:292` |
| **F11** | **Es gibt einen dritten Host.** `cola/sequenceeditor.py:227` hängt `FileWidget.commits_selected` an die Auswahl des Rebase-Editors. Er ist **ungefährlich**: `sequenceeditor.py:562` schneidet die Liste mit `commits = commits[-1:]` auf **genau einen** Commit zurück, erreicht den Mehrfach-Zweig also nie. Für ihn ändert sich nichts. | `cola/sequenceeditor.py:226-228`, `:559-563` |
| **F12** | **Kein einziger Test fasst den Mehrfach-Zweig an.** Deshalb ist der Fehler überhaupt ins Release gekommen, und deshalb ist die Suite heute grün, obwohl die Funktion kaputt ist. | Gemessen: `grep -rn "commits_selected(\[.*,.*\])" test/` → kein Treffer |
| **F13** | **`STAGE` und `WORKTREE` stehen in der sortierten Auswahl immer hinten.** `RepoReader` gibt ihnen `generation = parent_commit.generation + 1` (`cola/models/dag.py:415`, `:431`), und die Auswahl läuft durch `sort_by_generation`. Deshalb gewinnt ihr Status beim `dict.update()` zuletzt — was richtig ist, sie sind der jüngste Stand. | `cola/models/dag.py:405-431`, `cola/widgets/dag.py:1597` |
| **F14** | **Zeitgleich läuft `docs/plans/2026-08-01-commit-description-panel.md`** und ändert **dieselben zwei Dateien**: es hängt `all_paths()` an `FileWidget` (dessen Task 2) und Tests an `test/widgets_history_filelist_test.py`. Verschiedene Methoden, aber dieselbe Datei. Siehe §6. | `docs/plans/2026-08-01-commit-description-panel.md`, Task 2 |

## 5. Vorhandenes, das wiederverwendet wird (nicht neu bauen)

| Vorhanden | Wo | Rolle in diesem Plan |
|---|---|---|
| `parse_status_and_numstat(output, separator)` | `cola/widgets/filelist.py:285` | **Ist** der Parser. Verarbeitet die Mehr-Revisionen-Ausgabe von `git show` unverändert (Falle **F3**) und verträgt numstat ohne raw (Falle **F4**). Wird **nicht** angefasst. |
| `FileWidget.list_files(files_log, status_by_path=None)` | `cola/widgets/filelist.py:167` | **Ist** die Anzeige. Leert selbst vorweg, deshalb braucht der leere Fall keinen Sonderweg. Erwartet Zeilen `adds\tdels\tpath` — genau das liefert die neue Funktion. |
| `app_context`-Fixture | `test/helper.py:85` | **Ist** das Testrepository: echtes `git init` in einem Temp-Verzeichnis, `chdir` hinein, `A` und `B` gestaged (noch nicht committet), echtes `git`/`cfg`/`MainModel`. Kein eigenes Repo bauen, `context.git` nicht mocken. |
| `qapp`, `managed_qobject` | `test/widgets_history_filelist_test.py:21`, `:31` | **Stehen schon in der Datei**, die dieser Plan erweitert. Nicht neu schreiben, nicht kopieren. |
| `_fake_commit(oid, summary='summary')` | `test/widgets_history_filelist_test.py:135` | **Ist** der Commit-Stellvertreter. `commits_selected` liest ausschließlich `.oid`. |
| `_git(*args)` mit `subprocess` + `.strip()` | `test/widgets_main_history_test.py:138`, `test/widgets_history_checkout_test.py:52` | **Vorlage** für den git-Helfer, den `test/widgets_history_filelist_test.py` noch nicht hat. Wörtlich dieselbe Form übernehmen. |
| `dag.STAGE`, `dag.WORKTREE` | `cola/models/dag.py:17-18` | Schon importiert (`cola/widgets/filelist.py:11`). Kein neuer Import. |

## 6. Verhältnis zum Beschreibungs-Panel

`docs/plans/2026-08-01-commit-description-panel.md` läuft parallel. Abgrenzung:

- **Dieser Plan ändert die Dateiliste, jener das Textfeld darüber.** Die Regel „bei
  Mehrfachauswahl zeigt die Beschreibung den jüngsten Commit" ist dort bereits festgelegt
  (§1 dieses Plans: „Mehrere Commits ausgewählt? → **jüngsten** (`selection[-1]`)") und in Task 4,
  Anker 4 verdrahtet. **Hier ist dafür nichts zu tun.**
- **Falle F8 jenes Plans wird durch diesen Plan gegenstandslos.** Sie beschreibt genau den
  `UnboundLocalError` und sagt „wird separat behoben, nicht hier" — das ist dieser Plan. Jener
  Plan prüft vor seinem Task 4 selbst nach, ob die Stelle repariert ist. Task 3 hier pflegt den
  Hinweis nach.
- **Eine Nebenwirkung, die dort bekannt sein sollte:** `all_paths()` liefert nach diesem Plan bei
  Mehrfachauswahl die Pfade **aller** ausgewählten Commits, während die Beschreibung nur die
  Message des jüngsten zeigt. Ein Dateiname in dieser Message kann also markiert werden, obwohl
  ihn ein *anderer* ausgewählter Commit angefasst hat. Das ist vertretbar — markiert wird, was in
  der Liste darunter steht — aber es ist eine bewusste Entscheidung, keine Unachtsamkeit.
- **Reihenfolge der beiden Pläne ist egal.** Sie berühren verschiedene Methoden. Beide Pläne
  haben denselben Arbeitsbaum-Wächter (Task 1 hier, Task 2 dort).

---

# TASKS

## Task 0 — Testlauf sicherstellen

> **Blockierend. Kein Commit.** Ziel ist eine einzige Feststellung: **welcher Testbefehl läuft
> hier?** Jeder folgende Task hängt an einer beobachteten RED- und GREEN-Ausgabe.

```bash
python3 -m pytest --version 2>&1 | head -1
ls -d env3 2>/dev/null && env3/bin/python -m pytest --version 2>&1 | head -1
command -v garden cercis isort pyupgrade mypy
python3 -c "import qtpy; print('qtpy', qtpy.API_NAME)"
```

> **Achtung — in der Umgebung, in der dieser Plan geschrieben wurde, war _nichts_ davon
> installiert.** Gemessen am 2026-07-31: `pytest`, `cercis`, `isort`, `pyupgrade`, `mypy`,
> `garden` und `ruff` fehlen alle; `env3/` gibt es nicht; `python3` ist 3.14.4; einzig `qtpy`
> (vendored im Repo-Wurzelverzeichnis) und `PyQt5` sind vorhanden, `PyQt6` nicht. Auch
> `python3 -m venv` scheitert (`ensurepip` fehlt, `python3-venv` nicht installiert) und
> `python3 -m pip` gibt es nicht.

Läuft **kein** Interpreter mit `pytest`, einen der beiden Wege versuchen:

```bash
garden dev/virtualenv && garden dev
```

```bash
python3 -m venv --system-site-packages env3 && env3/bin/python -m ensurepip --upgrade && env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

Scheitert auch das: **STOPP und melden.** Dieser Plan ist ohne laufende Tests nicht ausführbar —
er ist vollständig TDD-strukturiert, und jede RED-Erwartung unten ist eine Beobachtung, die
gemacht werden muss.

### Verifikation

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -5
```

**Erwartet:** `NNN passed`, kein `failed`, kein `error`. **Notiere `NNN` als Baseline.**

---

## Task 1 — Zeilen zusammenfassen

**Ziel:** Eine reine Funktion ohne Qt und ohne Git: `merge_numstat_rows(rows)` macht aus den
numstat-Zeilen mehrerer Commits eine Zeile je Pfad.

> Absichtlich ohne Qt geschrieben, damit sie vollständig durch einen Tabellentest festgelegt
> werden kann. Sie ist das einzige Stück echte Logik in diesem Plan.

### Schritt 1.1 — Arbeitsbaum prüfen (Falle **F14**)

```bash
git status --short cola/widgets/filelist.py test/widgets_history_filelist_test.py
```

Sind dort Änderungen, die **nicht von dir** stammen: **stoppen und melden**, statt darüber zu
schreiben. Der Beschreibungs-Panel-Plan ändert dieselben zwei Dateien.

### Schritt 1.2 (RED) — Tests schreiben

Ergänze in `test/widgets_history_filelist_test.py` den Import — **eine Zeile**, in derselben
Gruppe, alphabetisch (`merge_numstat_rows` vor `parse_status_and_numstat`):

Anker:

```bash
grep -n "^from cola.widgets.filelist import" test/widgets_history_filelist_test.py
```

```python
from cola.widgets.filelist import merge_numstat_rows
```

Hänge ans **Ende** von `test/widgets_history_filelist_test.py` an:

```python
@pytest.mark.parametrize(
    ('scenario', 'rows', 'expected'),
    (
        ('nichts', [], []),
        ('eine Zeile', ['1\t0\ta.py'], ['1\t0\ta.py']),
        (
            'zwei Dateien bleiben zwei Zeilen',
            ['1\t0\ta.py', '2\t3\tb.py'],
            ['1\t0\ta.py', '2\t3\tb.py'],
        ),
        ('dieselbe Datei wird summiert', ['1\t0\ta.py', '2\t3\ta.py'], ['3\t3\ta.py']),
        (
            'die Reihenfolge des ersten Auftretens gilt',
            ['1\t0\tb.py', '1\t0\ta.py', '1\t0\tb.py'],
            ['2\t0\tb.py', '1\t0\ta.py'],
        ),
        ('binaer bleibt binaer', ['-\t-\tb.bin'], ['-\t-\tb.bin']),
        ('binaer steckt an', ['1\t0\tb.bin', '-\t-\tb.bin'], ['-\t-\tb.bin']),
        (
            'binaer zuerst steckt genauso an',
            ['-\t-\tb.bin', '1\t0\tb.bin'],
            ['-\t-\tb.bin'],
        ),
        ('unvollstaendige Zeile wird verworfen', ['1\t0'], []),
        ('leere Zeile wird verworfen', [''], []),
    ),
)
def test_merge_numstat_rows_lists_every_path_once(scenario, rows, expected):
    """Eine Zeile je Pfad, Zahlen summiert, Binaerdateien unangetastet."""
    assert merge_numstat_rows(rows) == expected
```

**RED ausführen:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -8
```

**Erwartete Fehlermeldung — die ganze Datei scheitert beim Einsammeln:**

```
ImportError: cannot import name 'merge_numstat_rows' from 'cola.widgets.filelist'
```

> Das ist ein **Collection-Error**, kein einzelner Testfehler, und hier beabsichtigt: die Funktion
> existiert noch nicht. Zur Kontrolle vorher: `grep -c merge_numstat_rows cola/widgets/filelist.py`
> → `0`.

### Schritt 1.3 (GREEN) — Funktion anlegen

**Anker:**

```bash
grep -n "^def parse_status_and_numstat(output, separator):" cola/widgets/filelist.py
```

**Erwartet:** genau **ein** Treffer. Füge **direkt davor** ein:

```python
def _add_count(total, field):
    """Add one numstat field to a running total.

    Returns None as soon as a field is not a plain number: git writes '-'
    instead of a count for binary files, and a total that mixes counted and
    uncounted changes has no meaningful number to report.
    """
    if total is None or not field.isdigit():
        return None
    return total + int(field)


def merge_numstat_rows(rows):
    """Combine numstat rows so that every path is listed exactly once.

    Rows arrive as ``adds\\tdels\\tpath``, one per path *per commit*. A path
    that several selected commits touch is reported once, with its added and
    deleted lines summed; its first appearance decides where it sits in the
    list. A binary file keeps the '-' that git writes instead of a count.
    """
    totals = {}
    for row in rows:
        fields = row.split('\t')
        if len(fields) < 3:
            continue
        path = fields[2]
        adds, dels = totals.get(path, (0, 0))
        totals[path] = (_add_count(adds, fields[0]), _add_count(dels, fields[1]))
    return [
        '{}\t{}\t{}'.format(
            '-' if adds is None else adds, '-' if dels is None else dels, path
        )
        for path, (adds, dels) in totals.items()
    ]


```

> **Keine Typannotationen** (Falle **F9**). **`\\t` im Docstring**, nicht `\t` (Falle **F10**).
> Die Reihenfolge „erstes Auftreten" kostet keinen Code: `dict` behält seit Python 3.7 die
> Einfügereihenfolge.

### Verifikation

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -3
```

**Erwartet:** alle passed, **10 Tests mehr** als vorher.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 10 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "feat: fold per-commit numstat rows into one row per path

merge_numstat_rows() sums the added and deleted lines of a path that several
commits touch and keeps the order of its first appearance. Binary files carry
'-' instead of a count and keep it."
```

---

## Task 2 — Die Dateiliste zeigt die Vereinigung

**Ziel:** `commits_selected` beschreibt die Auswahl als Vereinigung statt als Spanne — und
stürzt dabei nicht mehr ab.

### Schritt 2.1 (RED) — Tests schreiben

Ergänze oben in `test/widgets_history_filelist_test.py` den Import. Anker:

```bash
grep -n "^import sys$" test/widgets_history_filelist_test.py
```

Füge **direkt davor** ein (alphabetisch vor `sys`):

```python
import subprocess
```

Hänge ans **Ende** der Datei an:

```python
def _git(*args):
    """Wie in test/widgets_main_history_test.py: mit strip()."""
    return subprocess.run(
        ('git', *args), check=True, text=True, capture_output=True
    ).stdout.strip()


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(content)


def _commit_file(path, content, message):
    """Schreibt, staged und committet eine Datei - und liefert die OID."""
    _write(path, content)
    _git('add', path)
    _git('commit', '-q', '-m', message)
    return _git('rev-parse', 'HEAD')


@pytest.fixture
def history_repo(app_context):
    """Sechs Commits, an denen sich Vereinigung und Spanne unterscheiden.

    app_context hat A und B bereits gestaged, aber noch nichts committet - der
    erste Commit hier ist also der Root-Commit mit genau diesen beiden Dateien.
    """
    _git('commit', '-q', '-m', 'C1 root')
    oids = {'root': _git('rev-parse', 'HEAD')}
    oids['a'] = _commit_file('a.txt', 'a\n', 'C2 add a')
    oids['middle'] = _commit_file('middle.txt', 'm\n', 'C3 add middle')
    oids['tmp'] = _commit_file('tmp.txt', 't\n', 'C4 add tmp')
    _git('rm', '-q', 'tmp.txt')
    _git('commit', '-q', '-m', 'C5 delete tmp')
    oids['untmp'] = _git('rev-parse', 'HEAD')
    oids['a_again'] = _commit_file('a.txt', 'a\nagain\n', 'C6 touch a again')
    return oids


def _listed(widget):
    """(Pfad, +, -) je Zeile, in Anzeigereihenfolge."""
    return [
        (
            widget.topLevelItem(row).path,
            widget.topLevelItem(row).text(1),
            widget.topLevelItem(row).text(2),
        )
        for row in range(widget.topLevelItemCount())
    ]


def _paths(widget):
    return [path for path, _adds, _dels in _listed(widget)]


def test_two_selected_commits_list_the_files_of_both(
    qapp, app_context, history_repo, managed_qobject
):
    """Der gemeldete Fehler: zwei Commits ueber gueltiger Spanne."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['a']), _fake_commit(history_repo['middle'])]
    )

    assert _paths(widget) == ['a.txt', 'middle.txt']


def test_non_contiguous_selection_ignores_unselected_commits(
    qapp, app_context, history_repo, managed_qobject
):
    """C3 wurde uebersprungen - middle.txt gehoert nicht in die Liste."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['a']), _fake_commit(history_repo['tmp'])]
    )

    assert _paths(widget) == ['a.txt', 'tmp.txt']


def test_selection_including_the_root_commit_lists_its_files(
    qapp, app_context, history_repo, managed_qobject
):
    """Der Root-Commit hat kein Elternteil - trotzdem sind seine Dateien da."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['root']), _fake_commit(history_repo['middle'])]
    )

    assert _paths(widget) == ['A', 'B', 'middle.txt']


def test_file_added_and_deleted_across_the_selection_stays_listed(
    qapp, app_context, history_repo, managed_qobject
):
    """C4 legt tmp.txt an, C5 loescht es - beruehrt ist es trotzdem."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['tmp']), _fake_commit(history_repo['untmp'])]
    )

    assert _listed(widget) == [('tmp.txt', '1', '1')]


def test_file_touched_twice_is_listed_once_with_summed_counts(
    qapp, app_context, history_repo, managed_qobject
):
    """Zwei Commits an derselben Datei ergeben eine Zeile, keine zwei."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected(
        [_fake_commit(history_repo['a']), _fake_commit(history_repo['a_again'])]
    )

    assert _listed(widget) == [('a.txt', '2', '0')]


def test_single_commit_selection_is_unchanged(
    qapp, app_context, history_repo, managed_qobject
):
    """Charakterisierung: die Einzelauswahl verhaelt sich wie bisher."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected([_fake_commit(history_repo['a_again'])])

    assert _listed(widget) == [('a.txt', '1', '0')]


def test_unknown_revision_leaves_the_list_empty(
    qapp, app_context, history_repo, managed_qobject
):
    """Charakterisierung: eine unbekannte OID laesst nichts uebrig."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.commits_selected([_fake_commit(history_repo['a']), _fake_commit('d' * 40)])

    assert _paths(widget) == []


def _dirty_worktree():
    """Eine gestagte und eine ungestagte Aenderung, wie sie die History zeigt.

    Kein update_status() noetig: commits_selected fragt fuer STAGE und WORKTREE
    direkt git, nicht das Modell. Verifiziert.
    """
    _write('staged.txt', 's\n')
    _git('add', 'staged.txt')
    with open('a.txt', 'a', encoding='utf-8') as handle:
        handle.write('dirty\n')


def test_stage_pseudo_commit_lists_the_staged_files(
    qapp, app_context, history_repo, managed_qobject
):
    """Charakterisierung: STAGE ist keine Revision, sondern der Index."""
    widget = managed_qobject(FileWidget(app_context, None))
    _dirty_worktree()

    widget.commits_selected([_fake_commit(dag.STAGE)])

    assert _paths(widget) == ['staged.txt']


def test_worktree_pseudo_commit_lists_the_modified_files(
    qapp, app_context, history_repo, managed_qobject
):
    """Charakterisierung: WORKTREE ist der Arbeitsbaum gegen den Index."""
    widget = managed_qobject(FileWidget(app_context, None))
    _dirty_worktree()

    widget.commits_selected([_fake_commit(dag.WORKTREE)])

    assert _paths(widget) == ['a.txt']


def test_commit_with_stage_and_worktree_lists_all_of_them(
    qapp, app_context, history_repo, managed_qobject
):
    """Commit, Index und Arbeitsbaum zusammen - drei Quellen, eine Liste."""
    widget = managed_qobject(FileWidget(app_context, None))
    _dirty_worktree()

    widget.commits_selected(
        [
            _fake_commit(history_repo['a_again']),
            _fake_commit(dag.STAGE),
            _fake_commit(dag.WORKTREE),
        ]
    )

    assert _listed(widget) == [('a.txt', '2', '0'), ('staged.txt', '1', '0')]


def test_one_git_show_serves_the_whole_selection(
    qapp, app_context, history_repo, managed_qobject
):
    """Ein Aufruf fuer alle Commits - nicht einer je Commit.

    Haelt test_public_selection_reaches_all_standalone_consumers_synchronously
    ein, das genau einen git-show-Aufruf erwartet.
    """
    widget = managed_qobject(FileWidget(app_context, None))
    calls = []
    real_show = app_context.git.show
    app_context.git.show = lambda *args, **kwargs: (
        calls.append(args) or real_show(*args, **kwargs)
    )
    selection = [history_repo['a'], history_repo['middle'], history_repo['tmp']]

    widget.commits_selected([_fake_commit(oid) for oid in selection])

    assert len(calls) == 1
    assert list(calls[0]) == selection
```

Ergänze den fehlenden Import für `dag`. Anker:

```bash
grep -n "^from cola import icons$" test/widgets_history_filelist_test.py
```

Füge **direkt darunter** ein:

```python
from cola.models import dag
```

**RED ausführen:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -25
```

**Erwartet: 7 der 11 neuen Tests rot, 4 grün.** Der genaue Schnitt ist gemessen:

| Test | heute | Grund |
|---|---|---|
| `..._two_selected_commits_list_the_files_of_both` | **RED** | `UnboundLocalError` |
| `..._non_contiguous_selection_ignores_unselected_commits` | **RED** | `UnboundLocalError` |
| `..._selection_including_the_root_commit_lists_its_files` | **RED** | **`AssertionError: assert [] == ['A', 'B', 'middle.txt']`** — hier fliegt *keine* Ausnahme, weil `root~` scheitert und der `status != 0`-Ausstieg vorher greift |
| `..._file_added_and_deleted_across_the_selection_stays_listed` | **RED** | `UnboundLocalError` |
| `..._file_touched_twice_is_listed_once_with_summed_counts` | **RED** | `UnboundLocalError` |
| `..._single_commit_selection_is_unchanged` | **grün** | Charakterisierung |
| `..._unknown_revision_leaves_the_list_empty` | **grün** | Charakterisierung |
| `..._stage_pseudo_commit_lists_the_staged_files` | **grün** | Charakterisierung |
| `..._worktree_pseudo_commit_lists_the_modified_files` | **grün** | Charakterisierung |
| `..._commit_with_stage_and_worktree_lists_all_of_them` | **RED** | `UnboundLocalError` |
| `..._one_git_show_serves_the_whole_selection` | **RED** | `UnboundLocalError` |

Der `UnboundLocalError` lautet unter Python ≥ 3.11:

```
UnboundLocalError: cannot access local variable 'oid' where it is not associated with a value
```

und unter älteren Interpretern `local variable 'oid' referenced before assignment` (Falle **F8**).
Er kommt aus `cola/widgets/filelist.py`, Zeile mit `if oid in (dag.STAGE, dag.WORKTREE):`.

> **Die vier grünen Tests sind Charakterisierungstests** — sie halten fest, was heute schon
> stimmt und nach Task 2 weiter stimmen muss. Sie sind **kein kaputtes RED**. Sind einer der
> sieben roten grün oder einer der vier grünen rot: **stoppen und melden.**

### Schritt 2.2 (GREEN) — `commits_selected` ersetzen

**Anker:**

```bash
grep -n "    def commits_selected(self, commits):" cola/widgets/filelist.py
grep -n "    def list_files(self, files_log, status_by_path=None):" cola/widgets/filelist.py
```

**Erwartet:** je genau **ein** Treffer. Ersetze **alles zwischen den beiden** — also die
vollständige Methode `commits_selected`, von ihrer `def`-Zeile bis einschließlich der Zeile
`self.list_files(numstat_rows, status_by_path=status_by_path)` — durch:

```python
    def commits_selected(self, commits):
        self.commits = list(commits)
        if not commits:
            self.clear()
            return

        status_by_path = {}
        numstat_rows = []
        for out, separator in self._changed_file_output(commits):
            parsed_status, parsed_rows = parse_status_and_numstat(out, separator)
            status_by_path.update(parsed_status)
            numstat_rows.extend(parsed_rows)

        merged_rows = merge_numstat_rows(numstat_rows)
        self.list_files(merged_rows, status_by_path=status_by_path)

    def _changed_file_output(self, commits):
        """Yield an (output, separator) pair for every source in the selection.

        The list shows the union of what the user picked, so all real commits
        are described by a single "git show" over every one of them. STAGE and
        WORKTREE are not revisions and need their own commands. A source that
        fails is skipped rather than emptying the whole list.
        """
        git = self.context.git
        oids = [
            commit.oid
            for commit in commits
            if commit.oid not in (dag.STAGE, dag.WORKTREE)
        ]
        if oids:
            # "git show" takes several revisions and emits one raw+numstat
            # block per revision, in the order given -- the same shape it
            # emits for a single one.
            status, out, _ = git.show(
                *oids,
                format='',
                numstat=True,
                raw=True,
                no_renames=True,
                z=True,
                _readonly=True,
            )
            if status == 0:
                yield out, '\0'
        # NOTE: The output from "git diff-files --numstat -z" is not equivalent
        # to the output of "git show --numstat -z". "git diff-files" does not
        # emit a NULL separator between each entry. That's why we use the
        # default output (without "-z") and split on newline instead.
        # This is also true for "git diff-index" as well.
        selected = {commit.oid for commit in commits}
        if dag.STAGE in selected:
            status, out, _ = git.diff_index(
                'HEAD', cached=True, numstat=True, raw=True, _readonly=True
            )
            if status == 0:
                yield out, '\n'
        if dag.WORKTREE in selected:
            status, out, _ = git.diff_files(numstat=True, raw=True, _readonly=True)
            if status == 0:
                yield out, '\n'
```

> **Was dabei verschwindet:** der ganze `if len(commits) > 1:`-Zweig samt seiner vier
> `git.diff`-Varianten, der `status != 0`-Ausstieg und die Separator-Wahl über `oid`. Der
> `UnboundLocalError` verschwindet nicht, weil `oid` gesetzt wird, sondern weil die Variable
> nicht mehr existiert.
>
> **Was bleibt:** der `NOTE`-Kommentar zu `diff-files`/`diff-index` — er begründet das `'\n'`
> und gehört jetzt an diese Stelle.
>
> **Keine Typannotationen** (Falle **F9**). Kein neuer Import: `dag` steht schon in Zeile 11.

### Verifikation

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -3
```

**Erwartet:** alle passed.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py test/widgets_main_history_test.py test/diff_debounce_test.py 2>&1 | tail -3
```

**Erwartet:** alle passed. Diese drei Dateien enthalten die Tests, die `commits_selected`
mitbenutzen — insbesondere den Aufrufzähler aus Falle **F6**.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 21 passed, 0 failed.

### Formatierung

```bash
garden fmt
```

Ohne `garden` dasselbe von Hand (wörtlich das, was `garden fmt` tut — `garden.yaml:76-81`, ohne
die beiden `--version`-Zeilen):

```bash
cercis bin bin/git-* cola test extras/sphinxtogithub && isort --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* cola test extras/sphinxtogithub
```

> Der Code oben ist **von Hand auf 88 Zeichen gesetzt, aber nicht mit `cercis` geprüft** — das
> Werkzeug war beim Schreiben des Plans nicht installiert. `garden fmt` darf ihn umbrechen; danach
> die Tests noch einmal laufen lassen.

### Commit

```bash
git add -A && git commit -m "fix: list the files of every selected commit

Selecting more than one commit raised UnboundLocalError: the separator was
chosen from a variable that only the single-commit branch assigned. The branch
is gone. The file list now shows the union of the files the selected commits
touch, fetched with one 'git show' over all of them, instead of a diff of the
range between the oldest and the newest.

The range was wrong in three ways a union is not: it listed files from commits
between two non-adjacent selections, it hid changes that cancelled out inside
the range, and it showed nothing at all whenever the root commit was selected,
because there is no commit before it."
```

---

## Task 3 — Dokumentation

### Schritt 3.1 — `references/fork-history.md`

Anker:

```bash
grep -n "^## " .claude/skills/project-brief/references/fork-history.md
```

Füge den neuen Abschnitt **hinter** den letzten nummerierten Abschnitt und **vor**
`## Where the fork's tests live` ein. Die Nummer ist die nächste freie — sie hängt davon ab, ob
`docs/plans/2026-08-01-commit-description-panel.md` schon durch ist. Prüfe das mit dem `grep`
oben und nimm die nächste Zahl:

```markdown
## <N>. Multi-commit selection lists the union of the touched files

Plan: `docs/plans/2026-07-31-history-multi-commit-file-list.md`.

Selecting several commits shows **every file those commits touch**, one row per file, with the
added and deleted lines summed. Before this, the multi-commit branch tried to diff the *range*
from the oldest to the newest selection and crashed with `UnboundLocalError` before showing
anything.

**Decisions that later work must not undo:**

- **Union, not range.** A range lists files from commits *between* two non-adjacent selections,
  hides changes that cancel out inside it, and shows nothing whenever the root commit is selected
  (`<root>~` does not resolve). All three measured.
- **One `git show` for the whole selection.** `git show` accepts several revisions and emits one
  raw+numstat block per revision, in the order given, in the same NUL-separated shape it uses for
  a single one. `parse_status_and_numstat` needed no change at all. One call also keeps
  `test_public_selection_reaches_all_standalone_consumers_synchronously` (which asserts exactly
  one `git.show` call) valid.
- **STAGE and WORKTREE are not revisions.** They keep their own `git diff-index` / `git
  diff-files` calls and their own newline separator. A selection therefore costs at most three
  git calls, no matter how many commits it holds.
- **Order is first appearance, not alphabetical.** That makes the single-commit case byte-for-byte
  what it was before: git's own order.
- **Binary files keep `-`.** `merge_numstat_rows()` refuses to invent a number for them, and a
  path that is binary in any one commit stays binary in the merged row.
```

Ergänze außerdem in der Testliste am Dateiende:

```markdown
- `test/widgets_history_filelist_test.py` enthält zusätzlich den Tabellentest für
  `merge_numstat_rows()` und die Mehrfachauswahl-Tests gegen ein echtes Repository
  (Fixture `history_repo`).
```

### Schritt 3.2 — `references/gotchas.md`

Hänge im passenden Abschnitt an (bei den git-Ausgabe-Fallen, dort wo die
`git show --raw`-Merge-Falle steht):

```markdown
**`git show` takes more than one revision.** `git show <a> <b> … --format= --numstat --raw
--no-renames -z` emits one raw+numstat block per revision, in the order given, in exactly the
shape `parse_status_and_numstat` already parses. It is the cheapest way to describe a whole
selection, and it works for a root commit — unlike `<root>~`, which does not resolve.

**`--numstat -z` does not NUL-separate the numstat fields.** Despite "use NULs as output field
terminators", the row stays `adds<TAB>dels<TAB>path`; only the record ends with NUL. Binary files
carry `-` instead of a count in both fields.

**`FileWidget.commits_selected` must not grow a git call per commit.**
`test_public_selection_reaches_all_standalone_consumers_synchronously`
(`test/widgets_dag_history_test.py`) monkeypatches `git.show` and asserts it ran exactly once.
```

### Schritt 3.3 — den Hinweis im Beschreibungs-Panel-Plan nachziehen

`docs/plans/2026-08-01-commit-description-panel.md` führt den hier behobenen Fehler als Falle
**F8** und sagt „Das wird separat behoben, nicht hier". Ist jener Plan noch `status: open`,
ergänze in seiner F8-Zeile am Ende:

```markdown
**Erledigt durch `docs/plans/2026-07-31-history-multi-commit-file-list.md`.** Die Integrationstests jenes Plans dürfen ab jetzt mehrere Commits auswählen; die Beschreibung zeigt weiterhin `selection[-1]`.
```

Ist er bereits `status: completed`, **nichts ändern** — abgeschlossene Pläne sind Nachschlagewerk
und werden nicht umgeschrieben (`docs/plans/README.md`).

### Schritt 3.4 — `SKILL.md`

Erhöhe die Zahl der ausgelieferten Arbeitspakete um eins und ergänze den Aufzählungssatz um
„and the multi-commit file list in the history".

Anker:

```bash
grep -n "work packages have shipped" .claude/skills/project-brief/SKILL.md
```

### Schritt 3.5 — Plan als erledigt markieren

Setze die Frontmatter dieses Plans auf `status: completed` und ergänze `completed_at`,
`plan_commit`, `implementation_branch`, `implementation_head`, `ci_run` und
`manual_verification` — wie in `docs/plans/README.md` beschrieben. Stelle die Zeile dieses Plans
in der Tabelle von `docs/plans/README.md` von **offen** auf **abgeschlossen** um.

### Verifikation

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** unverändert grün.

```bash
garden check/fmt && garden check/pyupgrade && garden check/mypy
```

Ohne `garden` dieselben Prüfungen einzeln:

```bash
cercis --check bin bin/git-* cola test extras/sphinxtogithub
isort --check --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* cola test extras/sphinxtogithub
pyupgrade --py39-plus bin/git-* bin/*.py cola/*.py cola/*/*.py
python3 -m mypy --config-file pyproject.toml bin cola
```

**Erwartet:** ohne Befund. Fehlt ein Werkzeug, ist das kein Abbruchgrund: **notieren, welche
Prüfung nicht lief**, und es im Abschlussbericht so schreiben.

### Commit

```bash
git add -A && git commit -m "docs: document the multi-commit file list"
```

---

## Manuelle Abnahme

```bash
garden run
```

Ohne `garden` — oder in einer Umgebung ohne Anzeige — über den Launcher im Repository:

```bash
env3/bin/python bin/git-fanta
```

1. Zwei benachbarte Commits in der History markieren: die Dateiliste zeigt die Dateien **beider**,
   je Datei eine Zeile. (Vorher: leeres Panel, Absturz im Log.)
2. Zwei **nicht** benachbarte Commits mit Strg+Klick markieren: es erscheinen **nur** deren
   Dateien, nichts aus den Commits dazwischen.
3. Den **ältesten** Commit der History mitmarkieren: seine Dateien sind da. (Vorher: leer.)
4. Eine Datei doppelklicken, die von mehreren markierten Commits berührt wird: das Diff-Fenster
   öffnet sich wie gewohnt.
5. Bei uncommitteten Änderungen `STAGE` und `WORKTREE` zusammen mit einem Commit markieren: alle
   drei Quellen stehen in einer Liste.
6. Dasselbe im eigenständigen DAG-Fenster (`Files`-Dock).
7. Im Rebase-Sequenzeditor eine Zeile anklicken: unverändert, dort ist immer genau ein Commit
   ausgewählt.

> **In einer Umgebung ohne Anzeige entfällt dieser Abschnitt.** Dann gilt: die Punkte 1, 2, 3 und
> 5 sind durch die Tests aus Task 2 abgedeckt; **4, 6 und 7 sind es nicht** — der Doppelklick über
> eine Mehrfachauswahl, das DAG-Fenster und der Sequenzeditor haben für diesen Fall keine
> Testabdeckung. **Im Abschlussbericht so schreiben, nicht als „geprüft" ausgeben.**
