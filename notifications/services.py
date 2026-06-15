from .models import Notification


def notify_memo_sent(memo, recipients):
    Notification.objects.bulk_create([
        Notification(user=user, memo=memo, message=f"New memorandum: {memo.title}")
        for user in recipients
    ])


def notify_memo_updated(memo, recipients, message=None):
    message = message or f"Memorandum updated: {memo.title}"
    Notification.objects.bulk_create([
        Notification(user=user, memo=memo, message=message)
        for user in recipients
    ])
