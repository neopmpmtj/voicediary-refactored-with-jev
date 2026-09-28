import json

from django.core.management.base import BaseCommand, CommandError

from src.conference.services import ConferenceLookupError, show_conference_for_email


class Command(BaseCommand):
    help = "Show one conference and its segments in sequence order."

    def add_arguments(self, parser):
        parser.add_argument("id", help="Conference UUID.")
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            item = show_conference_for_email(options["id"], options["email"])
        except ConferenceLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(item))
            return
        self.stdout.write(item["content_text"])
