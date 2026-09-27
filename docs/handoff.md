> **Last updated:** 2026-09-27 15:51 WEST (Europe/Lisbon)
> Replace with the current date and time whenever you edit this file.

# Session handoff

## Done

- Phase one is running locally: Google login, voice upload, OpenAI transcription, TypeSafe classification. SQLite. Durations in seconds. No Stripe, quotas, translation, retrieval, or Celery.
- Apps live under `src/` (`src.accounts`, `src.diary`, `src.conference`, `src.config`). Settings: `src.config.settings.dev` / `.prod` / `.test`.
- File attachments stay on diary entries. User files under `media/attachments/`. Processed diary audio under `media/artifacts/`.
- Conferencing is a separate app. The user opens `/conference/`. One conference row holds the conversation. Each upload is a segment under `media/conferences/<user>/<conference>/`. A full segment is at most 240 seconds and does not close the conference. The last segment, of any shorter length, closes it. Segment transcripts are joined in sequence order. Diary JEV is not called. Classification questions for a finished conference are not defined yet.
- Diary voice links to Conference. Held-part crash backups from a conference are not recovered as diary entries.
- Pytest: 29 passed. Django check is clean.

## Not done

- Conference classification (own question set, after stop). Not the diary taxonomy, and not a length label.
- Diary prior-context rules discussed earlier are not changed: priors still wait until two older rows exist, and file-only rows can still appear as prior text.
- Summary (phase two). Conditions for when to summarize are not defined.
- Phase-three backlog: translation, retrieval/chat, GIGO, quotas, Stripe, verifier, list/todo/finance/calendar records, venue/day/time, extra taxonomy dimensions, Celery/Redis/WebSockets, Gmail/Drive/Calendar API calls.
- `GET /service-worker.js` returns 404. The new app does not register a worker.
- `ffprobe` sometimes logs `Could not parse ffprobe duration: N/A` on upload.
- Google Cloud authorized redirect is still the sample `/src.accounts/...` path.
- Browser recording of a conference was not clicked through here (Google login, no browser tools). Start, segment upload, stop, and page markup were checked with the Django test client.

## Next

Define the conference question set, then classify the joined transcript once after stop.

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
