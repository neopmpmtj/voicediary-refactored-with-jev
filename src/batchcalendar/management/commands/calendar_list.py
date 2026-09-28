import json

from django.core.management.base import BaseCommand, CommandError

from src.batchcalendar.errors import CalendarLookupError
from src.batchcalendar.services import bookings_for_email


class Command(BaseCommand):
    help = "List calendar bookings for a user."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--entry", help="Only bookings on this entry UUID.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            rows = bookings_for_email(options["email"], entry_id=options.get("entry"))
        except CalendarLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(rows))
            return
        if not rows:
            self.stdout.write("no bookings")
            return
        for item in rows:
            self.stdout.write(
                f"{item['id']} {item['status']} {item['summary']} {item['start']} {item['problem']}"
            )
