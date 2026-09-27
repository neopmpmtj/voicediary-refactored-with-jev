# Voice Diary (refactored)

This repo is a new Voice Diary implementation. Put new app code under `src/`, outside `sample-old-version-delete-when-finished-using/`.

`sample-old-version-delete-when-finished-using/` is a read-only reference for behavior and constraints. Do not copy its layout or files in as the implementation. Do not edit it unless asked.

Do not commit secrets. Sample env and credential files stay reference-only.

## Session

**Done**

- Phase one input and classify is implemented (Google OAuth, voice/text, transcription, Jev, usage log).
- Settings split: `src.config.settings.dev`, `src.config.settings.prod`, `src.config.settings.test`. Apps live under `src/`. Local `.env` points at dev.

**Not done**

- Phase two summary (conditions undefined). Phase-three backlog. Service-worker 404 left paused. Settings split not committed.

**Next**

- Restart runserver on `src.config.settings.dev`. Phase two when summary conditions are chosen.
