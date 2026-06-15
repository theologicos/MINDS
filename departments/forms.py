from django import forms
from .models import Department
from accounts.models import User


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Human Resources"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. HR"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Optional department description..."}),
        }

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        qs = Department.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A department with this code already exists.")
        return code

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Department.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A department with this name already exists.")
        return name


class DepartmentMemberForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("first_name", "last_name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control", "size": "10"}),
        label="Department Members",
        help_text="Hold Ctrl/Cmd to select multiple users.",
    )

    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.department = department
        if department:
            self.fields["users"].initial = department.members.values_list("pk", flat=True)
