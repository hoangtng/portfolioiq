"""
Usage:
    docker compose exec api python manage.py setup_analytics_tasks

Registers the daily snapshot task in django-celery-beat.
Idempotent — re-running updates the existing schedule.
"""

import json

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Register Phase 3 analytics periodic task in Celery Beat"

    def handle(self, *args, **options):
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="21",
            day_of_week="1-5",
            day_of_month="*",
            month_of_year="*",
            timezone="UTC",
        )

        _, created = PeriodicTask.objects.update_or_create(
            name="Take daily portfolio snapshot (Mon-Fri 21:00 UTC)",
            defaults={
                "task":    "analytics.take_portfolio_snapshot",
                "crontab": schedule,
                "args":    json.dumps([]),
                "enabled": True,
            },
        )

        status = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(
            f"  {status}: daily portfolio snapshot (Mon-Fri 21:00 UTC)"
        ))
        self.stdout.write(self.style.SUCCESS(
            "\nDone. Edit at /admin/django_celery_beat/periodictask/."
        ))
