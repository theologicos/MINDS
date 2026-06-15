from django import forms
from django.core.exceptions import ValidationError
from .models import Memorandum
from accounts.models import User
from departments.models import Department


class MemoForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control", "size": "8"}),
        help_text="Select individual recipients (hold Ctrl/Cmd to select multiple).",
    )

    class Meta:
        model = Memorandum
        fields = ["title", "body", "priority", "attachment", "department", "recipients"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter memorandum title"}),
            "body": forms.Textarea(attrs={"class": "form-control", "placeholder": "Write the memorandum content...", "rows": 10}),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-control"}),
            "attachment": forms.FileInput(attrs={"class": "hidden"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["department"].required = False
        self.fields["department"].empty_label = "No department (organization-wide)"
        if self.user and self.user.is_admin:
            self.fields["department"].queryset = Department.objects.filter(id=self.user.department_id)
            self.fields["department"].initial = self.user.department_id
            self.fields["recipients"].queryset = User.objects.filter(is_active=True, department=self.user.department)

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if attachment and attachment.size > Memorandum.MAX_ATTACHMENT_SIZE:
            raise ValidationError("Attachment must not exceed 100MB.")
        return attachment

    def clean(self):
        cleaned = super().clean()
        action = self.data.get("action")
        if action == "send" and not cleaned.get("recipients") and not cleaned.get("department"):
            raise ValidationError("Select at least one recipient or a department before sending.")
        return cleaned

    def get_recipient_users(self):
        recipients = set(self.cleaned_data.get("recipients") or [])
        department = self.cleaned_data.get("department")
        if department:
            recipients.update(department.members.filter(is_active=True))
        if self.user:
            recipients.discard(self.user)
        return list(recipients)
