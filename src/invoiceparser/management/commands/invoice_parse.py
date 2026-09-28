import json

from django.core.management.base import BaseCommand, CommandError

from src.invoiceparser.errors import InvoiceLookupError
from src.invoiceparser.services import process_invoices_for_email


class Command(BaseCommand):
    help = "Search Gmail for PDF invoices and store finance records."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            payload = process_invoices_for_email(options["email"])
        except InvoiceLookupError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(payload))
            return
        summary = payload.get("summary") or {}
        self.stdout.write(
            "messages={0} pdfs={1} created={2} skipped={3}".format(
                summary.get("messages_found", 0),
                summary.get("pdfs_parsed", 0),
                summary.get("records_created", 0),
                summary.get("records_skipped", 0),
            )
        )
        for err in payload.get("errors") or []:
            self.stdout.write(err)
        if not payload.get("results") and not payload.get("errors"):
            self.stdout.write("no invoices")
