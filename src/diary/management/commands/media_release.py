import json

from django.core.management.base import BaseCommand, CommandError

from src.diary.services import MediaReleaseError, release_file


class Command(BaseCommand):
    help = "Delete a file under media/ and soft-delete the row that stored the path."

    def add_arguments(self, parser):
        parser.add_argument("path", help="File under MEDIA_ROOT to delete.")
        parser.add_argument("--json", action="store_true", help="Print the result as JSON.")

    def handle(self, *args, **options):
        try:
            result = release_file(options["path"])
        except MediaReleaseError as exc:
            raise CommandError(str(exc)) from exc
        if options["json"]:
            self.stdout.write(json.dumps(result))
            return
        self.stdout.write(f"path {result['path']}")
        self.stdout.write(f"bytes_freed {result['bytes_freed']}")
        self.stdout.write(f"attachments {' '.join(result['attachments']) or '-'}")
        self.stdout.write(f"entries {' '.join(result['entries']) or '-'}")
        self.stdout.write(f"segments {' '.join(result['segments']) or '-'}")
