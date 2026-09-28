import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, add_attachment_from_path


class Command(BaseCommand):
    help = "Store a local file as an attachment. With --entry, link it; otherwise create a file entry."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Local file to store.")
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--entry", help="Attach to this active entry UUID.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            item = add_attachment_from_path(
                options["email"],
                options["path"],
                entry_id=options.get("entry"),
            )
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(item))
            return
        self.stdout.write(f"{item['id']} {item['content_text']}")
