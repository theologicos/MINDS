from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from memos.models import Memorandum
from settings_app.models import SystemSetting


class Command(BaseCommand):
    help = "Archives memorandums older than the configured threshold (default 365 days)."

    def handle(self, *args, **options):
        days = int(SystemSetting.get("archive_threshold_days", "365"))
        threshold = timezone.now() - timedelta(days=days)
        qs = Memorandum.objects.exclude(status=Memorandum.Status.ARCHIVED).filter(created_at__lt=threshold)
        count = qs.count()
        for memo in qs:
            memo.archive()
        self.stdout.write(self.style.SUCCESS(f"Archived {count} memorandum(s) older than {days} days."))
