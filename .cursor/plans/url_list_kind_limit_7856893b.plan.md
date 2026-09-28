---
name: url_list kind limit
overview: Add `--kind` and `--limit` to `url_list` as named flags (not a Docker-style `--filter` mini-language), applied in the service layer so human and `--json` output stay in sync.
todos:
  - id: service-filters
    content: Add kind and limit to references_for_email
    status: completed
  - id: cli-flags
    content: Add --kind and --limit to url_list and pass them to the service
    status: completed
  - id: tests-docs
    content: Tests plus commands.md and AGENTS.md flag lines
    status: completed
isProject: false
---

# url_list: kind and limit

## Advice (why not `--filter`)

`--filter` in industry usually means Docker's repeatable `key=value` pairs. This repo's commands already use one named flag per meaning (`--email`, `--json`). Two named flags are the smaller, clearer change:

- `--kind url` or `--kind endpoint` — subset
- `--limit 20` — cap, newest first (the list is already ordered that way)

No default cap. Omitting `--limit` still prints everything, so `--json` does not hide rows from agents. Invalid `--kind` is an argparse error (`choices`). `--limit` must be a positive integer.

## Code

Filtering stays in [`src/urls_others/services.py`](src/urls_others/services.py), not in the command (same layering as today).

Extend `references_for_email(email, *, kind=None, limit=None)`:

- After the user lookup, `filter(user=user)` then `order_by("-created_at")`
- If `kind` is set, also `filter(kind=kind)`
- If `limit` is set, `[:limit]`

[`src/urls_others/management/commands/url_list.py`](src/urls_others/management/commands/url_list.py) adds:

```text
--kind {url,endpoint}
--limit N
```

and passes both into the service. `--json` is unchanged: same subset, JSON list.

Empty result stays `no urls` (human) or `[]` (JSON).

## Docs and tests

- [`docs/commands.md`](docs/commands.md) and [`AGENTS.md`](AGENTS.md): one line each with the new flags
- Integration tests next to [`src/urls_others/tests/test_url_list.py`](src/urls_others/tests/test_url_list.py): `--kind url` omits endpoints; `--limit 1` returns the newest row only; both flags together; bad `--kind` errors
