import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, show_entry


class Command(BaseCommand):
    help = "Show one active diary entry. Agent Copy: stdout is the text."

    def add_arguments(self, parser):
        parser.add_argument("id", help="Entry UUID.")
        parser.add_argument("--email", help="Account email. When set, the entry must belong to that user.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            item = show_entry(options["id"], email=options.get("email"))
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(item))
            return
        self.stdout.write(item["content_text"])
