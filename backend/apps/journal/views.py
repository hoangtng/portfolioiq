"""
Journal views.

  GET  /api/v1/journal/                — list (paginated)
  POST /api/v1/journal/                — create new entry
  GET  /api/v1/journal/{id}/           — retrieve
  PATCH /api/v1/journal/{id}/          — edit
  DELETE /api/v1/journal/{id}/         — remove (also removes from ES)
  GET  /api/v1/journal/search/         — full-text search via Elasticsearch
"""

from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import JournalEntry
from .serializers import (
    JournalEntryCreateSerializer,
    JournalEntrySerializer,
    JournalSearchResultSerializer,
)
from .services import JournalSearchService


# ─── CRUD ─────────────────────────────────────────────────────

class JournalEntryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/journal/        list user's entries (newest first)
    POST /api/v1/journal/        create a new entry

    Query params for GET:
      ?ticker=PLTR     filter by ticker
      ?tag=earnings    filter by tag
      ?ai=true|false   filter by ai_generated
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return (
            JournalEntryCreateSerializer
            if self.request.method == "POST"
            else JournalEntrySerializer
        )

    def get_queryset(self):
        qs = JournalEntry.objects.filter(user=self.request.user)

        ticker = self.request.query_params.get("ticker")
        if ticker:
            qs = qs.filter(ticker=ticker.upper())

        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__contains=[tag.lower()])

        ai = self.request.query_params.get("ai")
        if ai is not None:
            qs = qs.filter(ai_generated=(ai.lower() == "true"))

        return qs

    def perform_create(self, serializer):
        # Pin ai_generated=False on user-created entries. The AI Celery
        # task creates AI-flagged entries directly via the ORM, bypassing
        # this serializer, so this can never block legitimate AI saves.
        serializer.save(user=self.request.user, ai_generated=False)


class JournalEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE — single entry. DELETE also removes from ES."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = JournalEntrySerializer

    def get_queryset(self):
        # Filter by user so unauthorized access returns 404, not 403.
        return JournalEntry.objects.filter(user=self.request.user)


# ─── Search ───────────────────────────────────────────────────

class JournalSearchView(APIView):
    """
    GET /api/v1/journal/search/

    Query params:
        q          full-text query (title boosted 2×)
        ticker     exact-match filter
        tag        exact-match filter — repeat for multi-tag (?tag=a&tag=b)
        from_date  ISO date, inclusive lower bound on created_at
        to_date    ISO date, inclusive upper bound
        ai         "true" | "false" — filter by ai_generated
        sort       "relevance" (default) | "date_desc" | "date_asc"
        page       page number (1-indexed)
        page_size  results per page (default 20, max 50)

    Response:
        {
            "total":     int,
            "page":      int,
            "page_size": int,
            "results":   [<JournalSearchResult>, ...]
        }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        params = request.query_params

        # Bound page_size — prevents clients from requesting a huge page.
        page_size = min(int(params.get("page_size", 20)), 50)
        page      = max(int(params.get("page", 1)), 1)

        # Parse the optional ai flag into True / False / None
        ai_param = params.get("ai")
        ai_generated = None
        if ai_param is not None:
            ai_generated = ai_param.lower() == "true"

        service = JournalSearchService(request.user)
        result = service.search(
            query        = params.get("q", ""),
            ticker       = params.get("ticker", ""),
            tags         = params.getlist("tag"),
            from_date    = params.get("from_date", ""),
            to_date      = params.get("to_date", ""),
            ai_generated = ai_generated,
            sort         = params.get("sort", "relevance"),
            page         = page,
            page_size    = page_size,
        )

        serializer = JournalSearchResultSerializer(result["results"], many=True)
        return Response({
            "backend":   result["backend"],
            "total":     result["total"],
            "page":      result["page"],
            "page_size": result["page_size"],
            "results":   serializer.data,
        })
