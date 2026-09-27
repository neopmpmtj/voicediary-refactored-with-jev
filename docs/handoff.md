> **Last updated:** 2026-09-27 11:11 WEST (Europe/Lisbon)
> Replace with the current date and time whenever you edit this file.

# Session handoff

## Done

- Phase one is running locally: Google login, voice upload, OpenAI transcription, TypeSafe classification. SQLite. Durations in seconds. No Stripe, quotas, translation, retrieval, or Celery.
- Apps and the project package live under `src/` (`src.accounts`, `src.diary`, `src.config`). Settings: `src.config.settings.dev` / `.prod` / `.test`. Local `.env` uses dev. Production deploy sets prod.
- Google callback URL in this app is `/accounts/google/callback/`. The Google Cloud client is still registered on the sample path `/src.accounts/google/callback/`; that path is also wired in `src/config/urls.py` so login works. Canonical public URL stays `/accounts/`.
- Classification calls TypeSafe System One: `POST https://api.typesafe.ai/v1/systemone` with `model=jev-latest` and `Authorization: Bearer` of a console `apikey_…` key (`JEV_API_KEY`). Hosted `jevtypesafeai.com` `jv_live_` keys are not used.
- Local Google OAuth and Jev classification were verified by the user. Pytest: 7 passed.

Uncommitted: the `src/` move, settings split, Google callback alias, TypeSafe URL. `.env` is gitignored.

## Not done

- Summary (phase two). Conditions for when to summarize are not defined.
- Phase-three backlog: translation, retrieval/chat, GIGO, quotas, Stripe, verifier, list/todo/finance/calendar records, venue/day/time, extra taxonomy dimensions, Celery/Redis/WebSockets, Gmail/Drive/Calendar API calls.
- `GET /service-worker.js` returns 404. The new app does not register a worker. Left as-is after an explicit pause.
- `ffprobe` sometimes logs `Could not parse ffprobe duration: N/A` on upload. Classification still completes.
- Google Cloud authorized redirect is still the sample `/src.accounts/...` path. Changing it to `/accounts/google/callback/` in the console would let the alias be removed.

## Next

Phase two when the summary conditions are chosen. Commit the `src/` layout if that is wanted.

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
