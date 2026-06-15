from notifications.models import Notification
from memos.models import Memorandum


def global_counts(request):
    if not request.user.is_authenticated:
        return {}
    user = request.user
    data = {
        "unread_notif_count": Notification.objects.for_user(user).unread().count(),
        "recent_notifications": Notification.objects.for_user(user).select_related("memo")[:6],
    }
    if user.can_create_memos():
        data["draft_count"] = Memorandum.objects.visible_to(user).drafts().count()
    else:
        data["unread_count"] = user.received_memos.filter(read_at__isnull=True).count()
    return data
