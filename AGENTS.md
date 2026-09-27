# Voice Diary (refactored)

This repo is a new Voice Diary implementation. Put new app code under `src/`, outside `sample-old-version-delete-when-finished-using/`.

`sample-old-version-delete-when-finished-using/` is a read-only reference for behavior and constraints. Do not copy its layout or files in as the implementation. Do not edit it unless asked.

Do not commit secrets. Sample env and credential files stay reference-only.

## Session

**Done**

- Phase one input and classify is implemented and working locally (Google OAuth, voice/text, transcription, TypeSafe System One, usage log).
- Settings split under `src/config/settings/`. Apps live under `src/`. Local `.env` points at `src.config.settings.dev`.
- Jev calls `https://api.typesafe.ai/v1/systemone` with a TypeSafe console `apikey_`. Sample Google callback path `/src.accounts/google/callback/` is aliased so the existing Cloud client works.

**Not done**

- Phase two summary (conditions undefined). Phase-three backlog. Service-worker 404 left paused. `src/` move and settings split not committed.

**Next**

- Phase two when summary conditions are chosen. Commit the `src/` layout if wanted.
