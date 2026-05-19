from django.urls import path

from .views import (
    JournalEntryDetailView,
    JournalEntryListCreateView,
    JournalSearchView,
)

urlpatterns = [
    path("",          JournalEntryListCreateView.as_view(), name="journal_list_create"),
    path("search/",   JournalSearchView.as_view(),          name="journal_search"),
    path("<int:pk>/", JournalEntryDetailView.as_view(),     name="journal_detail"),
]
