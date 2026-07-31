---
status: open
---

# Commit-Beschreibung über der Dateiliste, mit markierten Dateinamen

**Erstellt:** 2026-08-01
**Branch:** Die Tasks committen auf den Branch, der beim Start ausgecheckt ist. **Niemals auf
`main`** — das Muster für Feature-Arbeit ist `tree-ui/<agent>/<modell>/<thema>`. Vor Task 1
prüfen: `git rev-parse --abbrev-ref HEAD`. Steht dort `main`, vorher einen Branch anlegen.
Dieser Plan legt selbst **keinen** an.
**Betrifft:** die History-Ansicht (`CommitHistoryWidget` in `cola/widgets/dag.py`) und damit
sowohl das Hauptfenster als auch das eigenständige DAG-Fenster.

---

## 0. Wie dieser Plan zu lesen ist

Der Plan ist so geschrieben, dass er **ohne Vorwissen und ohne eigene Entscheidungen**
ausgeführt werden kann.

- **Tasks strikt in der Reihenfolge 0 → 7.** Nichts überspringen.
- **Ein Task = ein Commit.** Die Commit-Message steht am Ende jedes Tasks wörtlich da und ist
  **auf Englisch** — der Plan ist deutsch, die Git-Historie nicht. Übernimm sie wörtlich.
- **Jeder Task hat RED → GREEN → VERIFIKATION.** Steht beim RED-Schritt eine erwartete
  Fehlermeldung, muss die tatsächliche Ausgabe dazu passen. Passt sie nicht: **stoppen und
  melden**, nicht weitermachen.
- **Zeilennummern sind Orientierung, nicht Wahrheit.** Vor jedem Edit steht ein `grep`, der den
  Anker findet. Benutze den `grep`, nicht die Zeilennummer.
- **Nach jedem Task ist die volle Test-Suite grün.**
- Schlägt ein Befehl fehl und der Plan nennt keinen Ausweg: **stoppen und melden.**

**Arbeitsverzeichnis und Werkzeuge.** Alle Befehle laufen im **Wurzelverzeichnis des
Repositorys** — dort, wo `pyproject.toml` und `garden.yaml` liegen. Der Plan enthält keine
absoluten Pfade.

| Im Plan geschrieben | Falls das nicht läuft |
|---|---|
| `python3 -B -m pytest …` | `env3/bin/python -B -m pytest …`, wenn `env3/` existiert |
| `garden fmt` | `cercis bin bin/git-* cola test extras/sphinxtogithub` und danach `isort --force-single-line-imports --py=39 --no-lines-before=STDLIB bin bin/git-* cola test extras/sphinxtogithub` (wörtlich das, was `garden fmt` tut — `garden.yaml:76-81`) |

Standard-Testbefehle:

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test
```

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py test/widgets_main_history_test.py test/widgets_history_filelist_test.py
```

---

## 1. Was gebaut wird

Das Panel rechts neben der Commit-Tabelle wird **waagerecht geteilt**: oben die Beschreibung des
ausgewählten Commits, unten die geänderten Dateien wie bisher.

```
files_splitter (Horizontal)                <- existiert
├── treewidget                             <- existiert
└── details_splitter (Vertical)            <- NEU
    ├── descriptionwidget                  <- NEU
    └── filewidget                         <- existiert, wandert eine Ebene tiefer
```

In der Beschreibung werden die Namen der geänderten Dateien **hervorgehoben**, damit man beim
Überfliegen sofort sieht, wovon der Text spricht.

Festgelegte Entscheidungen:

| Frage | Entscheidung |
|---|---|
| Woher kommt der Text? | `git show --no-patch --format=%B <oid>` bei jeder Auswahl. **Nicht** über `LOGFMT` (`cola/models/dag.py:15`) — das Format ist zeilenbasiert, ein mehrzeiliger Body würde das Parsen aller 1000 Commits zerlegen und deren Speicherbedarf vervielfachen. |
| Wann wird geladen? | Über die **vorhandene** Entprellung: `_schedule_files` → `_files_timer` (100 ms) → `_load_pending_files`. Kein zweiter Timer, keine zweite Sichtbarkeitsprüfung. |
| Was steht im Panel? | **Genau die Commit-Message**, nichts sonst. Autor, Datum und OID stehen bereits in den Spalten der Liste; und wenn der angezeigte Text exakt `%B` ist, stimmen die Offsets der Markierungen ohne Umrechnung. |
| Wie wird es lesbar? | Schreibgeschütztes `text.MonoTextEdit` mit **eingeschaltetem Zeilenumbruch** (Falle **F1**), erste Zeile (Betreff) fett. |
| Was heißt „fuzzy"? | Ein Pfad wird an **jedem seiner Suffixe an `/`-Grenzen** erkannt: `cola/widgets/dag.py` auch als `widgets/dag.py` und als `dag.py`. Groß-/Kleinschreibung egal. Kein Levenshtein — siehe §2. |
| Mehrere Commits ausgewählt? | Die Beschreibung zeigt den **jüngsten** (`selection[-1]`), wie `CommitFileDiffWindow.set_commit_file`. Siehe auch Falle **F8**. |
| `WORKTREE`/`STAGE` ausgewählt? | Kein Commit, keine Message — das Panel wird geleert. |
| Ein- und Ausblenden? | Die **vorhandene** Aktion schaltet ab jetzt das ganze rechte Panel. Ihr Label wird zu `Display Commit Details`; der Zustandsschlüssel `display_files` bleibt unverändert, damit gespeicherte Layouts weiter passen. |
| Wo lebt der Code? | Alles in `cola/widgets/dag.py`. Grund: die Markierungsfarben kommen aus `inline_graph_style()` (`cola/widgets/dag.py:975`), und `cola/widgets/filelist.py` kann das nicht importieren — `dag.py` importiert `filelist` bereits (Zeile 40), die Gegenrichtung wäre ein Zyklus. |

## 2. Nicht-Ziele

- **Kein Levenshtein-/Score-Fuzzy-Matching.** „Fuzzy" heißt hier: der Pfad muss nicht vollständig
  dastehen. Eine Ähnlichkeitsschwelle wäre nicht sinnvoll testbar und produziert in Prosa
  Fehltreffer („main" in „main branch"). Deshalb **keine Übereinstimmung auf dem Dateinamen ohne
  Endung**: `main.py` wird nicht durch das Wort „main" ausgelöst.
- **Kein anklickbarer Link.** Die Markierung ist eine Lesehilfe, kein Navigationselement. Wer die
  Datei öffnen will, doppelklickt sie unten in der Liste — das gibt es seit
  `2026-07-31-commit-file-diff-window.md`.
- **Keine eigene Menü-Aktion für die Beschreibung.** Wer sie nicht sehen will, zieht den
  Splitter zu; deshalb ist `details_splitter` bewusst **collapsible** (Standard von
  `qtutils.splitter`), während `files_splitter` es nicht ist.
- **Kein Autor/Datum/OID-Kopf.** Siehe §1.
- **Kein `widget_version`-Bump.** Ein Splitter innerhalb eines Docks ist nicht Teil von
  `QMainWindow.saveState()`.
- **Keine Änderung an `FileWidget.commits_selected`.** Insbesondere wird der Fehler aus Falle
  **F8** in diesem Plan **nicht** behoben.
- **Keine Änderung an `cola/widgets/main.py`.** `MainView` benutzt `CommitHistoryWidget` als
  Ganzes und merkt von der Teilung nichts.

## 3. Fallen — alle empirisch verifiziert

| # | Falle | Beleg |
|---|---|---|
| **F1** | **`MonoTextEdit` startet ohne Zeilenumbruch.** `BaseTextEditExtension` setzt `NoWrap` (`cola/widgets/text.py:102`); der konstruierte Wert `line_wrap_mode` wird erst von `set_word_wrapping(True)` angewandt (`cola/widgets/text.py:337-344`). Ohne diesen Aufruf bekommt die Beschreibung eine waagerechte Bildlaufleiste — genau das Gegenteil von „gut lesbar". | Gemessen: direkt nach dem Konstruieren `lineWrapMode() == 0` (NoWrap), nach `set_word_wrapping(True)` `== 1` (WidgetWidth) |
| **F2** | **Ein verstecktes Eltern-Splitter versteckt die Kinder mit.** Deshalb funktionieren die vorhandenen Wächter `if not self.filewidget.isVisible()` in `_schedule_files` und `_load_pending_files` **unverändert** weiter, obwohl ab jetzt `details_splitter` versteckt wird und nicht mehr `filewidget`. | Gemessen an genau dieser Verschachtelung: sichtbar → `child.isVisible() == True`; `inner.setVisible(False)` → `child.isVisible() == False`; wieder sichtbar → `True` |
| **F3** | **Der Git-Wrapper schneidet abschließende Zeilenumbrüche ab** (`cola/git.py:327`: `out.rstrip('\n')`). Der Text im Panel endet deshalb ohne Leerzeile — Testerwartungen müssen das so schreiben. | Gemessen: `subprocess` liefert `'…here.\n\n'`, `context.git.show(oid, no_patch=True, format='%B')` liefert `'…here.'` |
| **F4** | **`HISTORY_KEYS` ist ein exakter Mengenvergleich.** `test/widgets_main_history_test.py:34` listet die Schlüssel, `:992` prüft `set(state['history']) == HISTORY_KEYS`. Ein neuer Zustandsschlüssel macht diesen Test rot, wenn er nicht mitgepflegt wird. | `test/widgets_main_history_test.py:34-41`, `:992` |
| **F5** | **`assert history.files_splitter.indexOf(history.filewidget) == 1`** (`test/widgets_main_history_test.py:1485`) wird nach der Teilung **−1**, weil die Dateiliste eine Ebene tiefer sitzt. Der Test heißt `test_main_history_file_panel_lives_inside_the_history_dock` und hält eine Architekturaussage fest („kein eigener Dock") — er wird **angepasst, nicht gelöscht**. | `test/widgets_main_history_test.py:1478-1487` |
| **F6** | **`self.filewidget = filelist.FileWidget(context, self)` steht zweimal in `dag.py`** — einmal in `CommitHistoryWidget` (Zeile 1801), einmal in `GitDAG` (Zeile 2274). Als Anker unbrauchbar. Dieser Plan verankert stattdessen auf `self.files_splitter = qtutils.splitter(`. | `grep -c "self.filewidget = filelist.FileWidget(context, self)" cola/widgets/dag.py` → `2` |
| **F7** | **Formate eines `QSyntaxHighlighter` sind über `QTextCursor.charFormat()` nicht sichtbar.** Sie liegen als *additional formats* im Layout. Tests lesen sie über `block.layout().formats()`. | Gemessen: nach dem Highlighten liefert `doc.findBlockByNumber(2).layout().formats()` `[(14, 6, 75, '#f7f7f7')]` — Start, Länge, Schriftgewicht, Hintergrund |
| **F8** | **Eine Mehrfachauswahl bricht heute schon.** `FileWidget.commits_selected` liest `oid` unbedingt (`cola/widgets/filelist.py:159`), weist es aber nur im Einzel-Commit-Zweig zu (Zeile 130). Bei einer gültigen Spanne fliegt `UnboundLocalError`. **Das wird separat behoben, nicht hier.** Alle Integrationstests dieses Plans wählen deshalb **einen** Commit aus. | Gemessen an einem Repo mit drei Commits, Auswahl der jüngsten zwei: `UnboundLocalError: cannot access local variable 'oid' where it is not associated with a value`. **Vor Task 4 nachprüfen** (Befehl in Task 4) — ist der Fehler inzwischen weg, ist diese Falle erledigt und der Hinweis in Task 4 gegenstandslos. |
| **F9** | **`is_valid_state` kehrt früh zurück.** `if log_state is None: return True` steht am Ende; jede neue Prüfung muss **darüber** stehen, sonst läuft sie für genau die Altzustände nicht, für die sie gedacht ist. Für `files_sizes` ist das bereits richtig gelöst — die neue Prüfung kommt direkt daneben. | `cola/widgets/dag.py:2151-2189` |
| **F10** | **`app_context.settings` ist ein roher `Mock`, und ein `Mock` ist truthy.** Jedes Widget mit `init_state(context.settings, …)` stirbt beim Konstruieren mit `TypeError` in `QByteArray.fromBase64()`. Betrifft `MainView` und `GitDAG`, nicht `CommitHistoryWidget`. Erst `app_context.settings.get_gui_state.return_value = {}` setzen. | Konvention in `test/widgets_dag_history_test.py:293` ff. und in der `main_context`-Fixture (`test/widgets_main_history_test.py:114`) |
| **F11** | **`context.timestamp` muss eine Zahl sein**, sobald ein Test ein `cmds`-Kommando auslöst (`cola/cmd.py:64` vergleicht numerisch). `main_context` setzt es; ein roher `app_context` nicht. Dieser Plan löst keine Kommandos aus — die Falle steht hier nur, damit sie beim Debuggen nicht neu gefunden werden muss. | `test/widgets_main_history_test.py:120` |
| **F13** | **Ein nie gezeigter `QSplitter` behaelt gesetzte Groessen nicht.** Er verteilt sie nach eigenen Hinweisen neu. Ein Test darf deshalb nie auf feste Pixelwerte pruefen, sondern spioniert `setSizes` aus — Instanz-Methoden lassen sich auf Qt-Objekten ueberschreiben. Genau deshalb gibt es auch fuer `files_sizes` keinen solchen Test. | Gemessen an einem frisch gebauten `CommitHistoryWidget`: `details_splitter.setSizes([120, 240])` gefolgt von `sizes()` liefert `[159, 317]` |
| **F12** | **`cola/widgets/filelist.py` darf `cola/widgets/dag.py` nicht importieren.** `dag.py:40` hat bereits `from . import filelist`; die Gegenrichtung auf Modulebene wäre ein Zyklus. Deshalb liegt der neue Code in `dag.py` und nicht neben `parse_status_and_numstat`. | `grep -n "^from \. import filelist$" cola/widgets/dag.py` |

## 4. Vorhandenes, das wiederverwendet wird (nicht neu bauen)

| Vorhanden | Wo | Rolle in diesem Plan |
|---|---|---|
| `text.MonoTextEdit` | `cola/widgets/text.py:651` | **Ist** die Basis des Beschreibungsfelds: `PlainTextEdit` + `qtutils.diff_font(context)`, mit `readonly=True` im Konstruktor. Es entsteht **keine neue Widget-Gattung**. |
| `PlainTextEdit.set_word_wrapping(enabled)` | `cola/widgets/text.py:337` | Schaltet den Umlauf ein. Siehe Falle **F1**. |
| `LogSyntaxHighlighter` | `cola/widgets/log.py:84-96` | **Vorbild** für den Highlighter: `__init__(self, doc)`, `highlightBlock(self, block_text)`, `self.setFormat(start, length, fmt)`. Genau diese Form übernehmen. |
| `inline_graph_style(palette)` | `cola/widgets/dag.py:975` | **Ist** die Farbableitung. `chip_other` als Hintergrund und `chip_text` als Schrift geben der Dateimarkierung dieselbe Optik wie die Branch-Chips daneben — und dieselbe garantierte Lesbarkeit. Palettenbasiert und ohne Cache, also ohne Theme-Sonderbehandlung. |
| `qtutils.splitter(orientation, *widgets)` | `cola/qtutils.py:211` | **Ist** der Splitter. Setzt Handle-Breite und Stretch-Faktoren bereits. |
| `_schedule_files` / `_load_pending_files` / `refresh_files` | `cola/widgets/dag.py:2100`, `:2111`, `:2121` | **Ist** die Entprellung samt Sichtbarkeitswächter. Der Beschreibungstext hängt sich dort ein — **kein zweiter Timer**. |
| `FileWidget.selected_paths()` | `cola/widgets/filelist.py:235` | Vorlage für `all_paths()`: eine Zeile, gleiche Form. |
| `TreeWidget.items()` | `cola/widgets/standard.py:660` | Liefert die Top-Level-Items. `all_paths()` braucht nichts anderes. |
| `git.show(oid, no_patch=True, format='%B', _readonly=True)` | `cola/git.py` (kwargs → Flags) | **Ist** der Abruf. `no_patch=True` → `--no-patch`, `format='%B'` → `--format=%B`. Verifiziert: Status 0, Message ohne abschließende Leerzeilen. |
| `test/widgets_history_filelist_test.py` | ganze Datei | **Vorlage** für die `FileWidget`-Tests in Task 2 (Fixtures `qapp`, `managed_qobject`, Helfer `_fake_commit`). |
| `_wait_for_commit_files`, `_wait_for_history`, `_show`, `_git` | `test/widgets_main_history_test.py` | **Fertige** Warte- und Aufbauhelfer für Task 6. Nicht neu schreiben. |

---

# TASKS

## Task 0 — Testlauf sicherstellen

> **Blockierend. Kein Commit.** Ziel ist eine einzige Feststellung: **welcher Testbefehl läuft
> hier?** Jeder folgende Task hängt an einer beobachteten RED- und GREEN-Ausgabe.

```bash
python3 -m pytest --version 2>&1 | head -1
ls -d env3 2>/dev/null && env3/bin/python -m pytest --version 2>&1 | head -1
command -v garden cercis isort
python3 -c "import qtpy; print('qtpy', qtpy.API_NAME)"
```

Notiere den Interpreter für alle `pytest`-Aufrufe und ob `garden` existiert. Läuft **keiner** der
beiden Interpreter, einen der beiden Wege versuchen:

```bash
garden dev/virtualenv && garden dev
```

```bash
python3 -m venv --system-site-packages env3 && env3/bin/python -m ensurepip --upgrade && env3/bin/pip install -e '.[docs,dev,testing,extras]'
```

Scheitert auch das: **STOPP und melden.**

### Verifikation

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -5
```

**Erwartet:** `NNN passed`, kein `failed`, kein `error`. **Notiere `NNN` als Baseline.**

---

## Task 1 — Welche Dateinamen stehen im Text?

**Ziel:** Eine reine Funktion ohne Qt: `commit_message_file_spans(text, paths)` liefert die
Stellen, an denen geänderte Dateien im Text vorkommen.

> **Diese Funktion ist der Kern des Features.** Sie ist absichtlich ohne Qt und ohne Git
> geschrieben, damit sie vollständig durch Tabellentests festgelegt werden kann.

### Schritt 1.1 (RED) — Tests schreiben

Hänge an `test/widgets_dag_history_test.py` an:

```python
_SPAN_PATHS = ['cola/widgets/dag.py', 'cola/widgets/filelist.py', 'test/helper.py']


@pytest.mark.parametrize(
    ('scenario', 'text', 'expected'),
    (
        ('voller Pfad', 'touch cola/widgets/dag.py now', ['cola/widgets/dag.py']),
        ('nur Dateiname', 'refactor dag.py a bit', ['dag.py']),
        ('mittleres Suffix', 'see widgets/filelist.py', ['widgets/filelist.py']),
        ('Satzende', 'all in dag.py.', ['dag.py']),
        (
            'laengster Treffer gewinnt',
            'in cola/widgets/dag.py',
            ['cola/widgets/dag.py'],
        ),
        ('kein Praefix-Teiltreffer', 'mydag.py untouched', []),
        ('kein Suffix-Teiltreffer', 'dag.pyc is generated', []),
        ('falsches Elternverzeichnis', 'src/dag.py elsewhere', []),
        ('Gross-/Kleinschreibung', 'DAG.PY shouted', ['DAG.PY']),
        ('zwei Erwaehnungen', 'dag.py and dag.py', ['dag.py', 'dag.py']),
        ('nichts dabei', 'nothing here', []),
        ('leerer Text', '', []),
        (
            'mehrzeilig',
            'fix stuff\n\n- cola/widgets/dag.py\n- test/helper.py\n',
            ['cola/widgets/dag.py', 'test/helper.py'],
        ),
    ),
)
def test_commit_message_file_spans_finds_mentioned_paths(scenario, text, expected):
    """Der markierte Ausschnitt ist genau der Text, der die Datei benennt."""
    spans = commit_message_file_spans(text, _SPAN_PATHS)

    assert [text[start:end] for start, end, _path in spans] == expected, scenario


def test_commit_message_file_spans_reports_the_changed_path():
    """Zurueckgemeldet wird der echte Pfad, nicht der gefundene Ausschnitt."""
    spans = commit_message_file_spans('see dag.py', _SPAN_PATHS)

    assert [path for _start, _end, path in spans] == ['cola/widgets/dag.py']


@pytest.mark.parametrize('paths', ([], [''], ['/']))
def test_commit_message_file_spans_without_usable_paths(paths):
    """Ohne brauchbare Pfade wird nichts markiert - und nichts geworfen."""
    assert commit_message_file_spans('dag.py', paths) == []


def test_commit_message_file_spans_are_sorted_and_disjoint():
    """Die Bereiche kommen sortiert und ueberschneidungsfrei - der Highlighter
    setzt sie in dieser Reihenfolge und darf sich nicht selbst ueberschreiben."""
    text = 'cola/widgets/dag.py, dann test/helper.py, dann nochmal dag.py'

    spans = commit_message_file_spans(text, _SPAN_PATHS)

    assert len(spans) == 3
    assert spans == sorted(spans)
    assert all(
        spans[index][1] <= spans[index + 1][0] for index in range(len(spans) - 1)
    )


def test_commit_message_file_spans_are_deterministic_for_equal_length_needles():
    """Gleich lange Kandidaten duerfen die Reihenfolge nicht dem Zufall ueberlassen."""
    first = commit_message_file_spans('a/b.py and c/b.py', ['x/a/b.py', 'y/c/b.py'])
    second = commit_message_file_spans('a/b.py and c/b.py', ['y/c/b.py', 'x/a/b.py'])

    assert first == second
    assert [path for _start, _end, path in first] == ['x/a/b.py', 'y/c/b.py']
```

Ergänze den Import. `test/widgets_dag_history_test.py` importiert bereits einzeln aus
`cola.widgets.dag`; füge **eine Zeile** alphabetisch in dieser Gruppe ein:

```python
from cola.widgets.dag import commit_message_file_spans
```

Anker für die Import-Gruppe:

```bash
grep -n "^from cola.widgets.dag import" test/widgets_dag_history_test.py
```

**RED ausführen:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -8
```

**Erwartete Fehlermeldung — die ganze Datei scheitert beim Einsammeln:**

```
ImportError: cannot import name 'commit_message_file_spans' from 'cola.widgets.dag'
```

> Das ist ein **Collection-Error**, kein einzelner Testfehler. Hier ist das richtig und
> beabsichtigt: die Funktion existiert noch nicht.

### Schritt 1.2 (GREEN) — Funktion anlegen

**Anker:**

```bash
grep -n "^def _prepare_labels" cola/widgets/dag.py
```

Füge **direkt vor** `def _prepare_labels(` ein:

```python
def _is_token_char(text: str, index: int) -> bool:
    """Would the character at `index` make a match a partial one?

    '.' is deliberately absent: it ends sentences ("… in dag.py.") and it is
    already part of the needle when it separates a name from its extension.
    """
    if index < 0 or index >= len(text):
        return False
    char = text[index]
    return char.isalnum() or char in '_-/'


def commit_message_file_spans(text, paths):
    """Return sorted, non-overlapping (start, end, path) spans for mentioned files.

    A path is recognised by any of its suffixes that begin at a directory
    boundary, so 'cola/widgets/dag.py' is also found as 'widgets/dag.py' and as
    'dag.py'. Matching ignores case and never cuts into a surrounding token, so
    'dag.py' is not found inside 'mydag.py' or 'dag.pyc'. The longest candidate
    wins, which keeps a full path from being reported as its own basename.
    """
    if not text or not paths:
        return []
    needles = {}
    for path in paths:
        segments = [segment for segment in path.split('/') if segment]
        for index in range(len(segments)):
            needle = '/'.join(segments[index:]).lower()
            if needle:
                needles.setdefault(needle, path)
    haystack = text.lower()
    spans = []
    # Longest first so that a full path claims its range before its basename
    # can; ties break on the needle itself to keep the result reproducible.
    for needle in sorted(needles, key=lambda item: (-len(item), item)):
        start = haystack.find(needle)
        while start != -1:
            end = start + len(needle)
            overlaps = any(
                start < taken_end and taken_start < end
                for taken_start, taken_end, _taken_path in spans
            )
            if (
                not overlaps
                and not _is_token_char(haystack, start - 1)
                and not _is_token_char(haystack, end)
            ):
                spans.append((start, end, needles[needle]))
            start = haystack.find(needle, start + 1)
    spans.sort()
    return spans


```

### Verifikation

```bash
garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -3
```

**Erwartet:** alle passed.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 19 passed, 0 failed — 13 Parameter des Tabellentests, 3 Parameter
von `..._without_usable_paths` und 3 Einzeltests.

### Commit

```bash
git add -A && git commit -m "feat: find file paths mentioned in a commit message

commit_message_file_spans() recognises a path by any of its suffixes that
begin at a directory boundary, ignoring case and never cutting into a
surrounding token. The longest candidate wins."
```

---

## Task 2 — Die Dateiliste verrät ihre Pfade

**Ziel:** Der Highlighter braucht die Pfade des Commits. Die hat die Dateiliste bereits
ausgerechnet — sie muss sie nur herausgeben.

> **Zeitgleich läuft eine separate Korrektur an `cola/widgets/filelist.py`** (der Fehler aus Falle
> **F8**), die dieselbe Testdatei erweitert. Prüfe vor diesem Task, ob der Arbeitsbaum sauber ist:
>
> ```bash
> git status --short cola/widgets/filelist.py test/widgets_history_filelist_test.py
> ```
>
> Sind dort Änderungen, die nicht von dir stammen: **stoppen und melden**, statt darüber zu
> schreiben.

### Schritt 2.1 (RED) — Test schreiben

Hänge an `test/widgets_history_filelist_test.py` an:

```python
def test_all_paths_reports_every_listed_file(qapp, app_context, managed_qobject):
    """Die Beschreibung braucht alle Pfade, nicht nur die markierten."""
    widget = managed_qobject(FileWidget(app_context, None))

    widget.list_files(['3\t1\tsrc/a.py', '0\t2\tsrc/b.py'])

    assert widget.all_paths() == ['src/a.py', 'src/b.py']


def test_all_paths_is_empty_without_files(qapp, app_context, managed_qobject):
    widget = managed_qobject(FileWidget(app_context, None))

    assert widget.all_paths() == []
```

**RED ausführen:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py -k all_paths 2>&1 | tail -8
```

**Erwartete Fehlermeldung — beide Tests:**

```
AttributeError: 'FileWidget' object has no attribute 'all_paths'
```

### Schritt 2.2 (GREEN) — Methode anlegen

**Anker:**

```bash
grep -n "    def selected_paths" -A 2 cola/widgets/filelist.py
```

Füge **direkt vor** `def selected_paths(self):` ein:

```python
    def all_paths(self):
        """Every listed path, in display order"""
        return [item.path for item in self.items()]

```

### Verifikation

```bash
garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_history_filelist_test.py 2>&1 | tail -3
```

**Erwartet:** alle passed.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 21 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "feat: let FileWidget report every listed path

all_paths() complements selected_paths(). The commit description marks the
files of the commit, not the ones that happen to be selected."
```

---

## Task 3 — Das Beschreibungsfeld

**Ziel:** Ein schreibgeschütztes Textfeld, das die Message eines Commits zeigt, den Betreff fett
setzt und die erwähnten Dateien hervorhebt.

### Schritt 3.1 (RED) — Tests schreiben

Hänge an `test/widgets_dag_history_test.py` an:

```python
def _description(app_context, managed_qobject):
    return managed_qobject(CommitDescriptionWidget(app_context, None))


def _formats(widget, block_number):
    """Die Formate eines Blocks.

    Ein QSyntaxHighlighter legt seine Formate als *additional formats* im Layout
    ab; ueber QTextCursor.charFormat() sind sie nicht sichtbar (Falle F7).
    """
    block = widget.document().findBlockByNumber(block_number)
    return [(rng.start, rng.length, rng.format) for rng in block.layout().formats()]


def _message_commit(app_context, oid, message):
    """Ein Commit-Stellvertreter, dessen Message ueber git.show geliefert wird."""
    commit = dag.Commit(None, dag.CommitFactory(), oid=oid)
    commit.summary = message.splitlines()[0]
    commit.author = 'A U Thor'
    commit.authdate = '2026-08-01'
    app_context.git.show = lambda *args, **kwargs: (0, message, '')
    return commit


def test_description_shows_the_commit_message(qapp, app_context, managed_qobject):
    """Angezeigt wird genau die Message - kein Kopf, keine Zusaetze."""
    widget = _description(app_context, managed_qobject)
    commit = _message_commit(app_context, 'a' * 40, 'subject line\n\nbody text')

    widget.set_commit(commit, [])

    assert widget.toPlainText() == 'subject line\n\nbody text'


def test_description_wraps_long_lines(qapp, app_context, managed_qobject):
    """Ohne Umbruch braeuchte man eine waagerechte Bildlaufleiste (Falle F1)."""
    widget = _description(app_context, managed_qobject)

    assert widget.lineWrapMode() == QtWidgets.QPlainTextEdit.WidgetWidth


def test_description_is_read_only(qapp, app_context, managed_qobject):
    widget = _description(app_context, managed_qobject)

    assert widget.isReadOnly()


def test_description_asks_git_for_the_message_body(
    qapp, app_context, managed_qobject
):
    """Genau ein "git show" ohne Patch, im Format %B."""
    widget = _description(app_context, managed_qobject)
    calls = []

    def record(*args, **kwargs):
        calls.append((args, kwargs))
        return (0, 'subject', '')

    app_context.git.show = record
    commit = dag.Commit(None, dag.CommitFactory(), oid='b' * 40)

    widget.set_commit(commit, [])

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == ('b' * 40,)
    assert kwargs['no_patch'] is True
    assert kwargs['format'] == '%B'


def test_description_marks_the_subject_line(qapp, app_context, managed_qobject):
    """Die erste Zeile wird fett - sie ist die Ueberschrift des Commits."""
    widget = _description(app_context, managed_qobject)
    commit = _message_commit(app_context, 'a' * 40, 'subject line\n\nbody text')

    widget.set_commit(commit, [])

    subject = _formats(widget, 0)
    assert [(start, length) for start, length, _fmt in subject] == [(0, 12)]
    assert subject[0][2].fontWeight() == QtGui.QFont.Bold


def test_description_marks_mentioned_files(qapp, app_context, managed_qobject):
    """Erwaehnte Dateien bekommen die Chip-Farben des Inline-Graphen."""
    widget = _description(app_context, managed_qobject)
    commit = _message_commit(
        app_context, 'a' * 40, 'subject\n\nsee cola/widgets/dag.py for details'
    )
    style = inline_graph_style(widget.palette())

    widget.set_commit(commit, ['cola/widgets/dag.py'])

    body = _formats(widget, 2)
    assert [(start, length) for start, length, _fmt in body] == [(4, 19)]
    assert body[0][2].background().color() == style.chip_other
    assert body[0][2].foreground().color() == style.chip_text


def test_description_leaves_unmentioned_files_alone(
    qapp, app_context, managed_qobject
):
    widget = _description(app_context, managed_qobject)
    commit = _message_commit(app_context, 'a' * 40, 'subject\n\nnothing to see')

    widget.set_commit(commit, ['cola/widgets/dag.py'])

    assert _formats(widget, 2) == []


@pytest.mark.parametrize('oid', (dag.STAGE, dag.WORKTREE))
def test_description_is_empty_for_pseudo_commits(
    qapp, app_context, managed_qobject, oid
):
    """WORKTREE und STAGE haben keine Message - und duerfen kein git aufrufen."""
    widget = _description(app_context, managed_qobject)
    calls = []
    app_context.git.show = lambda *args, **kwargs: calls.append(args) or (0, '', '')
    commit = dag.Commit(None, dag.CommitFactory(), oid=oid)

    widget.set_commit(commit, [])

    assert widget.toPlainText() == ''
    assert calls == []


def test_description_clears_without_a_commit(qapp, app_context, managed_qobject):
    widget = _description(app_context, managed_qobject)
    commit = _message_commit(app_context, 'a' * 40, 'subject\n\nbody')
    widget.set_commit(commit, [])

    widget.set_commit(None, [])

    assert widget.toPlainText() == ''


def test_description_survives_a_failed_git_call(qapp, app_context, managed_qobject):
    """Ein fehlgeschlagenes git show leert das Feld, statt Muell anzuzeigen."""
    widget = _description(app_context, managed_qobject)
    app_context.git.show = lambda *args, **kwargs: (128, '', 'boom')
    commit = dag.Commit(None, dag.CommitFactory(), oid='c' * 40)

    widget.set_commit(commit, [])

    assert widget.toPlainText() == ''
```

Ergänze den Import, eine Zeile, alphabetisch in derselben Gruppe wie in Task 1:

```python
from cola.widgets.dag import CommitDescriptionWidget
```

> **`app_context.git` ist ein echtes `Git`-Objekt, aber `git.show` lässt sich überschreiben:**
> `Git.__getattr__` legt den erzeugten Aufruf per `setattr` auf der Instanz ab
> (`cola/git.py:255-258`), eine Zuweisung ist also möglich und wirkt.
>
> **`CommitDescriptionWidget` braucht ein echtes `context.cfg`.** `MonoTextEdit` ruft
> `qtutils.diff_font(context)` → `prefs.diff_font(context)` → `context.cfg.get(...)`. Die
> `app_context`-Fixture liefert ein echtes `GitConfig`; ein handgebauter Stub ohne `cfg` stirbt
> beim Konstruieren mit `AttributeError`. Deshalb bauen diese Tests das Widget über
> `app_context` und nicht über einen eigenen Mock.
>
> **Wird eine Datei im Betreff genannt, überschreibt das Datei-Format dort das Betreff-Format.**
> Deshalb setzt das Datei-Format ebenfalls `Bold` — sonst würde der Dateiname als einziges Stück
> der Überschrift wieder mager. Verifiziert.

**RED ausführen:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -8
```

**Erwartete Fehlermeldung:**

```
ImportError: cannot import name 'CommitDescriptionWidget' from 'cola.widgets.dag'
```

### Schritt 3.2 (GREEN) — Import ergänzen

**Anker:**

```bash
grep -n "^from \. import standard$" cola/widgets/dag.py
```

Füge **direkt darunter** ein (isort sortiert `standard` vor `text`):

```python
from . import text
```

### Schritt 3.3 (GREEN) — Highlighter und Widget

**Anker:**

```bash
grep -n "^class CommitHistoryWidget" cola/widgets/dag.py
```

Füge **direkt vor** `class CommitHistoryWidget(QtWidgets.QWidget):` ein:

```python
class CommitMessageHighlighter(QtGui.QSyntaxHighlighter):
    """Bold the subject line and mark the files the message talks about"""

    def __init__(self, edit):
        QtGui.QSyntaxHighlighter.__init__(self, edit.document())
        self._edit = edit
        self.spans = []

    def set_spans(self, spans):
        """Replace the marked ranges and repaint"""
        self.spans = list(spans)
        self.rehighlight()

    def highlightBlock(self, block_text):
        block = self.currentBlock()
        if block.blockNumber() == 0 and block_text:
            subject_format = QtGui.QTextCharFormat()
            subject_format.setFontWeight(QtGui.QFont.Bold)
            self.setFormat(0, len(block_text), subject_format)
        if not self.spans:
            return
        # The palette is read on every pass instead of being cached, so a theme
        # change repaints correctly - the same rule the inline graph follows.
        style = inline_graph_style(self._edit.palette())
        file_format = QtGui.QTextCharFormat()
        file_format.setBackground(style.chip_other)
        file_format.setForeground(style.chip_text)
        file_format.setFontWeight(QtGui.QFont.Bold)
        start = block.position()
        end = start + block.length()
        for span_start, span_end, _path in self.spans:
            if span_start >= end or span_end <= start:
                continue
            self.setFormat(
                max(span_start, start) - start,
                min(span_end, end) - max(span_start, start),
                file_format,
            )


class CommitDescriptionWidget(text.MonoTextEdit):
    """Show the message of the selected commit, with its files marked"""

    def __init__(self, context, parent=None):
        text.MonoTextEdit.__init__(self, context, parent=parent, readonly=True)
        self.context = context
        # MonoTextEdit starts out with NoWrap; a commit message needs to wrap.
        self.set_word_wrapping(True)
        self.highlighter = CommitMessageHighlighter(self)

    def clear(self):
        """Drop the text and the marked ranges together"""
        self.highlighter.set_spans([])
        self.setPlainText('')

    def set_commit(self, commit, paths=()):
        """Show `commit`'s message and mark `paths` wherever it names them"""
        if commit is None or commit.oid in (dag.STAGE, dag.WORKTREE):
            self.clear()
            return
        status, message, _err = self.context.git.show(
            commit.oid, no_patch=True, format='%B', _readonly=True
        )
        if status != 0:
            self.clear()
            return
        # Spans are computed before the text is set so that the first
        # highlighting pass already has them.
        self.highlighter.spans = commit_message_file_spans(message, list(paths))
        self.setPlainText(message)
        self.highlighter.rehighlight()


```

### Verifikation

```bash
garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py 2>&1 | tail -3
```

**Erwartet:** alle passed.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 32 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "feat: add a description panel for the selected commit

CommitDescriptionWidget is a read-only MonoTextEdit with word wrapping turned
on. The subject line is bold and mentioned files get the inline graph's chip
colors - the same look as the branch labels beside them, and the same
guaranteed contrast."
```

---

## Task 4 — Das Panel wird geteilt

**Ziel:** Die Beschreibung sitzt über der Dateiliste, beide zusammen rechts neben der
Commit-Tabelle.

> **Vorher Falle F8 nachprüfen:**
>
> ```bash
> grep -n "        if oid in (dag.STAGE, dag.WORKTREE):" -B 3 cola/widgets/filelist.py
> ```
>
> Steht dort weiterhin ein unbedingter Zugriff auf `oid`, gilt: **Mehrfachauswahl bricht heute
> schon**, und alle Tests dieses Plans wählen genau einen Commit. Ist die Stelle inzwischen
> repariert, ändert das an diesem Plan nichts — die Beschreibung zeigt so oder so `selection[-1]`.

### Schritt 4.1 (RED) — Tests schreiben

Hänge an `test/widgets_dag_history_test.py` an:

```python
def test_history_stacks_description_over_the_file_list(
    qapp, app_context, managed_qobject
):
    """Rechts neben der Tabelle steht oben die Beschreibung, unten die Dateien."""
    history = managed_qobject(CommitHistoryWidget(app_context))

    assert history.files_splitter.indexOf(history.details_splitter) == 1
    assert history.details_splitter.orientation() == QtCore.Qt.Vertical
    assert history.details_splitter.indexOf(history.descriptionwidget) == 0
    assert history.details_splitter.indexOf(history.filewidget) == 1


def test_history_hides_and_shows_both_halves_together(
    qapp, app_context, managed_qobject
):
    """Die vorhandene Aktion schaltet das ganze rechte Panel."""
    history = managed_qobject(CommitHistoryWidget(app_context, display_files=True))

    history.display_files(False)
    assert not history.details_splitter.isVisible()

    history.display_files(True)
    assert history.details_splitter.isVisibleTo(history)


def test_history_clear_empties_the_description(qapp, app_context, managed_qobject):
    history = managed_qobject(CommitHistoryWidget(app_context))
    history.descriptionwidget.setPlainText('leftover')

    history.clear()

    assert history.descriptionwidget.toPlainText() == ''


def test_history_feeds_description_with_commit_and_paths(
    qapp, app_context, managed_qobject, monkeypatch
):
    """Die Beschreibung bekommt den juengsten Commit und die Pfade der Dateiliste."""
    history = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    received = []
    monkeypatch.setattr(
        history.descriptionwidget,
        'set_commit',
        lambda commit, paths: received.append((commit, list(paths))),
    )
    monkeypatch.setattr(history.filewidget, 'commits_selected', lambda commits: None)
    monkeypatch.setattr(history.filewidget, 'all_paths', lambda: ['src/a.py'])
    # Der Waechter in _load_pending_files fragt die Dateiliste, nicht den Splitter.
    monkeypatch.setattr(history.filewidget, 'isVisible', lambda: True)
    factory = dag.CommitFactory()
    older = _commit(app_context, factory, 'older')
    newer = _commit(app_context, factory, 'newer', (older,))
    history.selection = [older, newer]

    history._load_pending_files()

    assert received == [(newer, ['src/a.py'])]


def test_history_description_stays_empty_without_selection(
    qapp, app_context, managed_qobject, monkeypatch
):
    history = managed_qobject(CommitHistoryWidget(app_context, display_files=True))
    received = []
    monkeypatch.setattr(
        history.descriptionwidget,
        'set_commit',
        lambda commit, paths: received.append(commit),
    )
    history.selection = []

    history._load_pending_files()

    assert received == []
```

> **Warum `isVisibleTo(history)` und nicht `isVisible()`?** Ein nie gezeigtes Widget meldet
> immer `isVisible() == False`, unabhängig von der eigenen Einstellung. `isVisibleTo(parent)`
> beantwortet die Frage, die hier zählt: „wäre es sichtbar, wenn der Elternteil es wäre".
> Für den Ausblend-Fall reicht `isVisible()`, weil `False` dort die Aussage ist.

**RED ausführen:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k "stacks_description or both_halves or clear_empties or feeds_description or stays_empty" 2>&1 | tail -10
```

**Erwartete Fehlermeldungen — alle fünf scheitern, mit zwei Ursachen.** Welches Attribut zuerst
fehlt, hängt davon ab, was der Test zuerst anfasst:

```
AttributeError: 'CommitHistoryWidget' object has no attribute 'details_splitter'
AttributeError: 'CommitHistoryWidget' object has no attribute 'descriptionwidget'
```

Die ersten beiden Tests (`..._stacks_description_over_the_file_list`,
`..._hides_and_shows_both_halves_together`) melden `details_splitter`, die übrigen drei
`descriptionwidget`. Ist einer der fünf grün, **stoppen und melden**.

### Schritt 4.2 (GREEN) — Aufbau

**Anker 1 — Widget und Splitter.**

> **Achtung, `self.filewidget = filelist.FileWidget(context, self)` steht zweimal in der Datei**
> (Falle **F6**). Der folgende `grep` trifft nur die Stelle in `CommitHistoryWidget`:

```bash
grep -n "        self.files_splitter = qtutils.splitter(" -B 4 -A 6 cola/widgets/dag.py
```

**Erwartet:** genau **ein** Treffer. Ersetze den ausgegebenen Block

```python
        self.filewidget = filelist.FileWidget(context, self)
        self.filewidget.setVisible(display_files)
        self.files_splitter = qtutils.splitter(
            Qt.Horizontal, self.treewidget, self.filewidget
        )
        self.files_splitter.setChildrenCollapsible(False)
        self.files_splitter.setStretchFactor(0, 3)
        self.files_splitter.setStretchFactor(1, 1)
```

durch

```python
        self.filewidget = filelist.FileWidget(context, self)
        self.descriptionwidget = CommitDescriptionWidget(context, self)
        # Beide Haelften sind einklappbar: wer nur die Dateien sehen will, zieht
        # den Griff hoch. Dafuer braucht es keine zweite Menue-Aktion.
        self.details_splitter = qtutils.splitter(
            Qt.Vertical, self.descriptionwidget, self.filewidget
        )
        self.details_splitter.setVisible(display_files)
        self.files_splitter = qtutils.splitter(
            Qt.Horizontal, self.treewidget, self.details_splitter
        )
        self.files_splitter.setChildrenCollapsible(False)
        self.files_splitter.setStretchFactor(0, 3)
        self.files_splitter.setStretchFactor(1, 1)
```

**Anker 2 — Label der Aktion:**

```bash
grep -n "            N_('Display Commit Files')," cola/widgets/dag.py
```

Ersetze die Zeile durch

```python
            N_('Display Commit Details'),
```

> Der Zustandsschlüssel heißt weiterhin `display_files` — nur die Beschriftung ändert sich, weil
> das Panel jetzt mehr als Dateien zeigt. Das Label kommt in keiner `.po`-Datei vor
> (`grep -rl "Display Commit Files" cola/i18n/` liefert nichts), es geht also keine Übersetzung
> verloren.

**Anker 3 — Ein- und Ausblenden.** Zuerst die Beschreibung der Methode, die jetzt nicht mehr
stimmt:

```bash
grep -n '        """Toggle the embedded commit file panel and reload the current selection."""' cola/widgets/dag.py
```

Ersetze die Zeile durch

```python
        """Toggle the embedded commit details panel and reload the selection"""
```

Dann der Rumpf:

```bash
grep -n "        self.filewidget.setVisible(bool(enabled))" -B 4 -A 6 cola/widgets/dag.py
```

Ersetze den Rumpf von `display_files`

```python
        self.filewidget.setVisible(bool(enabled))
        if enabled and self.selection:
            self._schedule_files()
        else:
            self._files_timer.stop()
            self._files_dirty = False
            self.filewidget.clear()
```

durch

```python
        self.details_splitter.setVisible(bool(enabled))
        if enabled and self.selection:
            self._schedule_files()
        else:
            self._files_timer.stop()
            self._files_dirty = False
            self.filewidget.clear()
            self.descriptionwidget.clear()
```

> Die Wächter in `_schedule_files` und `_load_pending_files` fragen weiterhin
> `self.filewidget.isVisible()` und brauchen **keine** Änderung: ein verstecktes Eltern-Splitter
> macht auch die Kinder unsichtbar (Falle **F2**, gemessen).

**Anker 4 — Beschickung:**

```bash
grep -n "        self.filewidget.commits_selected(self.selection)" cola/widgets/dag.py
```

Ersetze die Zeile durch

```python
        self.filewidget.commits_selected(self.selection)
        # FileWidget arbeitet synchron - die Pfade stehen unmittelbar danach fest.
        # Das ist eine zugesicherte Eigenschaft, siehe
        # test_public_selection_reaches_all_standalone_consumers_synchronously.
        self.descriptionwidget.set_commit(
            self.selection[-1], self.filewidget.all_paths()
        )
```

**Anker 5 — Leeren:**

```bash
grep -n "        self.treewidget.clear()" -A 1 cola/widgets/dag.py
```

Ersetze in `CommitHistoryWidget.clear` die beiden Zeilen

```python
        self.treewidget.clear()
        self.filewidget.clear()
```

durch

```python
        self.treewidget.clear()
        self.filewidget.clear()
        self.descriptionwidget.clear()
```

**Anker 6 — die Architektur-Invariante mitpflegen.** `test_history_widget_owns_history_state_
without_window_children` (`test/widgets_dag_history_test.py:201`) zählt auf, was das History-Widget
besitzen **muss**. Die beiden neuen Kinder gehören dazu:

```bash
grep -n "        'files_splitter'," test/widgets_dag_history_test.py
```

Füge **direkt darunter** ein:

```python
        'details_splitter',
        'descriptionwidget',
```

**Anker 7 — die Struktur-Aussage im Hauptfenster mitpflegen** (Falle **F5**):

```bash
grep -n "    assert history.files_splitter.indexOf(history.filewidget) == 1" test/widgets_main_history_test.py
```

Ersetze die Zeile durch

```python
    assert history.files_splitter.indexOf(history.details_splitter) == 1
    assert history.details_splitter.indexOf(history.filewidget) == 1
```

### Verifikation

```bash
garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py test/widgets_main_history_test.py 2>&1 | tail -3
```

**Erwartet:** alle passed.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 37 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "feat: stack the description above the history file list

The right-hand panel is now a vertical splitter: the selected commit's message
on top, its changed files below. The existing debounce feeds both, and hiding
the parent splitter hides the children, so the visibility guards keep working
untouched."
```

---

## Task 5 — Die Aufteilung überlebt den Neustart

### Schritt 5.1 (RED) — Tests schreiben

Hänge an `test/widgets_dag_history_test.py` an:

```python
def test_history_state_carries_the_details_sizes(qapp, app_context, managed_qobject):
    """Die Hoehe der Beschreibung wird gespeichert."""
    history = managed_qobject(CommitHistoryWidget(app_context))

    state = history.export_state()

    assert 'details_sizes' in state
    assert state['details_sizes'] == history.details_splitter.sizes()


def test_history_applies_stored_details_sizes(qapp, app_context, managed_qobject):
    """Gespeicherte Groessen werden an den Splitter durchgereicht.

    Geprueft wird der Aufruf, nicht das Ergebnis: ein nie gezeigter QSplitter
    verteilt die Groessen selbst neu. Gemessen: nach setSizes([120, 240]) meldet
    sizes() [159, 317] (Falle F13).
    """
    history = managed_qobject(CommitHistoryWidget(app_context))
    applied = []
    history.details_splitter.setSizes = lambda sizes: applied.append(list(sizes))
    state = history.export_state()
    state['details_sizes'] = [120, 240]

    assert history.apply_state(state)
    assert applied == [[120, 240]]


@pytest.mark.parametrize('details_sizes', ('oops', [1, 'two'], [True, 2], {}))
def test_history_rejects_malformed_details_sizes(
    qapp, app_context, managed_qobject, details_sizes
):
    """Die Pruefung muss oberhalb des fruehen return fuer 'log' stehen (Falle F9)."""
    history = managed_qobject(CommitHistoryWidget(app_context))
    state = history.export_state()
    state.pop('log', None)
    state['details_sizes'] = details_sizes

    assert not history.is_valid_state(state)


def test_history_accepts_state_without_details_sizes(
    qapp, app_context, managed_qobject
):
    """Ein vor diesem Feature gespeicherter Zustand bleibt gueltig."""
    history = managed_qobject(CommitHistoryWidget(app_context))
    state = history.export_state()
    state.pop('details_sizes')

    assert history.is_valid_state(state)
    assert history.apply_state(state)
```

> **Kein neuer Import.** Die Tests vergleichen bewusst mit `details_splitter.sizes()` statt mit
> `qtutils.get(...)` — `get()` gibt für einen Splitter genau `sizes()` zurück
> (`cola/qtutils.py:111-112`), und so bleibt die Importliste der Testdatei unverändert.

**RED ausführen:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py -k details_sizes 2>&1 | tail -10
```

**Erwartete Fehlermeldungen — vier Tests, drei Ursachen:**

```
AssertionError: assert 'details_sizes' in {'count': ..., 'display_files': ..., ...}
AssertionError: assert [] == [[120, 240]]
AssertionError: assert not True
KeyError: 'details_sizes'
```

Der `KeyError` kommt aus `test_history_accepts_state_without_details_sizes`: dessen
`state.pop('details_sizes')` findet den Schlüssel noch nicht. Das ist ein zulässiges RED —
gemessen — und wird mit dem Export in Schritt 5.2 aufgelöst. `assert not True` stammt aus
`..._rejects_malformed_details_sizes`: ein unbekannter Schlüssel wird heute stillschweigend
akzeptiert.

### Schritt 5.2 (GREEN) — Export

**Anker:**

```bash
grep -n "            'files_sizes': get(self.files_splitter)," cola/widgets/dag.py
```

Füge **direkt darunter** ein:

```python
            'details_sizes': get(self.details_splitter),
```

### Schritt 5.3 (GREEN) — Validierung

**Anker:**

`log_state = state.get('log')` steht **zweimal** in der Datei — in `is_valid_state` und in
`apply_state`. Nur in `is_valid_state` folgt darauf `if log_state is None:`; dieses Zweizeilen-Paar
ist eindeutig (verifiziert):

```bash
grep -n "        log_state = state.get('log')" -A 1 cola/widgets/dag.py
```

**Erwartet:** zwei Blöcke, von denen genau einer mit `if log_state is None:` weitergeht. Füge
**direkt vor** genau diesem `log_state = state.get('log')` ein:

```python
        details_sizes = state.get('details_sizes')
        if details_sizes is not None and not (
            isinstance(details_sizes, (list, tuple))
            and all(
                isinstance(size, int) and not isinstance(size, bool)
                for size in details_sizes
            )
        ):
            return False
```

### Schritt 5.4 (GREEN) — Anwenden

**Anker:**

```bash
grep -n "        if files_sizes:" -A 1 cola/widgets/dag.py
```

Füge **direkt nach** `self.files_splitter.setSizes(list(files_sizes))` ein:

```python
        details_sizes = state.get('details_sizes')
        if details_sizes:
            self.details_splitter.setSizes(list(details_sizes))
```

### Schritt 5.5 (GREEN) — `HISTORY_KEYS` mitpflegen (Falle **F4**)

**Anker:**

```bash
grep -n "    'files_sizes'," test/widgets_main_history_test.py
```

Füge **direkt darunter** ein:

```python
    'details_sizes',
```

Und dort, wo `files_sizes` aus den Vergleichen entfernt wird, muss `details_sizes` genauso
entfernt werden — es hängt genauso an der gelebten Splitter-Geometrie:

```bash
grep -n "pop('files_sizes', None)" test/widgets_main_history_test.py test/widgets_dag_history_test.py
```

Füge **hinter jede** dieser Zeilen eine gleich aufgebaute Zeile mit `'details_sizes'` ein. Beispiel
für `history_state.pop('files_sizes', None)`:

```python
    history_state.pop('details_sizes', None)
```

> **Erwartet:** 9 Fundstellen — 7 in `test/widgets_main_history_test.py`, 2 in
> `test/widgets_dag_history_test.py`. Weicht die Zahl ab, **stoppen und melden**: dann hat sich
> eine Testdatei geändert und die Liste muss neu bestimmt werden.

### Verifikation

```bash
garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_dag_history_test.py test/widgets_main_history_test.py 2>&1 | tail -3
```

**Erwartet:** alle passed.

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 44 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "feat: persist how the details panel is split

details_sizes is exported, validated and applied. The validation sits above the
early return for 'log', because below it the check would never run for exactly
the legacy states it was written for."
```

---

## Task 6 — Ende-zu-Ende im Hauptfenster

**Ziel:** Ein Test mit echtem Repository, der belegt, dass die Auswahl eines Commits im
Hauptfenster tatsächlich Beschreibung **und** Markierung erzeugt.

### Schritt 6.1 (RED) — Test schreiben

Hänge an `test/widgets_main_history_test.py` an:

```python
def test_selected_commit_shows_its_description_with_marked_files(
    qapp, main_context, managed_qobject
):
    """Auswahl im Hauptfenster -> Message im Panel, Dateiname darin markiert."""
    with open('described.txt', 'w', encoding='utf-8') as handle:
        handle.write('content\n')
    _git('add', 'described.txt')
    _git(
        'commit',
        '-m',
        'feat: add described.txt\n\nThe file described.txt carries the content.',
    )
    main_context.model.update_status()
    window = managed_qobject(MainView(main_context))
    _show(qapp, window)
    _wait_for_history(qapp, window)
    _wait_for_commit_files(qapp, window, {'described.txt'})

    description = window.historywidget.descriptionwidget
    assert description.toPlainText().startswith('feat: add described.txt')
    assert 'The file described.txt carries the content.' in description.toPlainText()
    assert [path for _start, _end, path in description.highlighter.spans] == [
        'described.txt',
        'described.txt',
    ]
```

> **Warum zweimal `described.txt`?** Der Name steht im Betreff *und* im Rumpf; beide Vorkommen
> werden markiert. Genau das macht den Test aussagekräftig: er belegt, dass die Pfade der
> Dateiliste beim Beschreibungsfeld angekommen sind, und nicht nur, dass irgendein Text da steht.
>
> `_wait_for_commit_files` wartet, bis die Dateiliste gefüllt ist — und weil `_load_pending_files`
> die Beschreibung im selben Durchlauf beschickt, ist danach auch sie fertig. Der Helfer hat einen
> Zeitdeckel und endet mit einer Assertion, terminiert also in jedem Fall.

**RED ausführen:**

```bash
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q test/widgets_main_history_test.py -k marked_files 2>&1 | tail -12
```

**Erwartet:** **bereits grün.** Task 4 hat die Verdrahtung gelegt, Task 3 die Anzeige. Dieser Test
ist ein **Charakterisierungstest der fertigen Kette** — er belegt, dass die Teile im Hauptfenster
zusammenspielen und nicht nur einzeln funktionieren.

> Ist er **nicht** grün: **stoppen und melden.** Die Fehlermeldung sagt, welches Glied fehlt.

### Verifikation

```bash
garden fmt && QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=offscreen python3 -B -m pytest -p no:ruff -q cola test 2>&1 | tail -3
```

**Erwartet:** Baseline + 45 passed, 0 failed.

### Commit

```bash
git add -A && git commit -m "test: selected commit shows its description with marked files

The chain from selection through the debounce, git show and the marking can
only be exercised in the main window. This is a characterization test of the
finished state."
```

---

## Task 7 — Dokumentation

### Schritt 7.1 — `references/fork-history.md`

Anker:

```bash
grep -n "^## " .claude/skills/project-brief/references/fork-history.md
```

Füge **nach** dem Abschnitt `## 5. Mouse actions and HEAD marking in the history` und **vor**
`## Where the fork's tests live` ein:

```markdown
## 6. Commit description above the file list

Plan: `docs/plans/2026-08-01-commit-description-panel.md`.

The history's right-hand panel is a **vertical splitter**: the selected commit's message on top,
its changed files below. File names the message mentions are marked inside the text.

**Decisions that later work must not undo:**

- **The message is fetched per selection, not stored on `Commit`.** `LOGFMT`
  (`cola/models/dag.py:15`) stays subject-only: it is line-based, so a multi-line `%b` would break
  parsing for all 1000 commits and multiply their memory cost.
- **No second debounce.** The description rides the file panel's existing
  `_schedule_files` / `_files_timer` / `_load_pending_files` chain and its visibility guard.
- **The guards still ask `filewidget.isVisible()`** even though `display_files` now hides
  `details_splitter`. Hiding a parent splitter hides its children — measured, and the reason no
  guard had to change.
- **"Fuzzy" means path suffixes, not edit distance.** `commit_message_file_spans()` matches a path
  at every `/` boundary suffix, case-insensitively, never cutting into a surrounding token, longest
  candidate first. A basename *without* its extension is deliberately not a candidate — otherwise
  `main.py` would light up on the word "main".
- **The marking reuses `inline_graph_style()`**, so the file chips in the message look like the
  branch chips in the graph and inherit their contrast guarantee. That is also why the widget lives
  in `cola/widgets/dag.py`: `filelist.py` cannot import `dag.py` back.
- **The panel's text is exactly `%B`.** No author/date header — the columns already show that, and
  an exact text keeps the highlight offsets correct without translation.
- **`MonoTextEdit` starts with `NoWrap`**; `set_word_wrapping(True)` in the constructor is what
  makes the description readable.
```

Ergänze außerdem in der Testliste am Dateiende:

```markdown
- `test/widgets_dag_history_test.py` enthält zusätzlich die Tabellentests für
  `commit_message_file_spans()` und die Format-Tests des Beschreibungsfelds.
```

### Schritt 7.2 — `references/gotchas.md`

Hänge im Abschnitt `## Qt widget behavior` an:

```markdown
**`MonoTextEdit` and `PlainTextEdit` start with `NoWrap`.** `BaseTextEditExtension` sets it
(`cola/widgets/text.py:102`); the constructor's `line_wrap_mode` only takes effect through
`set_word_wrapping(True)` (`:337`). A read-only text view that forgets this gets a horizontal
scrollbar.

**Hiding a parent `QSplitter` hides its children.** `child.isVisible()` becomes `False` — measured
on the history's nested splitters. Visibility guards written against a child keep working when the
parent becomes the thing that is toggled.

**A `QSyntaxHighlighter`'s formats are invisible to `QTextCursor.charFormat()`.** They live as
additional formats in the layout; read them with `block.layout().formats()`.
```

### Schritt 7.3 — `SKILL.md`

Ersetze

```
Five work packages have shipped:
```

durch

```
Six work packages have shipped:
```

und ergänze den Aufzählungssatz um „and the commit description panel above the history's file
list".

### Schritt 7.4 — Plan als erledigt markieren

Setze die Frontmatter dieses Plans auf `status: completed` und ergänze `completed_at`,
`plan_commit`, `implementation_branch`, `implementation_head`, `ci_run` und
`manual_verification` — wie in `docs/plans/README.md` beschrieben. Stelle die Zeile dieses Plans
in der Tabelle von `docs/plans/README.md` von **open** auf **completed** um. (Der Index ist seit
2026-07-31 auf Englisch; die Statuswörter in der Tabelle heißen jetzt so.)

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

**Erwartet:** ohne Befund. Fehlt ein Werkzeug, ist das kein Abbruchgrund: notieren, welche
Prüfung nicht lief.

### Commit

```bash
git add -A && git commit -m "docs: document the history's commit description panel"
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

1. Einen Commit in der History anklicken: oben rechts erscheint seine Message, unten seine Dateien.
2. Eine Message mit mehreren Absätzen wählen: der Text bricht um, keine waagerechte Bildlaufleiste.
3. Ein Commit, dessen Message einen Dateinamen nennt: der Name ist im Text farbig hinterlegt und
   fett, in hellem **und** dunklem Theme lesbar (`View → Theme` umschalten).
4. Die erste Zeile (Betreff) ist fett.
5. Den Griff zwischen Beschreibung und Dateiliste ziehen, App schließen und neu starten: die
   Aufteilung ist noch da.
6. `View → Display Commit Details` aus- und wieder einschalten: beide Hälften verschwinden und
   kommen zurück.
7. Einen Commit ohne Rumpf wählen (nur Betreff): nur die fette Zeile, kein Leerraum-Artefakt.
8. Dasselbe im eigenständigen DAG-Fenster, nachdem `Display Commit Details` dort eingeschaltet
   wurde.

> **In einer Umgebung ohne Anzeige entfällt dieser Abschnitt.** Dann gilt: die Punkte 1, 4, 5, 6
> und 7 sind durch die Tests aus Task 3–6 abgedeckt; **2, 3 und 8 sind es nicht** — Zeilenumbruch
> und Farbwirkung sind zwar numerisch geprüft (`lineWrapMode()`, Chip-Farben mit garantiertem
> Kontrast), aber niemand hat sie angesehen. **Im Abschlussbericht so schreiben, nicht als
> „geprüft" ausgeben.**
