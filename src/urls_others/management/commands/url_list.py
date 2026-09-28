import argparse
import json

from django.core.management.base import BaseCommand, CommandError

from src.urls_others.models import ReferenceKind
from src.urls_others.services import ReferenceLookupError, references_for_email


def _positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("limit must be a positive integer")
    return number


class Command(BaseCommand):
    help = "List URL and endpoint references for a user."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument(
            "--kind",
            choices=ReferenceKind.values,
            help="Only rows of this kind.",
        )
        parser.add_argument(
            "--limit",
            type=_positive_int,
            help="Maximum rows to print, newest first.",
        )
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            rows = references_for_email(
                options["email"],
                kind=options["kind"],
                limit=options["limit"],
            )
        except ReferenceLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(rows))
            return
        if not rows:
            self.stdout.write("no urls")
            return
        for item in rows:
            self.stdout.write(
                f"{item['id']} {item['kind']} {item['created_at']} {item['value']} {item['note']}"
            )
