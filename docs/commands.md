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

## entry_delete

- **Location:** `src/diary/management/commands/entry_delete.py`
- **Run:** `python manage.py entry_delete <id>` (`--email` optional, `--json` optional)
- **Does:** soft-delete the entry and its attachments, and delete attached files. No prompt
