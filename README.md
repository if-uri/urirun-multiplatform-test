# urirun-multiplatform-test

[![urirun multiplatform e2e](https://github.com/if-uri/urirun-multiplatform-test/actions/workflows/multiplatform.yml/badge.svg)](https://github.com/if-uri/urirun-multiplatform-test/actions/workflows/multiplatform.yml)

Samodzielny black-box test harness dla `urirun`. Repo pobiera wskazaną wersję `urirun`, instaluje ją w świeżym virtualenv, uruchamia realne komendy CLI i zapisuje raporty diagnostyczne do `reports/`.

## Architektura

Linux jest testowany przez Docker, bo kontenery Linux są normalnym i powtarzalnym środowiskiem testowym.

Windows i macOS nie są tu udawane jako zwykłe kontenery Docker. Te systemy są testowane przez GitHub Actions runners (`windows-latest`, `macos-latest`) albo mogą zostać przeniesione na self-hosted runners z tym samym workflow. To jest celowe: kontenery Windows/macOS nie są równoważnym, legalnie i technicznie prostym substytutem pełnych runnerów dla tego typu E2E.

## Profile

- `linux-docker` - buduje `docker/linux/Dockerfile` i uruchamia cały suite w kontenerze.
- `windows-runner` - uruchamia suite bezpośrednio na runnerze Windows.
- `macos-runner` - uruchamia suite bezpośrednio na runnerze macOS.

## Zmienne środowiskowe

- `URIRUN_REPO_URL` - repozytorium `urirun` do sklonowania. Domyślnie `https://github.com/if-uri/urirun.git`.
- `URIRUN_REF` - branch/tag/commit do testowania. Domyślnie `main`.
- `URIRUN_SOURCE_DIR` - opcjonalnie lokalna ścieżka do źródeł `urirun`; użyteczne w development, omija `git clone`, ale nadal wykonuje instalację pakietu.
- `URIRUN_TEST_PROFILE` - nazwa profilu, ustawiana przez CI.
- `URIRUN_TEST_VENV` - ścieżka do virtualenv używanego przez testy; zwykle ustawiana automatycznie.

## Lokalnie

Z domyślnego GitHuba:

```bash
python scripts/run_tests.py
```

Po świeżym checkoutcie nie trzeba tworzyć `.work/` ręcznie. `scripts/run_tests.py` sam:

- tworzy `.work/venv`,
- instaluje zależności test harnessu,
- pobiera albo wskazuje źródła `urirun`,
- instaluje `urirun`,
- uruchamia pytest,
- zbiera `reports/summary.json`.
- zapisuje `reports/junit.xml`.

Na lokalnym checkoutcie `urirun`:

```bash
URIRUN_SOURCE_DIR=/path/to/urirun python scripts/run_tests.py
```

Windows PowerShell:

```powershell
$env:URIRUN_SOURCE_DIR="C:\Users\Praca\fork\if-uri\urirun"
python scripts\run_tests.py
```

Można też uruchamiać sam `pytest`, ale najpierw trzeba przygotować środowisko:

```bash
python scripts/bootstrap.py
python scripts/install_urirun.py
.work/venv/bin/python -m pytest
```

## Docker Linux

```bash
docker build -t urirun-linux-test -f docker/linux/Dockerfile .
docker run --rm urirun-linux-test
```

Jeżeli chcesz zachować raporty poza kontenerem:

```bash
docker run --rm -v "$PWD/reports:/workspace/reports" urirun-linux-test
```

## GitHub Actions

Workflow jest w `.github/workflows/multiplatform.yml`. Matrix uruchamia:

- `ubuntu-latest` z profilem `linux-docker`,
- `windows-latest` z profilem `windows-runner`,
- `macos-latest` z profilem `macos-runner`.

Workflow checkoutuje repo testowe, instaluje Python i Node, pobiera/instaluje `urirun`, uruchamia testy, uploaduje `reports/` jako artifact i dopisuje summary do GitHub Actions.

Dla self-hosted runnerów można skopiować ten sam job i zmienić `runs-on` na własne etykiety, np. `[self-hosted, windows, urirun]` albo `[self-hosted, macOS, urirun]`. Ważne, żeby runner miał Python 3.10+, Git, dostęp do `URIRUN_REPO_URL` oraz właściwą powłokę systemową.

## Raporty

Raporty JSON w `reports/` zawierają:

- system operacyjny,
- wersję Pythona,
- wersję Node, jeśli jest dostępna,
- wersję `urirun`,
- komendę,
- exit code,
- stdout,
- stderr,
- stack trace, jeśli błąd pochodzi z pytest/Pythona,
- minimalną rekomendację naprawy.

`scripts/collect_report.py` tworzy `reports/summary.json`.

## Testy

Aktualnie zaimplementowane:

- instalacja i `urirun --version`,
- świeży bootstrap bez istniejącego `.work/`,
- `urirun doctor --json`,
- `urirun version --no-check`,
- help dla głównych subkomend CLI,
- walidacja fixture registry,
- `discover`,
- `tree --format json`,
- `gen openapi`,
- `agent space`,
- `errors bindings`,
- `add-command`,
- konfiguracja `node init/config` bez startowania usługi,
- konfiguracja `host init/add-node/config` bez sieci,
- lista tras z registry,
- błędna komenda CLI,
- kompilacja registry,
- `urirun run` dla realnej trasy `argv-template`,
- błędny URI,
- `urirun connectors show planfile` jako `xfail` dla obecnej niezgodności handlera CLI,
- `urirun connectors doctor --json` dla wbudowanych connectorów `ready`, `session`, `skill`,
- bezpieczny dry-run `connectors install` dla kilku connector ids,
- deny-by-default bez `--allow`,
- błędna allow-list,
- ścieżki natywne Windows/Linux/macOS,
- ścieżki z odstępami,
- output file w katalogu ze spacją,
- smoke test shelli: bash tam gdzie dostępny, PowerShell tam gdzie dostępny, `cmd.exe` na Windows,
- raport błędu dla intencjonalnie padającej trasy,
- zapis/wykrycie `error://` lub error log dla odmowy polityki,
- stack trace dla błędów procesu jako `xfail`, bo aktualny envelope CLI nie gwarantuje pełnego tracebacku.

## Stabilność

Markery pytest:

- `stable` - podstawowy cross-platform suite,
- `experimental` - przydatna powierzchnia, która może się jeszcze zmieniać,
- `expected_failure` - znany brak albo niestabilne zachowanie, zwykle z `xfail`.

## Znane ograniczenia

Aktualny `urirun` z lokalnego repo deklaruje zależności `urirun-contract`, `urirun-connector-router` i `urirun-flow`, których pip może nie znaleźć jako publiczne pakiety. Instalator najpierw próbuje normalnego `pip install`; jeśli to się nie uda, zapisuje `reports/install-warning.json`, instaluje dostępne publiczne zależności i wykonuje kontrolowany fallback `pip install --no-deps` plus `PYTHONPATH` do pobranych źródeł. To nadal uruchamia realny CLI i realne procesy, ale raportuje problem pakietowania zamiast go ukrywać.

TODO:

- usunąć fallback po opublikowaniu albo poprawnym vendoringu wszystkich zależności `urirun`,
- odwrócić `xfail` dla `connectors show planfile`, gdy handler CLI obsłuży komendę,
- dodać pełniejszy test transportów HTTP/gRPC/MCP inspirowany `examples/matrix`,
- dodać self-hosted runner examples dla firmowych Windows/macOS hostów.
