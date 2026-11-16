# CI — TidalBot

Stato verificato il 16 novembre 2026. Non esiste una pipeline di deploy: pubblicare significa fare push su `main` e lasciare che la CI verifichi il commit.

## Integrazione continua

`.github/workflows/ci.yml` gira su push e pull request verso `main`:

1. checkout con `persist-credentials: false`;
2. Python 3.11 preparato con `astral-sh/setup-uv` (uv 0.12.23);
3. riuso di `.venv` se il suo interprete è Python 3.11, altrimenti `uv venv --python 3.11 --clear .venv`;
4. `uv pip install --python .venv/bin/python -r requirements.txt`;
5. `python -m unittest discover -s tests -q`.

Dettagli che contano:

- `paths-ignore: ["**.md", "docs/**"]`: una modifica alla sola documentazione non fa partire la CI, quindi il workflow non compare tra le esecuzioni di quel commit.
- concorrenza su `ci-${{ github.ref }}` con `cancel-in-progress`: un nuovo push annulla l'esecuzione precedente dello stesso ref.
- permessi minimi: `contents: read`.

La suite (`tests/test_tidalbot.py`, 16 test) non usa la rete né una sessione Tidal: costruisce l'oggetto con `TidalBot.__new__` e verifica parsing della tracklist, serializzazione delle date e punteggio di similarità. Non copre autenticazione, ricerca reale, creazione della playlist né `process_songs`.

## Riproduzione in locale

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m unittest discover -s tests -q
```

Atteso: 16 test verdi (`Ran 16 tests ... OK`), in meno di un decimo di secondo. Le dipendenze servono ai test perché `test_tidalbot.py` importa `tidalbot.py`, che importa `tidalapi`.

## Deployment continuo

Non c'è. Il progetto non espone servizi, non ha un container, un timer o un workflow di pubblicazione: dopo un merge su `main` non viene distribuito nulla. `tidal_session.json` resta sulla macchina di chi esegue lo script ed è in `.gitignore`.

## Storia

Questo file e `.github/workflows/ci.yml` nascevano dall'installer `agent-pipeline`. Il dispatch issue→PR (etichette `ai-fix` / `ai-fix-complex`, PR automatiche) è stato ritirato per questo repository: `.agent/pipeline.yml` non esiste più e la voce in `/home/gangio/agent-pipeline/registry.yml` su CT102 riporta `enabled: false`. Il workflow e questo documento sono ora mantenuti a mano.
