---
name: Sync missing files
overview: A CLI command takes a file path, deletes that file to free space, then soft-deletes the database row that stored the path. The entries page only hides missing or soft-deleted files and does not write.
todos:
  - id: soft-delete-fields
    content: Add is_deleted and deleted_at on Entry and Attachment, with a migration
    status: completed
  - id: release-service
    content: Add release_file(path) in services.py and remove the hard deletes from list_entries
    status: completed
  - id: cli
    content: Add media_release management command that takes a path and supports --json
    status: completed
  - id: commands-doc
    content: Create docs/commands.md and list media_release with its path in the codebase
    status: completed
  - id: tests
    content: Replace the hard-delete tests with path-based soft-delete cases and run pytest
    status: completed
isProject: false
---

# Release a file by path, then soft-delete its row

The command is for freeing disk space. Audio will be the large files later. The command exists now so it is there when a recording needs to go.

There is still no delete function in this app. The draft in `list_entries` hard-deletes with Django `.delete()`. Remove that. Loading `/entries/` stays read-only: it hides an attachment whose file is missing or whose row is soft-deleted, and it hides a soft-deleted file-only entry. Voice and text entries stay on the page.

## Command

The command file is [src/diary/management/commands/media_release.py](src/diary/management/commands/media_release.py). `src.diary` is in `INSTALLED_APPS`, so `manage.py` picks it up from there. `management/` and `commands/` need their `__init__.py` files. There is no commands package in this repo yet.

`python manage.py media_release <path>`

`<path>` is one file, absolute or relative to the project. It must resolve inside `MEDIA_ROOT`. A directory is refused. A path outside `media/` is refused, and nothing is deleted.

Then, in order:

1. If the file is there, delete it and count the bytes freed.
2. If it is already gone, continue. The space is already free.
3. Soft-delete the row that stored that path. The row stays, with `is_deleted=True` and `deleted_at` set.

`--json` prints the path, bytes freed, and the ids soft-deleted. Without it, the same facts as plain lines. The command calls `release_file` in [src/diary/services.py](src/diary/services.py) only.

Register it in [AGENTS.md](AGENTS.md): purpose, the path argument, and `--json`.

## Command inventory

Create [docs/commands.md](docs/commands.md) when `media_release` is added. It is the list of management commands in this repo. Each new command is added to that file at the time it is created.

The first entry:

- Command: `media_release`
- Location: `src/diary/management/commands/media_release.py`
- Run: `python manage.py media_release <path>` (`--json` optional)
- Does: delete that file under `media/`, then soft-delete the row that stored the path

## What the path matches

- [Attachment.relative_path](src/diary/models.py) matches today. That attachment is soft-deleted. The voice or text entry stays, including its transcript and usage log.
- If that was a file-only entry and no active attachment remains, the entry is soft-deleted too. The row and any usage log stay.
- A conference segment stores `relative_path` and `processed_relative_path` in [src/conference/models.py](src/conference/models.py). The same command soft-deletes that segment only when the path matches. The conference row and its joined transcript stay.
- A diary recording under `media/recordings/` or `media/artifacts/` is not stored on `Entry`. The command can delete that file. It cannot soft-delete the diary entry, because there is no path to match. The transcript stays. A later path column can use this same command.

Restoring the file does not clear `is_deleted`.

## Model

One migration. On `Entry`, `Attachment`, and conference `Segment`:

- `is_deleted = BooleanField(default=False)`
- `deleted_at = DateTimeField(null=True, blank=True)`

Existing rows stay active. No custom manager, so other queries keep seeing every row. `list_entries` and the conference list filter `is_deleted=False` themselves. `_classify` adds `is_deleted=False` so a soft-deleted file-only entry is not used as prior context.

## Tests

Replace the hard-delete cases in [src/diary/tests/test_attachment_views.py](src/diary/tests/test_attachment_views.py). The command test is `integration` because it uses `call_command`.

- `media_release` on an attachment path deletes the file, sets `is_deleted` on that attachment, and leaves the text entry.
- The same command on a file-only entry's path soft-deletes the entry as well. The row still exists.
- A path outside `MEDIA_ROOT` deletes nothing and soft-deletes nothing.
- `/entries/` does not show the released filename.
