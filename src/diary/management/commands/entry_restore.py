import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, restore_entry_for_email


class Command(BaseCommand):
    help = "Restore a soft-deleted diary entry. Default is the newest deleted row."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--id", help="Entry UUID. Default: newest soft-deleted.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            item = restore_entry_for_email(options["email"], entry_id=options.get("id"))
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(item))
            return
        self.stdout.write(f"{item['id']} {item['content_text']}")
