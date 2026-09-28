import json

from django.core.management.base import BaseCommand, CommandError

from src.finance.errors import FinanceLookupError
from src.finance.services import records_for_email


class Command(BaseCommand):
    help = "List finance records for a user."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--entry", help="Only records on this entry UUID.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            rows = records_for_email(options["email"], entry_id=options.get("entry"))
        except FinanceLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(rows))
            return
        if not rows:
            self.stdout.write("no records")
            return
        for item in rows:
            names = item["record_name"] or "finance"
            self.stdout.write(
                f"{item['id']} {item['status']} {names} {item['error_message']}"
            )
            for money in item["items"]:
                self.stdout.write(
                    f"  {money['type']} {money['amount']} {money['currency']} {money['description']}"
                )
