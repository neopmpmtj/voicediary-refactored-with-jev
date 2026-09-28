import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, attachments_for_email


class Command(BaseCommand):
    help = "List active attachments for a user."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--entry", help="Only attachments on this entry UUID.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            rows = attachments_for_email(options["email"], entry_id=options.get("entry"))
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(rows))
            return
        if not rows:
            self.stdout.write("no attachments")
            return
        for item in rows:
            self.stdout.write(
                f"{item['id']} {item['entry_id']} {item['original_filename']} {item['relative_path']}"
            )
