# Management commands

Each command is added here when it is created.

## media_release

- **Location:** `src/diary/management/commands/media_release.py`
- **Run:** `python manage.py media_release <path>` (`--json` optional)
- **Does:** delete that file under `media/`, then soft-delete the row that stored the path

## entry_list

- **Location:** `src/diary/management/commands/entry_list.py`
- **Run:** `python manage.py entry_list --email <email>` (`--json` optional)
- **Does:** list active diary entries for that account, newest first

## entry_show

- **Location:** `src/diary/management/commands/entry_show.py`
- **Run:** `python manage.py entry_show <id>` (`--email` optional, `--json` optional)
- **Does:** print one entry's text (agent Copy). `--email` requires the row to belong to that user

## entry_update

- **Location:** `src/diary/management/commands/entry_update.py`
- **Run:** `python manage.py entry_update <id> --text "..."` (`--email` optional, `--json` optional)
- **Does:** overwrite `content_text` in place. Does not reclassify

## entry_create

- **Location:** `src/diary/management/commands/entry_create.py`
- **Run:** `python manage.py entry_create --email <email> --text "..."` (`--json` optional)
- **Does:** create a text diary entry through the same ingest path as the typed form (classify, URL capture). Empty text is rejected

## url_list

- **Location:** `src/urls_others/management/commands/url_list.py`
- **Run:** `python manage.py url_list --email <email>` (`--kind`, `--limit`, `--json` optional)
- **Does:** list URL and endpoint rows for that account, newest first. `--kind url|endpoint` subsets; `--limit N` caps the count
