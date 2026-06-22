from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from memos.models import Memorandum


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    template_name = "core/search_results.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        results = []

        if len(q) >= 2:  # avoid firing on single keystrokes
            results = (
                Memorandum.objects
                .visible_to(self.request.user)
                .filter(
                    Q(title__icontains=q) | Q(body__icontains=q)
                )
                .select_related("created_by", "created_by__department")
                .prefetch_related("departments")
                .order_by("-created_at")[:50]
            )

        ctx.update({
            "q": q,
            "results": results,
            "result_count": len(results),
            "breadcrumbs": [{"label": f'Search results for "{q}"' if q else "Search"}],
        })
        return ctx
