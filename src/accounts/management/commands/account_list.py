import json

from django.core.management.base import BaseCommand

from src.accounts.services import accounts_list


class Command(BaseCommand):
    help = "List accounts. Email and Google-account flag only."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        rows = accounts_list()
        if options["json"]:
            self.stdout.write(json.dumps(rows))
            return
        if not rows:
            self.stdout.write("no accounts")
            return
        for item in rows:
            self.stdout.write(f"{item['email']} {item['is_google_account']}")
