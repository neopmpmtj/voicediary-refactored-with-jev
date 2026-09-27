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

**Not done**

- Conference question set and the single classification call after stop.
- Diary prior context still waits for two older rows. File-only uploads can still be sent as prior text. Both changes are decided and not built. Unknown audio duration stays out of prior context.
- Phase two summary (conditions undefined). Phase-three backlog. Service-worker 404 left paused.

**Next**

- Define conference classification questions, then classify the joined transcript after stop.
