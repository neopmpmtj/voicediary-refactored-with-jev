---
name: UI rules and language
overview: Write a docs rule that locks the old app’s black background, red record button, and recording pulse for every screen, and schedule English/Portuguese interface language as the phase right after that shell — not before it, and not as the backlog “Translation” item.
todos:
  - id: write-ui-rules
    content: Add docs/ui-rules.md with the locked palette, record-button states, type, layout, and what is intentionally left out
    status: completed
  - id: update-project-plan
    content: Add Visual shell and Interface language to docs/project-plan.md, separate from content Translation
    status: completed
isProject: false
---

# UI rules and interface language

The look is already decided by the app this repo replaces. This pass writes that down and sequences the work. It does not restyle templates yet, and it does not copy files out of `sample-old-version-delete-when-finished-using/`.

## Advice

Do the visual shell before interface language. The live screens ([src/diary/templates/base.html](src/diary/templates/base.html), [src/diary/static/diary/diary.css](src/diary/static/diary/diary.css)) are still the temporary cream page (Georgia, `#f6f4ef`). Translating those strings now means translating them again when the shell changes.

While the shell is built, wrap every user-facing string in `{% trans %}`. That is the cheap part. The Portuguese catalog, the language switch, and `LANGUAGE_CODE = pt-pt` come in the next short phase, before any new pages, so later screens are born bilingual.

Keep this separate from the phase-three backlog item **Translation**. That item is translating diary content. Interface language is the chrome: buttons, errors, empty states.

## What the document will lock

New file: [docs/ui-rules.md](docs/ui-rules.md). It is the constraint for the shell and for every screen after it ships.

Taken from the old design system ([sample-old-version-delete-when-finished-using/src/theme/static/src/css/input.css](sample-old-version-delete-when-finished-using/src/theme/static/src/css/input.css) and [tailwind.config.js](sample-old-version-delete-when-finished-using/src/theme/static/src/tailwind.config.js)), not reinvented:

- Background near-black `hsl(0 0% 5%)`, text `hsl(0 0% 95%)`, cards a step lighter `hsl(0 0% 8%)`, borders `hsl(0 0% 18%)`.
- Record control is always red `hsl(0 90% 50%)`, 72px circle, white microphone icon. Hover grows it slightly. Class `recording` runs `pulse-record` (red ring expanding to 20px over 1.5s). Paused is a slightly darker red `hsl(0 85% 48%)` and does not pulse.
- Type is Inter. Input column is centered, max about 42rem. Voice and text are two dots under a thin top bar.
- Django templates and plain JavaScript stay. No Tailwind build and no React. The old app used Tailwind only as the delivery of these tokens; the tokens are the rule, the class names are not.

Left out on purpose, because this product does not have those features yet: light mode, the seven accent themes (old default accent was green), rewrite, quotas, chat, and the theme picker. The record button stays red even if an accent returns later.

Screens the shell will cover when that phase starts: sign-in, voice, text, entries, conference record, conference list, profile.

## Project plan

Update [docs/project-plan.md](docs/project-plan.md):

- **Visual shell** — next UI phase. Apply the rules above to the screens that exist. Recorder behavior in [src/diary/static/diary/js/voice_page.js](src/diary/static/diary/js/voice_page.js) and [src/conference/static/conference/js/conference_page.js](src/conference/static/conference/js/conference_page.js) stays; only the control’s look and the page chrome change.
- **Interface language** — immediately after the shell. `pt-pt` and `en`, default `pt-pt` (same as the old app in `utter_it/settings/base.py`). `LocaleMiddleware`, `LOCALE_PATHS`, user preference, and a language control. English strings in code are the message ids; Portuguese is the catalog.
- Conference classification stays the backend next item. It does not wait on the shell, and new UI is not designed in the cream layout.
