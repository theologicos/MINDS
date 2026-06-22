from django.urls import path
from .views import GlobalSearchView

app_name = "core"

urlpatterns = [
    path("search/", GlobalSearchView.as_view(), name="search"),
]
