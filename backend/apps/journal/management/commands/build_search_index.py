"""
Usage:
    docker compose exec api python manage.py build_search_index
    docker compose exec api python manage.py build_search_index --rebuild

Creates the Elasticsearch index mapping and bulk-indexes all existing
JournalEntry rows. Run once after Phase 2 is deployed; after that the
post_save signal keeps the index in sync automatically.

Safe to re-run. Idempotent.
"""

from django.core.management.base import BaseCommand

from apps.journal.documents import JournalEntryDocument
from apps.journal.models import JournalEntry


class Command(BaseCommand):
    help = "Create the Elasticsearch index and bulk-index all journal entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--rebuild",
            action="store_true",
            help="Delete the existing index before recreating",
        )

    def handle(self, *args, **options):
        doc = JournalEntryDocument()

        if options["rebuild"]:
            self.stdout.write("Deleting existing index...")
            try:
                doc._index.delete(ignore=404)
            except Exception as exc:
                self.stderr.write(f"  delete failed: {exc}")

        self.stdout.write("Creating index mapping...")
        # init() is idempotent — creates the index if it doesn't exist.
        doc.init()

        entries = JournalEntry.objects.all()
        total = entries.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No entries to index."))
            self.stdout.write(self.style.SUCCESS(
                "Index is ready — new entries will be indexed automatically."
            ))
            return

        self.stdout.write(f"Indexing {total} entries...")
        indexed, errors = 0, 0
        for entry in entries.iterator():
            try:
                doc.update(entry)
                indexed += 1
            except Exception as exc:
                errors += 1
                self.stdout.write(self.style.WARNING(
                    f"  entry {entry.id}: {exc}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"Done. Indexed {indexed}/{total} ({errors} errors)."
        ))
