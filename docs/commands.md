# Management commands

Each command is added here when it is created.

## media_release

- **Location:** `src/diary/management/commands/media_release.py`
- **Run:** `python manage.py media_release <path>` (`--json` optional)
- **Does:** delete that file under `media/`, then soft-delete the row that stored the path

## account_list

- **Location:** `src/accounts/management/commands/account_list.py`
- **Run:** `python manage.py account_list` (`--json` optional)
- **Does:** list accounts, email and Google-account flag only. Does not print tokens

## entry_list

- **Location:** `src/diary/management/commands/entry_list.py`
- **Run:** `python manage.py entry_list --email <email>` (`--q`, `--intent`, `--subject`, `--route`, `--item-type`, `--limit`, `--json` optional)
- **Does:** list active diary entries for that account, newest first. `--q` matches `content_text`. Filters and `--limit` cap the list

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

## entry_delete

- **Location:** `src/diary/management/commands/entry_delete.py`
- **Run:** `python manage.py entry_delete <id>` (`--email` optional, `--json` optional)
- **Does:** soft-delete an entry and free attached files. No prompt

## entry_delete_last

- **Location:** `src/diary/management/commands/entry_delete_last.py`
- **Run:** `python manage.py entry_delete_last --email <email>` (`--json` optional)
- **Does:** soft-delete the newest active diary entry. Leaves attached files in place so restore can bring them back

## entry_restore

- **Location:** `src/diary/management/commands/entry_restore.py`
- **Run:** `python manage.py entry_restore --email <email>` (`--id` optional, `--json` optional)
- **Does:** clear soft-delete on an entry. Default is the newest deleted row. `--id` restores that row when it belongs to the account and is deleted. Does not recreate files already freed by `entry_delete`

## entry_audio

- **Location:** `src/diary/management/commands/entry_audio.py`
- **Run:** `python manage.py entry_audio <path> --email <email>` (`--json` optional)
- **Does:** ingest one local audio file through the diary recorder path (silence removal, transcription, classification). One file becomes one audio entry. It is not split at 240 seconds. It is not `attachment_add`

## attachment_list

- **Location:** `src/diary/management/commands/attachment_list.py`
- **Run:** `python manage.py attachment_list --email <email>` (`--entry`, `--json` optional)
- **Does:** list active attachments, including `relative_path` for `media_release`. `--entry` subsets to one entry

## attachment_add

- **Location:** `src/diary/management/commands/attachment_add.py`
- **Run:** `python manage.py attachment_add <path> --email <email>` (`--entry`, `--json` optional)
- **Does:** store a local file. With `--entry`, attach it to that active entry. Without, create a file entry. Does not transcribe or classify

## usage_list

- **Location:** `src/diary/management/commands/usage_list.py`
- **Run:** `python manage.py usage_list --email <email>` (`--entry`, `--limit`, `--json` optional)
- **Does:** list usage log rows for that account, newest first

## conference_list

- **Location:** `src/conference/management/commands/conference_list.py`
- **Run:** `python manage.py conference_list --email <email>` (`--json` optional)
- **Does:** list conferences for that account. Id, status, times, duration, segment count. No transcript

## conference_show

- **Location:** `src/conference/management/commands/conference_show.py`
- **Run:** `python manage.py conference_show <id> --email <email>` (`--json` optional)
- **Does:** print the joined transcript and segments in sequence order

## url_list

- **Location:** `src/urls_others/management/commands/url_list.py`
- **Run:** `python manage.py url_list --email <email>` (`--kind`, `--limit`, `--json` optional)
- **Does:** list URL and endpoint rows for that account, newest first. `--kind url|endpoint` subsets; `--limit N` caps the count. Omits a row whose diary entry is soft-deleted

## rewrite_run

- **Location:** `src/textrewrite/management/commands/rewrite_run.py`
- **Run:** `python manage.py rewrite_run` (`--file`, `--model`, `--style`, `--json` optional)
- **Does:** rewrite text from `--file` or stdin. `--style` is `grammar` (default), `professional`, `casual`, `llm-friendly`, `story`, or `fairy-tale`. Prints the rewritten prose. `--json` adds model, style, and token counts. Does not store the source or the rewrite

## conference_rewrite_run

- **Location:** `src/conferencerewrite/management/commands/conference_rewrite_run.py`
- **Run:** `python manage.py conference_rewrite_run` (`--file`, `--model`, `--json` optional)
- **Does:** rewrite conference text from `--file` or stdin. Prints the rewritten prose with headings. `--json` adds model and token counts. Does not store the source or the rewrite
