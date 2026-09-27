# Voice Diary

A Django app for short voice and text notes, local file attachments, and longer conference recordings. Sign-in is Google OAuth. New code lives under `src/`.

`sample-old-version-delete-when-finished-using/` is a read-only reference for older behavior. Do not copy its layout into this project, and do not commit secrets.

Living notes: [`docs/handoff.md`](docs/handoff.md) (latest session) and [`docs/project-plan.md`](docs/project-plan.md) (phases and backlog).

## What works now

- **Accounts** (`src.accounts`) — Google login, profile, connect/disconnect. Tokens are stored encrypted. The Google Cloud client still allows the sample callback path `/src.accounts/google/callback/`; this app also serves `/accounts/google/callback/`.
- **Diary** (`src.diary`) — Record or type an entry. Voice supports pause/resume, microphone interruption, IndexedDB recovery, and a rollover at `RECORDER_MAX_DURATION` (default 240 seconds). Audio is trimmed, silence is stripped with ffmpeg, and OpenAI transcribes it. TypeSafe System One (Jev) classifies intent, subject, and two yes/no checks. Follow-up, reschedule, or appointment routes to calendar even if the user asked for the diary.
- **Attachments** — Any file type. Sent with voice stop or text save, they link to that entry. Uploaded with nothing in progress, they become their own `file` entry. Files can also be added later on `/entries/`. Downloads are owner-only. User files: `media/attachments/`. Processed diary audio: `media/artifacts/`.
- **Conference** (`src.conference`) — A separate long-recording mode at `/conference/`. One conference holds the conversation. Audio is stored as segments of at most 240 seconds under `media/conferences/<user>/<conference>/`. Each segment is transcribed as it arrives; the last shorter segment closes the conference. Diary Jev is not called. Classification questions for a finished conference are not defined yet.

There is no Stripe, quota gate, summary, translation, retrieval/chat, or Celery.

## Layout

```text
manage.py
src/
  config/          project package, split settings
  accounts/        Google auth and profile
  diary/           short voice/text entries, attachments, Jev
  conference/      long recordings and segments
docs/
  handoff.md
  project-plan.md
```

Settings modules:

| Module | Use |
| --- | --- |
| `src.config.settings.dev` | local |
| `src.config.settings.prod` | production |
| `src.config.settings.test` | pytest and `manage.py test` |

Local `.env` should set `DJANGO_SETTINGS_MODULE=src.config.settings.dev`. Production deploy sets prod.

## Pages

| Path | App |
| --- | --- |
| `/voice/` | Diary record |
| `/text-input/` | Diary typed entry |
| `/entries/` | Diary list and later file attach |
| `/conference/` | Conference record |
| `/conference/list/` | Conference list |
| `/accounts/login/` | Google sign-in |
| `/accounts/profile/` | Profile |

`/` redirects to the diary voice page.

## Local setup

Python 3.12+, ffmpeg/ffprobe on `PATH` (silence strip and duration probe), and a Google OAuth client.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` (do not commit it):

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret |
| `ALLOWED_HOSTS` | comma-separated hosts |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth client |
| `GOOGLE_OAUTH_REDIRECT_URI` | default `http://localhost:8000/accounts/google/callback/` |
| `MASTER_ENCRYPTION_KEY` | Fernet key for stored Google tokens |
| `AI_OPENAI_API_KEY` | transcription |
| `TRANSCRIPTION_MODEL` | default `gpt-4o-transcribe` |
| `JEV_API_KEY` | TypeSafe console key (`apikey_…`), not a hosted `jv_live_` key |
| `JEV_API_URL` | default `https://api.typesafe.ai/v1/systemone` |
| `PRIOR_ENTRY_COUNT` | prior diary rows sent to Jev (default 2) |
| `RECORDER_MAX_DURATION` | voice/conference segment cap in seconds (default 240) |

Generate the Fernet key:

```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Then:

```bash
.venv/bin/python manage.py migrate
DJANGO_SETTINGS_MODULE=src.config.settings.dev .venv/bin/python manage.py runserver
```

Open `http://127.0.0.1:8000/` and sign in with Google.

## Tests

Every `test_*` is marked `unit` or `integration` (see [`pytest.ini`](pytest.ini) and [`.cursor/rules/pytest-markers.mdc`](.cursor/rules/pytest-markers.mdc)). `django_db` is added when the test touches the database.

```bash
.venv/bin/python manage.py check
.venv/bin/pytest -q
.venv/bin/pytest -m unit
.venv/bin/pytest -m integration
```

## Production

Set `DJANGO_SETTINGS_MODULE=src.config.settings.prod`. Prod requires `SECRET_KEY`, `ALLOWED_HOSTS`, Google client values, and the OAuth redirect URI. It enables TLS-related cookie flags and `SECURE_SSL_REDIRECT`.

## Not in this rewrite yet

Phase two (summary, conditions undefined), conference classification after stop, and the phase-three backlog (translation, retrieval, quotas, Stripe, list/todo/finance/calendar records, Celery, and the rest). See [`docs/project-plan.md`](docs/project-plan.md).
