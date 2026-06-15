from django.contrib import admin
from .models import Memorandum, MemoRecipient


@admin.register(Memorandum)
class MemorandumAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "created_by", "department", "created_at")
    list_filter = ("status", "priority", "department")
    search_fields = ("title", "body")
    readonly_fields = ("created_at", "updated_at", "sent_at", "archived_at")


@admin.register(MemoRecipient)
class MemoRecipientAdmin(admin.ModelAdmin):
    list_display = ("memo", "recipient", "read_at", "created_at")
    list_filter = ("read_at",)
