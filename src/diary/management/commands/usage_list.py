import argparse
import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, usage_for_email


def _positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("limit must be a positive integer")
    return number


class Command(BaseCommand):
    help = "List usage log rows for a user."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--entry", help="Only rows for this entry UUID.")
        parser.add_argument(
            "--limit",
            type=_positive_int,
            help="Maximum rows to print, newest first.",
        )
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            rows = usage_for_email(
                options["email"],
                entry_id=options.get("entry"),
                limit=options["limit"],
            )
        except EntryLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(rows))
            return
        if not rows:
            self.stdout.write("no usage")
            return
        for item in rows:
            self.stdout.write(
                f"{item['created_at']} {item['service']} {item['usage_type']} {item['amount']} {item['entry_id']}"
            )
