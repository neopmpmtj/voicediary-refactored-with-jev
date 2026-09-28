import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, create_entry_for_email


class Command(BaseCommand):
    help = "Create a text diary entry for a user."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--text", required=True, help="Entry text.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            item = create_entry_for_email(options["email"], options["text"])
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(item))
            return
        self.stdout.write(f"{item['id']} {item['content_text']}")
