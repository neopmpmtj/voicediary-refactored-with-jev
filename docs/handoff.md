> **Last updated:** 2026-09-28 11:10 WEST (Europe/Lisbon)
> Replace with the current date and time whenever you edit this file.

# Session handoff

## Done

- Phase one is running locally: Google login, voice upload, OpenAI transcription, TypeSafe classification. SQLite. Durations in seconds. No Stripe, quotas, translation, retrieval, or Celery.
- Apps live under `src/` (`src.accounts`, `src.diary`, `src.conference`, `src.urls_others`, `src.textrewrite`, `src.conferencerewrite`, `src.config`). Settings: `src.config.settings.dev` / `.prod` / `.test`.
- File attachments stay on diary entries. User files under `media/attachments/`. Processed diary audio under `media/artifacts/`.
- Voice-page attach bugs are fixed on `cursor/fix-audio-attachments-2973` (PR #4): Attach is a real button, empty Stop uploads queued files instead of dropping them, CSRF token is on the page, and the entries Add-files form reports success or asks for a file.
- Conferencing is a separate app. The user opens `/conference/`. One conference row holds the conversation. Each upload is a segment under `media/conferences/<user>/<conference>/`. A full segment is at most 240 seconds and does not close the conference. The last segment, of any shorter length, closes it. Segment transcripts are joined in sequence order. Diary JEV is not called. Classification questions for a finished conference are not defined yet.
- Diary voice links to Conference. Held-part crash backups from a conference are not recovered as diary entries.
- Pytest: 121 passed. Django check is clean.
- Visual shell matches the old Voice Diary chrome on the screens that exist: near-black, Inter, green accent, red 72px record button that starts/pauses/resumes, Stop while live. Tailwind via `django-tailwind-cli`. User-facing strings wrapped in `{% trans %}`.
- Entries list hides a missing or soft-deleted attachment and does not write. `python manage.py media_release <path>` deletes that file under `media/` and soft-deletes the matching row. A file-only entry is soft-deleted when no active attachment remains. Inventory: [docs/commands.md](commands.md).
- Entries cards have Delete, Edit, and Copy. Delete soft-deletes the entry and frees attached files. Edit saves text in a modal without reclassifying. Copy uses the clipboard.
- URL and endpoint capture: Jev `reference` choice (`url` / `endpoint` / `none`) on the existing diary call. Matching entries also write rows in `src.urls_others`. Regex parse, no second model call. CLI: `url_list`.
- Phase two is rewrite. Two apps already do it. `src.textrewrite` (`rewrite_text`, `rewrite_run`) and `src.conferencerewrite` (`rewrite_text`, `conference_rewrite_run`). OpenAI Responses only. Source and rewrite stay in memory. A successful call writes a usage row (date, model, tokens). The conference prompt asks for a heading on each grouped idea.

## Not done

- Interface language after the shell: `pt-pt` default, `en` available. Separate from diary-content translation.
- Conference classification (own question set, after stop). Not the diary taxonomy, and not a length label. It does not wait on the visual shell.
- Diary prior-context rules discussed earlier are not changed: priors still wait until two older rows exist, and file-only rows can still appear as prior text.
- Phase-three backlog: translation, retrieval/chat, GIGO, quotas, Stripe, verifier, list/todo/finance/calendar records, venue/day/time, extra taxonomy dimensions, Celery/Redis/WebSockets, Gmail/Drive/Calendar API calls.
- `GET /service-worker.js` returns 404. The new app does not register a worker.
- `ffprobe` sometimes logs `Could not parse ffprobe duration: N/A` on upload.
- Google Cloud authorized redirect is still the sample `/src.accounts/...` path.

## Next

Interface language (`pt-pt` default, `en`). Conference classification can proceed beside that.

## Commands

```bash
# local
DJANGO_SETTINGS_MODULE=src.config.settings.dev
.venv/bin/python manage.py runserver

# checks
.venv/bin/python manage.py check
.venv/bin/pytest -q
.venv/bin/python manage.py tailwind build

# production
DJANGO_SETTINGS_MODULE=src.config.settings.prod
```
