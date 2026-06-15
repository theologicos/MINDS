import django.db.models.deletion
import memos.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("departments", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Memorandum",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("status", models.CharField(
                    choices=[("draft", "Draft"), ("sent", "Sent"), ("archived", "Archived")],
                    default="draft", max_length=20,
                )),
                ("priority", models.CharField(
                    choices=[("normal", "Normal"), ("important", "Important"), ("urgent", "Urgent")],
                    default="normal", max_length=20,
                )),
                ("attachment", models.FileField(blank=True, null=True, upload_to=memos.models.memo_attachment_path)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="created_memos",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("department", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="memorandums",
                    to="departments.department",
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MemoRecipient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("memo", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="recipients",
                    to="memos.memorandum",
                )),
                ("recipient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="received_memos",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.AddIndex(
            model_name="memorandum",
            index=models.Index(fields=["status", "created_at"], name="memos_memor_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="memorandum",
            index=models.Index(fields=["department", "status"], name="memos_memor_dept_status_idx"),
        ),
        migrations.AddIndex(
            model_name="memorecipient",
            index=models.Index(fields=["recipient", "read_at"], name="memos_memor_recip_read_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="memorecipient",
            unique_together={("memo", "recipient")},
        ),
    ]
