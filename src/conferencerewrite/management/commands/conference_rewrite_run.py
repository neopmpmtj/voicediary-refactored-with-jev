import json
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from src.conferencerewrite.errors import RewriteError
from src.conferencerewrite.services import rewrite_text


class Command(BaseCommand):
    help = "Rewrite conference text from a file or stdin. Prints the rewritten prose with headings."

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Path to the text to rewrite.")
        parser.add_argument("--model", help="Responses model id from the catalog.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            result = rewrite_text(self._read_text(options.get("file")), model_id=options.get("model"))
        except RewriteError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(result))
            return
        self.stdout.write(result["text"])

    def _read_text(self, path):
        if path:
            try:
                return Path(path).read_text(encoding="utf-8")
            except OSError as exc:
                raise CommandError(f"Cannot read {path}") from exc
        if sys.stdin.isatty():
            raise CommandError("Pass --file or pipe text on stdin")
        return sys.stdin.read()
