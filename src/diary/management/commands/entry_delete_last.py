import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, delete_last_entry_for_email


class Command(BaseCommand):
    help = "Soft-delete the newest active diary entry. Leaves attached files in place."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            result = delete_last_entry_for_email(options["email"])
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(result))
            return
        self.stdout.write(f"id {result['id']}")
