> **Last updated:** 2026-09-27 09:34 WEST (Europe/Lisbon)
> Replace with the current date and time whenever you edit this file.

# Session handoff

## Done

- Phase one is in the repo: Google OAuth login, voice and text input, silence removal, OpenAI transcription in the original language (optional `AI_TRANSCRIPTION_PROMPT`), Jev classification, route stored on the entry, usage log (audio minutes plus Jev tokens). Durations are stored in seconds. SQLite. No Stripe, quotas, translation, retrieval, or Celery.
- Settings are split: `src/config/settings/{base,dev,prod,test}.py`. `BASE_DIR` is the repo root.
- Apps and the project package live under `src/` (`src.accounts`, `src.diary`, `src.config`).
- `manage.py` forces `src.config.settings.test` when `test` is in `sys.argv`. Otherwise it defaults to `src.config.settings.dev`. WSGI and ASGI default to dev. `pytest.ini` uses `src.config.settings.test`.
- `.env.example` and the local `.env` use `DJANGO_SETTINGS_MODULE=src.config.settings.dev`. Production deploy sets `src.config.settings.prod`.
- `manage.py check` is clean. Pytest: 7 passed.

The settings split is uncommitted. `.env` is gitignored.

## Not done

- Summary (phase two). Conditions for when to summarize are not defined.
- Phase-three backlog: translation, retrieval/chat, GIGO, quotas, Stripe, verifier, list/todo/finance/calendar records, venue/day/time, extra taxonomy dimensions, Celery/Redis/WebSockets, Gmail/Drive/Calendar API calls.
- `GET /service-worker.js` returns 404. The new app does not register a worker. Left as-is after an explicit pause.
- Database stays SQLite. Postgres was not part of the settings split.

## Next

Restart the dev server so it loads `src.config.settings.dev`. Phase two starts when the summary conditions are chosen.

## Commands

```bash
# local
DJANGO_SETTINGS_MODULE=src.config.settings.dev
.venv/bin/python manage.py runserver

# checks
.venv/bin/python manage.py check
.venv/bin/pytest -q

# production
DJANGO_SETTINGS_MODULE=src.config.settings.prod
```
