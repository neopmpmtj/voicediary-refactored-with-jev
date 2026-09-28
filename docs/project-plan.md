# Project plan

- [x] Phase one — input and classify
- [x] File attachments (local, timestamped, optional link to an input)
- [x] URL and endpoint capture (JEV `reference` choice; `src.urls_others` rows)
- [x] Text rewrite (CLI + in-memory `rewrite_text`; Responses API)
- [x] Conference rewrite (CLI + in-memory `rewrite_text`; headings; Responses API)
- [ ] Conferencing
- [x] Visual shell
- [ ] Interface language
- [x] Phase two — rewrite (`src.textrewrite`, `src.conferencerewrite`)
- [ ] Phase three — some of the backlog

## Phase one — input and classify

A Google-authenticated user records or types an entry. Voice keeps the current input behavior: swipe between voice and text, pause and resume, microphone interruption, one merged recording, IndexedDB recovery, and automatic restart at `RECORDER_MAX_DURATION` (default 240 seconds). Audio is trimmed, silence is removed, and OpenAI transcribes it in the original language. Durations stored are the original length and the length after silence removal, in seconds. File sizes are not stored.

Jev classifies each entry in one call: intent (freeform, list, follow-up, todo, reschedule), subject (diary, finance, appointment), and two yes/no checks (the user asked for the diary, and this continues the prior entries). Prior entries are included only after two rows exist. The count defaults to 2 (`PRIOR_ENTRY_COUNT`). A prior recording is included only when its duration is known and shorter than `RECORDER_MAX_DURATION`. A missing duration stays out.

Decided, not built yet:

- Prior context starts when one older row exists. The cap stays `PRIOR_ENTRY_COUNT`.
- A file-only upload is not a prior utterance. Attachment filenames on a voice or text entry are their own field. The utterance text stays the transcript or the typed note.

If the intent is follow-up or reschedule, or the subject is appointment, the stored route is calendar. That wins even when the user asked for the diary. The diary answer is still stored.

Usage is logged. Transcription is stored as audio minutes, because the transcription response has no token count. Jev input and output tokens are stored. There is no quota gate and no Stripe charge.

## URL and endpoint capture

Jev's diary call includes a `reference` choice: `url`, `endpoint`, or `none`. The diary entry still stores the raw typed text or transcript. When the choice is `url` or `endpoint`, a regex script in `src.urls_others` writes one row per parsed address into its own table. `http(s)` addresses are `url` (including an API-looking host). `GET /v1/users` and paths starting with `/api/` or `/vN/` are `endpoint`. Leftover text is the row's note. A leftover note currently calls `start_process`, which logs a reminder; the LLM start-process call is later. Classification failure or `none` writes no reference rows. Fetching descriptions is later work; rows start as `pending`. CLI: `url_list --email` (`--json`).

## Text rewrite

A standalone app (`src.textrewrite`). Other functions call `rewrite_text(text, model_id=None)`. The CLI is the same function.

One OpenAI Responses call. Models come from `src/textrewrite/openai_models.json` at runtime (default `o3-mini`). The instruction lives in `src/textrewrite/rewrite_prompt.txt`. The Responses caller receives a model id, the instruction, and the source text. No tools. OpenAI only.

The function returns the rewritten prose, the model id, and the token counts. The source text and the rewrite are not stored. A successful call writes a `RewriteUsage` row (date, model, tokens). A failed call writes nothing and raises `RewriteError`. A missing API key is rejected before the request. A network failure is tried once more. An auth or billing refusal, and an empty reply, raise immediately.

CLI: `rewrite_run` (`--file`, `--model`, `--json`). File or stdin. No `--email`.

## Conference rewrite

A standalone copy of text rewrite (`src.conferencerewrite`). Other functions call `rewrite_text(text, model_id=None)`. The CLI is the same function.

The shape matches text rewrite: OpenAI Responses only, models from `src/conferencerewrite/openai_models.json` (default `o3-mini`), usage row on success, no stored source or rewrite. The instruction lives in `src/conferencerewrite/conference_rewrite_prompt.txt` and asks for a heading on each grouped idea.

CLI: `conference_rewrite_run` (`--file`, `--model`, `--json`). File or stdin. No `--email`.

## File attachments

Any file type can be added at any stage. Each file stores the upload date and time. User files live under `media/attachments/`. Processed audio artifacts live under `media/artifacts/`.

- Files sent when a recording stops or a text entry is saved are linked to that input.
- If no file is sent, the input has no attachment link.
- Files uploaded with no voice or text in progress become their own input (`item_type=file`).
- Files can also be added later to an existing entry on the entries list.

## Conferencing

A separate app from the diary. The user chooses this mode. The diary stays the short-note path.

A conference is one conversation. Audio is stored as segments of at most `RECORDER_MAX_DURATION` (default 240 seconds). When the user stops, the last segment is whatever length remains, and it still belongs to that conference.

Two tables:

- **Conference** — the conversation. Created when recording starts, closed when the user stops. Holds the user, the joined transcript, the total duration, and classification after stop.
- **Segment** — one audio file in order. Sequence number, duration, transcript, and file location. Order is the sequence number.

Audio lives under `media/conferences/<user>/<conference>/`, separate from diary recordings and from user attachments.

Pause, resume, and microphone interruption are merged inside a segment before upload. The 240-second boundary is the only split. Each full segment is uploaded and transcribed while recording continues. JEV is not called on a segment.

Diary questions stay on short entries. A finished conference is not classified with that taxonomy. "Conference" is not a diary intent or subject, and it is not chosen because the audio is longer than 240 seconds. The mode already records that. Questions for the joined conference are a separate set and are not defined yet.

Build order:

1. [x] Start, roll over at 240 seconds, and stop, including a short final segment, on one conference. No classification.
2. [x] Transcribe each segment as it arrives.
3. [ ] After stop, one classification call. Segment texts stay in order as parts of that conference. The question set is not defined yet.

`recording_group_id` on a diary entry is not the conference model.

Conference classification does not wait on the visual shell. New screens are not designed in the temporary cream layout. They follow [docs/ui-rules.md](ui-rules.md).

## Visual shell

Applied [docs/ui-rules.md](ui-rules.md) to the screens that exist: sign-in, voice, text, entries, conference record, conference list, profile, and Google link-confirm.

The shell is a replica of the old Voice Diary chrome, with fewer screens. Tailwind via `django-tailwind-cli` is required so the old layout, spacing, and `vd-` components match. JavaScript stays plain. No React.

Near-black background, Inter, green accent for cards and dots, a centered column of about 42rem, and the red 72px record button. One button starts, pauses, and resumes. The `recording` class pulses. Paused is a darker red and does not pulse. Stop appears while the take is live.

Recorder behavior in `src/diary/static/diary/js/voice_page.js` and `src/conference/static/conference/js/conference_page.js` stays except for that control pattern.

While this shell is built, wrap every user-facing string in `{% trans %}`. The Portuguese catalog is the next phase, not this one.

## Interface language

Immediately after the visual shell, and before any new pages, so later screens are born bilingual.

English and Portuguese (`en` and `pt-pt`). The default is `pt-pt`, matching the app this repo replaces. English strings in code are the message ids. Portuguese is the catalog.

`LocaleMiddleware`, `LOCALE_PATHS`, a user language preference, and a language control. This is the interface chrome: buttons, errors, and empty states.

This is not the backlog item Translation. That item translates diary content.

## Phase two — rewrite

Rewrite replaces the earlier summary step. Two apps already do this work. Each is a standalone OpenAI Responses call. The source text and the rewrite stay in memory. A successful call writes a usage row (date, model, tokens).

- Text rewrite (`src.textrewrite`): `rewrite_text` and `rewrite_run`. See [Text rewrite](#text-rewrite).
- Conference rewrite (`src.conferencerewrite`): `rewrite_text` and `conference_rewrite_run`. The prompt asks for a heading on each grouped idea. See [Conference rewrite](#conference-rewrite).

## Phase three — some of the backlog

Phase three takes some of the items below, not all of them. Which ones is decided when that phase starts.

### Backlog

- Translation (diary content, not the interface language)
- Retrieval and chat
- GIGO
- Quotas
- Stripe
- Taxonomy verifier
- List, todo, finance, and calendar records
- Venue, day, and time extraction
- Context, time, and governance taxonomy dimensions
- Celery, Redis, and pipeline WebSockets
- Gmail, Drive, and Calendar API calls (full OAuth scopes are requested in phase one)
