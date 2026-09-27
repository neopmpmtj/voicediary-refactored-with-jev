import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, entries_for_email


class Command(BaseCommand):
    help = "List active diary entries for a user."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            rows = entries_for_email(options["email"])
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(rows))
            return
        if not rows:
            self.stdout.write("no entries")
            return
        for item in rows:
            self.stdout.write(
                f"{item['id']} {item['item_type']} {item['created_at']} {item['content_text']}"
            )
