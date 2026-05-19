"""
Celery configuration for PortfolioIQ application.
This module sets up allowing us to define and run asynchronous background tasks (get live prices data).
"""

import os
from celery import Celery

# Sets up Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery ("portfolioiq")

# Read Celery config from Django settings, looking for CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-find tasks.py files in all installed apps
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Ping task — call from `make shell` to verify Celery is alive."""
    print(f"Celery is alive: {self.request!r}")