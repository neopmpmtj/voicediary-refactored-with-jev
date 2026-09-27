# Project plan

- [x] Phase one — input and classify
- [x] File attachments (local, timestamped, optional link to an input)
- [ ] Conferencing
- [ ] Phase two — summary
- [ ] Phase three — some of the backlog

## Phase one — input and classify

A Google-authenticated user records or types an entry. Voice keeps the current input behavior: swipe between voice and text, pause and resume, microphone interruption, one merged recording, IndexedDB recovery, and automatic restart at `RECORDER_MAX_DURATION` (default 240 seconds). Audio is trimmed, silence is removed, and OpenAI transcribes it in the original language. Durations stored are the original length and the length after silence removal, in seconds. File sizes are not stored.

Jev classifies each entry in one call: intent (freeform, list, follow-up, todo, reschedule), subject (diary, finance, appointment), and two yes/no checks (the user asked for the diary, and this continues the prior entries). Prior entries are included only after two rows exist. The count defaults to 2 (`PRIOR_ENTRY_COUNT`). A prior recording is included only when its duration is known and shorter than `RECORDER_MAX_DURATION`. A missing duration stays out.

Decided, not built yet:

- Prior context starts when one older row exists. The cap stays `PRIOR_ENTRY_COUNT`.
- A file-only upload is not a prior utterance. Attachment filenames on a voice or text entry are their own field. The utterance text stays the transcript or the typed note.

If the intent is follow-up or reschedule, or the subject is appointment, the stored route is calendar. That wins even when the user asked for the diary. The diary answer is still stored.

Usage is logged. Transcription is stored as audio minutes, because the transcription response has no token count. Jev input and output tokens are stored. There is no quota gate and no Stripe charge.

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
