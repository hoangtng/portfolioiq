"""
Usage: docker compose exec api python manage.py setup_periodic_tasks

Registers Phase 1 recurring tasks in django-celery-beat's DB scheduler:
  - portfolio.fetch_quotes        every 60s
  - portfolio.check_price_alerts  every 60s

Idempotent — safe to re-run.
"""

import json

from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Register Phase 1 periodic tasks in Celery Beat"

    def handle(self, *args, **options):
        every_60s, _ = IntervalSchedule.objects.get_or_create(
            every=60,
            period=IntervalSchedule.SECONDS,
        )

        tasks = [
            ("Fetch stock quotes every 60s", "portfolio.fetch_quotes"),
            ("Check price alerts every 60s", "portfolio.check_price_alerts"),
        ]

        for name, task_path in tasks:
            _, created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "task":     task_path,
                    "interval": every_60s,
                    "args":     json.dumps([]),
                    "enabled":  True,
                },
            )
            status = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"  {status}: {name}"))

        self.stdout.write(self.style.SUCCESS(
            "\nDone. Periodic tasks registered in Django Admin."
        ))
