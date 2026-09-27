# Voice Diary (refactored)

This repo is a new Voice Diary implementation. Put new app code under `src/`, outside `sample-old-version-delete-when-finished-using/`.

`sample-old-version-delete-when-finished-using/` is a read-only reference for behavior and constraints. Do not copy its layout or files in as the implementation. Do not edit it unless asked.

Do not commit secrets. Sample env and credential files stay reference-only.

## Session

**Done**

- Phase one input and classify is implemented and working locally (Google OAuth, voice/text, transcription, TypeSafe System One, usage log).
- Settings split under `src/config/settings/`. Apps live under `src/`. Local `.env` points at `src.config.settings.dev`. The `src/` layout is on `main`.
- Jev calls `https://api.typesafe.ai/v1/systemone` with a TypeSafe console `apikey_`. Sample Google callback path `/src.accounts/google/callback/` is aliased so the existing Cloud client works.
- Local file attachments: timestamped uploads under `media/attachments/`, processed audio under `media/artifacts/`. Linked to the voice/text entry when sent with it; standalone files become their own input.
- Voice-page attach + entries Add-files bugs fixed (PR #4): button opens the picker, empty Stop saves queued files, entries form shows success/error.
- Conferencing app at `/conference/`: one conversation, 240-second segments plus a short final segment, transcripts joined in order. No diary classification.
- Visual shell matches the old Voice Diary chrome (Tailwind, dark, red record button, pulse). `docs/ui-rules.md`. Strings wrapped in `{% trans %}`.
- Entries list hides an attachment whose file is gone or soft-deleted. `media_release` deletes the file and soft-deletes that row. A file-only entry is soft-deleted when it has no remaining files. Voice and text entries stay.
- Entries cards have Delete, Edit, and Copy. Delete soft-deletes the entry and frees attached files. Edit saves `content_text` in a modal. Copy uses the clipboard.

**Not done**

- Interface language (`pt-pt` default, `en`). Interface language is not the backlog item Translation.
- Conference question set and the single classification call after stop.
- Diary prior context still waits for two older rows. File-only uploads can still be sent as prior text. Both changes are decided and not built. Unknown audio duration stays out of prior context.
- Phase two summary (conditions undefined). Phase-three backlog. Service-worker 404 left paused.

**Next**

- Interface language. Conference classification can proceed beside that.

## Commands

- `media_release <path>` (`--json`) — delete a file under `media/`, then soft-delete the row that stored the path. `src/diary/management/commands/media_release.py`
- `entry_list --email <email>` (`--json`) — list active entries for that account. `src/diary/management/commands/entry_list.py`
- `entry_show <id>` (`--email`, `--json`) — print one entry's text. `src/diary/management/commands/entry_show.py`
- `entry_update <id> --text "..."` (`--email`, `--json`) — overwrite entry text. `src/diary/management/commands/entry_update.py`
- `entry_delete <id>` (`--email`, `--json`) — soft-delete an entry and free attached files. No prompt. `src/diary/management/commands/entry_delete.py`
