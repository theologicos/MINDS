from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from memos.models import Memorandum, MemoRecipient
from notifications.models import Notification
from departments.models import Department


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.can_create_memos():
            context.update(self._admin_context(user))
        else:
            context.update(self._staff_context(user))
        context["recent_activity"] = Notification.objects.for_user(user)[:5]
        return context

    def _admin_context(self, user):
        memos_qs = Memorandum.objects.visible_to(user)
        sent_memos = memos_qs.sent()
        avg_read_rate = (
            sum(m.read_rate for m in sent_memos) // sent_memos.count()
            if sent_memos.exists() else 0
        )
        ctx = {
            "stats": [
                {"label": "Total Memos", "value": memos_qs.count(), "icon": "envelope", "color": "primary"},
                {"label": "Drafts", "value": memos_qs.drafts().count(), "icon": "file-pen", "color": "warning"},
                {"label": "Sent", "value": sent_memos.count(), "icon": "paper-plane", "color": "success"},
                {"label": "Avg. Read Rate", "value": f"{avg_read_rate}%", "icon": "chart-pie", "color": "info"},
            ],
            "recent_memos": memos_qs.exclude(status=Memorandum.Status.DRAFT)[:5],
        }
        if user.is_superadmin:
            ctx["department_count"] = Department.objects.count()
            ctx["archived_count"] = memos_qs.archived().count()
        return ctx

    def _staff_context(self, user):
        my_recipients = MemoRecipient.objects.filter(recipient=user)
        total = my_recipients.count()
        unread = my_recipients.filter(read_at__isnull=True).count()
        recent = Memorandum.objects.filter(recipients__recipient=user).distinct().order_by("-sent_at")[:5]
        read_ids = set(my_recipients.filter(read_at__isnull=False).values_list("memo_id", flat=True))
        for memo in recent:
            memo.is_unread_for_user = memo.id not in read_ids
        return {
            "stats": [
                {"label": "Assigned Memos", "value": total, "icon": "inbox", "color": "primary"},
                {"label": "Unread", "value": unread, "icon": "envelope", "color": "danger"},
                {"label": "Read", "value": total - unread, "icon": "envelope-open", "color": "success"},
            ],
            "recent_memos": recent,
        }
