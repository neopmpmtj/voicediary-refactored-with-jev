import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, update_entry_by_id


class Command(BaseCommand):
    help = "Overwrite the text of one active diary entry."

    def add_arguments(self, parser):
        parser.add_argument("id", help="Entry UUID.")
        parser.add_argument("--text", required=True, help="New content_text.")
        parser.add_argument("--email", help="Account email. When set, the entry must belong to that user.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            item = update_entry_by_id(options["id"], options["text"], email=options.get("email"))
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(item))
            return
        self.stdout.write(item["content_text"])
