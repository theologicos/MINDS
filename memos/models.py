import os
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


def memo_attachment_path(instance, filename):
    return f"memo_attachments/{instance.created_by_id}/{filename}"


class MemoQuerySet(models.QuerySet):
    def visible_to(self, user):
        if user.is_superadmin:
            return self
        if user.is_admin:
            return self.filter(
                models.Q(created_by=user) | models.Q(department=user.department)
            ).distinct()
        return self.filter(recipients__recipient=user).distinct()

    def drafts(self):
        return self.filter(status=Memorandum.Status.DRAFT)

    def sent(self):
        return self.filter(status=Memorandum.Status.SENT)

    def archived(self):
        return self.filter(status=Memorandum.Status.ARCHIVED)


class MemoManager(models.Manager.from_queryset(MemoQuerySet)):
    pass


class Memorandum(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ARCHIVED = "archived", "Archived"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        IMPORTANT = "important", "Important"
        URGENT = "urgent", "Urgent"

    title = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    attachment = models.FileField(upload_to=memo_attachment_path, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_memos")
    department = models.ForeignKey("departments.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="memorandums")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    objects = MemoManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["department", "status"]),
        ]

    def __str__(self):
        return self.title

    MAX_ATTACHMENT_SIZE = 100 * 1024 * 1024

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.attachment and self.attachment.size > self.MAX_ATTACHMENT_SIZE:
            raise ValidationError({"attachment": "Attachment must not exceed 100MB."})

    def mark_sent(self, recipients=None):
        from notifications.services import notify_memo_sent
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at"])
        if recipients:
            MemoRecipient.objects.bulk_create(
                [MemoRecipient(memo=self, recipient=user) for user in recipients],
                ignore_conflicts=True,
            )
            notify_memo_sent(self, recipients)

    def archive(self):
        self.status = self.Status.ARCHIVED
        self.archived_at = timezone.now()
        self.save(update_fields=["status", "archived_at"])

    def get_archive_url(self):
        return reverse("memos:archive", args=[self.pk])

    @property
    def is_overdue_for_archive(self):
        if self.status == self.Status.ARCHIVED:
            return False
        return self.created_at < timezone.now() - timezone.timedelta(days=365)

    @property
    def attachment_filename(self):
        return os.path.basename(self.attachment.name) if self.attachment else None

    @property
    def total_recipients(self):
        return self.recipients.count()

    @property
    def read_count(self):
        return self.recipients.filter(read_at__isnull=False).count()

    @property
    def read_rate(self):
        total = self.total_recipients
        return round((self.read_count / total) * 100) if total else 0


class MemoRecipient(models.Model):
    memo = models.ForeignKey(Memorandum, on_delete=models.CASCADE, related_name="recipients")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_memos")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("memo", "recipient")
        indexes = [models.Index(fields=["recipient", "read_at"])]

    def __str__(self):
        return f"{self.memo.title} → {self.recipient}"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])
