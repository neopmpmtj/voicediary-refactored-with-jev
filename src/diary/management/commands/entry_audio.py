import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import EntryLookupError, create_audio_entry_from_path
from src.diary.transcription import TranscriptionError


class Command(BaseCommand):
    help = "Ingest one local audio file through the diary recorder path."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Local audio file.")
        parser.add_argument("--email", required=True, help="Account email.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            item = create_audio_entry_from_path(options["email"], options["path"])
        except (EntryLookupError, TranscriptionError) as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(item))
            return
        self.stdout.write(f"{item['id']} {item['content_text']}")
