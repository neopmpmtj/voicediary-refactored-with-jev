import json
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from src.textrewrite.config import DEFAULT_STYLE, list_styles
from src.textrewrite.errors import RewriteError
from src.textrewrite.services import rewrite_text


class Command(BaseCommand):
    help = "Rewrite text from a file or stdin. Prints the rewritten prose."

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Path to the text to rewrite.")
        parser.add_argument("--model", help="Responses model id from the catalog.")
        parser.add_argument(
            "--style",
            choices=[item["id"] for item in list_styles()],
            default=DEFAULT_STYLE,
            help="Rewrite style. Default grammar.",
        )
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            result = rewrite_text(
                self._read_text(options.get("file")),
                model_id=options.get("model"),
                style=options.get("style"),
            )
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
