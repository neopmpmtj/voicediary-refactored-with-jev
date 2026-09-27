import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, delete_entry_by_id


class Command(BaseCommand):
    help = "Soft-delete one diary entry and free its attached files. No prompt."

    def add_arguments(self, parser):
        parser.add_argument("id", help="Entry UUID.")
        parser.add_argument("--email", help="Account email. When set, the entry must belong to that user.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            result = delete_entry_by_id(options["id"], email=options.get("email"))
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(result))
            return
        self.stdout.write(f"id {result['id']}")
        self.stdout.write(f"bytes_freed {result['bytes_freed']}")
        self.stdout.write(f"attachments {' '.join(result['attachments']) or '-'}")
