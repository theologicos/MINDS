from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from core.permissions import SuperadminRequiredMixin
from .forms import DepartmentForm, DepartmentMemberForm
from .models import Department


class DepartmentListView(LoginRequiredMixin, SuperadminRequiredMixin, ListView):
    model = Department
    template_name = "departments/department_list.html"
    context_object_name = "departments"
    paginate_by = 15

    def get_queryset(self):
        qs = Department.objects.all()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q)
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import User
        context.update({
            "page_title": "Departments",
            "page_subtitle": "Manage organizational departments and their members.",
            "breadcrumbs": [{"label": "Departments"}],
            "total_departments": Department.objects.count(),
            "total_members": User.objects.filter(department__isnull=False, is_active=True).count(),
        })
        return context


class DepartmentCreateView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "departments/department_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form": DepartmentForm(),
            "title": "Create Department",
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": "Create"},
            ],
        })

    def post(self, request):
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            messages.success(request, f"Department '{dept.name}' created successfully.")
            return redirect("departments:detail", pk=dept.pk)
        return render(request, self.template_name, {
            "form": form, "title": "Create Department",
            "breadcrumbs": [{"label": "Departments", "url": reverse("departments:list")}, {"label": "Create"}],
        })


class DepartmentDetailView(LoginRequiredMixin, SuperadminRequiredMixin, DetailView):
    model = Department
    template_name = "departments/department_detail.html"
    context_object_name = "department"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dept = self.object
        members = dept.members.filter(is_active=True).order_by("first_name", "last_name")
        context.update({
            "breadcrumbs": [{"label": "Departments", "url": reverse("departments:list")}, {"label": dept.name}],
            "members": members,
            "recent_memos": dept.memorandums.select_related("created_by").order_by("-created_at")[:5],
            "member_count": members.count(),
            "memo_count": dept.memorandums.count(),
            "sent_memo_count": dept.memorandums.filter(status="sent").count(),
        })
        return context


class DepartmentEditView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "departments/department_form.html"

    def get(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        return render(request, self.template_name, {
            "form": DepartmentForm(instance=dept), "department": dept,
            "title": f"Edit Department — {dept.name}",
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": dept.name, "url": reverse("departments:detail", args=[dept.pk])},
                {"label": "Edit"},
            ],
        })

    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            dept = form.save()
            messages.success(request, f"Department '{dept.name}' updated.")
            return redirect("departments:detail", pk=dept.pk)
        return render(request, self.template_name, {
            "form": form, "department": dept, "title": f"Edit Department — {dept.name}",
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": dept.name, "url": reverse("departments:detail", args=[dept.pk])},
                {"label": "Edit"},
            ],
        })


class DepartmentMembersView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "departments/department_members.html"

    def get(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        return render(request, self.template_name, {
            "form": DepartmentMemberForm(department=dept), "department": dept,
            "current_members": dept.members.filter(is_active=True).order_by("first_name"),
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": dept.name, "url": reverse("departments:detail", args=[dept.pk])},
                {"label": "Manage Members"},
            ],
        })

    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        form = DepartmentMemberForm(request.POST, department=dept)
        if form.is_valid():
            selected_users = form.cleaned_data["users"]
            with transaction.atomic():
                dept.members.update(department=None)
                selected_users.update(department=dept)
            messages.success(request, f"Department members updated. {selected_users.count()} member(s) assigned.")
            return redirect("departments:detail", pk=dept.pk)
        return render(request, self.template_name, {
            "form": form, "department": dept,
            "current_members": dept.members.filter(is_active=True).order_by("first_name"),
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": dept.name, "url": reverse("departments:detail", args=[dept.pk])},
                {"label": "Manage Members"},
            ],
        })


class DepartmentDeleteView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        if dept.members.exists():
            messages.error(request, f"Cannot delete '{dept.name}' — it still has {dept.member_count} member(s). Reassign members first.")
            return redirect("departments:detail", pk=dept.pk)
        name = dept.name
        dept.delete()
        messages.success(request, f"Department '{name}' deleted.")
        return redirect("departments:list")
