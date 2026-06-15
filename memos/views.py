from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from core.permissions import AdminOrSuperadminRequiredMixin, MemoOwnerOrSuperadminMixin
from notifications.services import notify_memo_sent, notify_memo_updated
from .forms import MemoForm
from .models import Memorandum, MemoRecipient


class MemoCreateView(LoginRequiredMixin, AdminOrSuperadminRequiredMixin, View):
    template_name = "memos/memo_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form": MemoForm(user=request.user), "title": "Create Memorandum",
            "breadcrumbs": [{"label": "Memorandums", "url": reverse("memos:sent")}, {"label": "Create"}],
        })

    def post(self, request):
        form = MemoForm(request.POST, request.FILES, user=request.user)
        action = request.POST.get("action", "draft")
        if form.is_valid():
            memo = form.save(commit=False)
            memo.created_by = request.user
            if not memo.department_id and request.user.department_id:
                memo.department = request.user.department
            memo.save()
            if action == "send":
                recipients = form.get_recipient_users()
                memo.mark_sent(recipients=recipients)
                messages.success(request, f"Memorandum sent to {len(recipients)} recipient(s).")
                return redirect("memos:sent")
            else:
                messages.success(request, "Memorandum saved as draft.")
                return redirect("memos:drafts")
        return render(request, self.template_name, {
            "form": form, "title": "Create Memorandum",
            "breadcrumbs": [{"label": "Memorandums", "url": reverse("memos:sent")}, {"label": "Create"}],
        })


class MemoEditView(LoginRequiredMixin, AdminOrSuperadminRequiredMixin, MemoOwnerOrSuperadminMixin, View):
    template_name = "memos/memo_form.html"

    def get_object(self):
        return get_object_or_404(Memorandum, pk=self.kwargs["pk"])

    def get(self, request, pk):
        memo = self.get_object()
        return render(request, self.template_name, {
            "form": MemoForm(instance=memo, user=request.user), "memo": memo,
            "title": "Edit Memorandum",
            "breadcrumbs": [{"label": "Drafts", "url": reverse("memos:drafts")}, {"label": "Edit"}],
        })

    def post(self, request, pk):
        memo = self.get_object()
        form = MemoForm(request.POST, request.FILES, instance=memo, user=request.user)
        action = request.POST.get("action", "draft")
        if form.is_valid():
            memo = form.save()
            if action == "send":
                recipients = form.get_recipient_users()
                if memo.status == Memorandum.Status.SENT:
                    existing_ids = set(memo.recipients.values_list("recipient_id", flat=True))
                    new_recipients = [r for r in recipients if r.id not in existing_ids]
                    if new_recipients:
                        MemoRecipient.objects.bulk_create(
                            [MemoRecipient(memo=memo, recipient=u) for u in new_recipients],
                            ignore_conflicts=True,
                        )
                        notify_memo_sent(memo, new_recipients)
                    notify_memo_updated(memo, [r.recipient for r in memo.recipients.select_related("recipient")])
                    messages.success(request, "Memorandum updated and recipients notified.")
                else:
                    memo.mark_sent(recipients=recipients)
                    messages.success(request, f"Memorandum sent to {len(recipients)} recipient(s).")
                return redirect("memos:sent")
            messages.success(request, "Draft updated.")
            return redirect("memos:drafts")
        return render(request, self.template_name, {
            "form": form, "memo": memo, "title": "Edit Memorandum",
            "breadcrumbs": [{"label": "Drafts", "url": reverse("memos:drafts")}, {"label": "Edit"}],
        })


class BaseMemoListView(LoginRequiredMixin, ListView):
    model = Memorandum
    template_name = "memos/memo_list.html"
    context_object_name = "memos"
    paginate_by = 10

    def get_queryset(self):
        qs = Memorandum.objects.visible_to(self.request.user).select_related("created_by", "department")
        qs = self.filter_by_status(qs)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(title__icontains=q)
        return qs

    def filter_by_status(self, qs):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.extra_context_data())
        return context

    def extra_context_data(self):
        return {}


class DraftListView(AdminOrSuperadminRequiredMixin, BaseMemoListView):
    def filter_by_status(self, qs):
        return qs.drafts()

    def extra_context_data(self):
        return {
            "page_title": "Draft Memorandums", "page_subtitle": "Memorandums saved but not yet sent.",
            "list_type": "drafts", "breadcrumbs": [{"label": "Drafts"}],
            "empty_icon": "file-pen", "empty_title": "No drafts",
            "empty_message": "Memos you save as drafts will appear here.",
            "memo_create_url": reverse("memos:create"),
        }


class SentListView(AdminOrSuperadminRequiredMixin, BaseMemoListView):
    def filter_by_status(self, qs):
        return qs.sent()

    def extra_context_data(self):
        return {
            "page_title": "Sent Memorandums", "page_subtitle": "Memorandums distributed to recipients.",
            "list_type": "sent", "breadcrumbs": [{"label": "Sent"}],
            "empty_icon": "paper-plane", "empty_title": "No sent memorandums",
            "empty_message": "Memos you send will appear here.",
            "memo_create_url": reverse("memos:create"),
        }


class ArchivedListView(BaseMemoListView):
    def filter_by_status(self, qs):
        return qs.archived()

    def extra_context_data(self):
        return {
            "page_title": "Archived Memorandums", "page_subtitle": "Memorandums archived manually or automatically.",
            "list_type": "archived", "breadcrumbs": [{"label": "Archived"}],
            "empty_icon": "box-archive", "empty_title": "No archived memorandums",
            "empty_message": "Archived memos will appear here.",
        }


class AssignedListView(BaseMemoListView):
    def get_queryset(self):
        user = self.request.user
        qs = Memorandum.objects.filter(
            recipients__recipient=user, status=Memorandum.Status.SENT
        ).select_related("created_by", "department").distinct().order_by("-sent_at")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(title__icontains=q)
        return qs

    def filter_by_status(self, qs):
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        read_ids = set(MemoRecipient.objects.filter(recipient=user, read_at__isnull=False).values_list("memo_id", flat=True))
        for memo in context["memos"]:
            memo.is_unread_for_user = memo.id not in read_ids
        context.update({
            "page_title": "Assigned to Me", "page_subtitle": "Memorandums distributed to you.",
            "list_type": "assigned", "breadcrumbs": [{"label": "Assigned to Me"}],
            "empty_icon": "inbox", "empty_title": "Nothing assigned yet",
            "empty_message": "Memorandums sent to you will appear here.",
        })
        return context


class MemoDetailView(LoginRequiredMixin, DetailView):
    model = Memorandum
    template_name = "memos/memo_detail.html"
    context_object_name = "memo"

    def get_queryset(self):
        return Memorandum.objects.visible_to(self.request.user).select_related("created_by", "department")

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        memo = self.object
        if not request.user.can_create_memos():
            rec, _ = MemoRecipient.objects.get_or_create(memo=memo, recipient=request.user)
            rec.mark_read()
            request.user.notifications.filter(memo=memo, is_read=False).update(is_read=True)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        memo = self.object
        user = self.request.user
        context["breadcrumbs"] = [{"label": "Memorandums", "url": self._back_url()}, {"label": memo.title}]
        if user.can_create_memos():
            context["recipients_list"] = memo.recipients.select_related("recipient").order_by("-read_at")
        context["can_edit"] = (
            memo.status == Memorandum.Status.DRAFT and
            (user.is_superadmin or memo.created_by_id == user.id)
        )
        context["can_archive"] = (
            (user.is_superadmin or memo.created_by_id == user.id) and
            memo.status != Memorandum.Status.ARCHIVED
        )
        return context

    def _back_url(self):
        memo = self.object
        user = self.request.user
        if not user.can_create_memos():
            return reverse("memos:assigned")
        if memo.status == Memorandum.Status.DRAFT:
            return reverse("memos:drafts")
        if memo.status == Memorandum.Status.ARCHIVED:
            return reverse("memos:archived")
        return reverse("memos:sent")


class MemoArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        memo = get_object_or_404(Memorandum.objects.visible_to(request.user), pk=pk)
        if not (request.user.is_superadmin or memo.created_by_id == request.user.id):
            messages.error(request, "You do not have permission to archive this memorandum.")
            return redirect("memos:detail", pk=memo.pk)
        memo.archive()
        messages.success(request, "Memorandum archived.")
        return redirect("memos:archived")
