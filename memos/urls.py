from django.urls import path
from . import views

app_name = "memos"

urlpatterns = [
    path("create/", views.MemoCreateView.as_view(), name="create"),
    path("drafts/", views.DraftListView.as_view(), name="drafts"),
    path("sent/", views.SentListView.as_view(), name="sent"),
    path("archived/", views.ArchivedListView.as_view(), name="archived"),
    path("assigned/", views.AssignedListView.as_view(), name="assigned"),
    path("<int:pk>/", views.MemoDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.MemoEditView.as_view(), name="edit"),
    path("<int:pk>/archive/", views.MemoArchiveView.as_view(), name="archive"),
]
