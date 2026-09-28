# UI rules

These rules apply to the visual shell and to every screen after it ships. The look and the recording controls are the ones already used by the app this repo replaces. Do not invent a new palette. Do not copy Python, JavaScript, or whole apps out of `sample-old-version-delete-when-finished-using/`. Recreate the design system under `src/`.

The current templates follow this document. New screens do too.

This product has fewer screens than the old app. Missing apps (chat, quotas, billing, lists) are omitted. What exists must still look and behave like the corresponding old screens. Rewrite is on the entries list, not on voice or text input.

## Stack

Django templates, plain JavaScript, and Tailwind via `django-tailwind-cli`. No React and no Vue.

The old app delivered this look with Tailwind. Use that same setup so spacing, the top bar, the dots, the cards, and the record button match. JavaScript stays plain. Pause, resume, stop, and when the pulse starts are still the recorder code.

## Color

Dark only. There is no light mode and no theme picker. Lock `dark` and the green accent on `<html>` so cards, dots, and Save match the old default. The record button stays red even so.

| Role | Value |
|------|--------|
| Background | `hsl(0 0% 5%)` |
| Text | `hsl(0 0% 95%)` |
| Card | `hsl(0 0% 8%)` |
| Border | `hsl(0 0% 18%)` |
| Muted text | `hsl(0 0% 55%)` |
| Accent (dots, cards, Save) | `hsl(142 69% 50%)` |

## Record button

The record control is always red.

- Circle, 72px by 72px.
- Fill `hsl(0 90% 50%)`. Icon white, `hsl(0 0% 100%)`, a microphone when idle.
- Hover, when enabled, scales to `1.05`.
- One button starts, pauses, and resumes. Stop is a separate control that appears while the take is live.
- While recording, the `recording` class runs `pulse-record`: a red ring that expands to 20px and fades, `1.5s` ease-in-out, infinite.

```css
@keyframes pulse-record {
  0% { box-shadow: 0 0 0 0 hsl(0 90% 50% / 0.7); }
  70% { box-shadow: 0 0 0 20px hsl(0 90% 50% / 0); }
  100% { box-shadow: 0 0 0 0 hsl(0 90% 50% / 0); }
}
```

- Paused uses `hsl(0 85% 48%)` and does not pulse. The icon is play.
- If the user prefers reduced motion, the button stays red and still, without the ring.

Recorder behavior otherwise stays as it is: rollover at 240 seconds, microphone interruption, IndexedDB recovery, conference segments.

## Type and layout

- Typeface is Inter.
- The input column is centered, max width about 42rem (`max-w-2xl`).
- A thin sticky top bar sits above the page.
- Voice and text are two dots under that bar. The active mode is the filled accent dot.
- On voice, the left control is Entries (the old Dashboard slot). The right control is Conference (the old Chat slot). Attach sits on the second row with the dots.
- List and profile pages use the dashboard chrome: back to input, page title, `vd-card` rows.
- Sign-in uses the centered auth card.

## Left out until those features exist

- Light mode and the seven accent themes
- Quotas, chat, billing, lists
- The theme picker

## Screens

The shell covers the screens that exist: sign-in, voice, text, entries, conference record, conference list, profile, and Google link-confirm.

## Interface language

Interface language is the next phase after the shell, specified in `docs/project-plan.md`. It is not the backlog item Translation, which is diary content. While the shell is built, wrap every user-facing string in `{% trans %}` so the Portuguese catalog does not require a second pass over the markup.
