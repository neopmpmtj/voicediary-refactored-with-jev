# Project plan

- [x] Phase one — input and classify
- [ ] Phase two — summary
- [ ] Phase three — some of the backlog

## Phase one — input and classify

A Google-authenticated user records or types an entry. Voice keeps the current input behavior: swipe between voice and text, pause and resume, microphone interruption, one merged recording, IndexedDB recovery, and automatic restart at `RECORDER_MAX_DURATION` (default 240 seconds). Audio is trimmed, silence is removed, and OpenAI transcribes it in the original language. Durations stored are the original length and the length after silence removal, in seconds. File sizes are not stored.

Jev classifies each entry in one call: intent (freeform, list, follow-up, todo, reschedule), subject (diary, finance, appointment), and two yes/no checks (the user asked for the diary, and this continues the prior entries). Prior entries are included only after two rows exist. The count defaults to 2 (`PRIOR_ENTRY_COUNT`). A prior recording is included only when it is shorter than `RECORDER_MAX_DURATION`.

If the intent is follow-up or reschedule, or the subject is appointment, the stored route is calendar. That wins even when the user asked for the diary. The diary answer is still stored.

Usage is logged. Transcription is stored as audio minutes, because the transcription response has no token count. Jev input and output tokens are stored. There is no quota gate and no Stripe charge.

## Phase two — summary

After a phase-one entry is stored and classified. Run only when conditions are met. Those conditions are not defined yet. The summarizer reports input and output tokens, written to the same usage log.

## Phase three — some of the backlog

Phase three takes some of the items below, not all of them. Which ones is decided when that phase starts.

### Backlog

- Translation
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
