"""
JournalSearchService — full-text search with graceful degradation.

Strategy:
  1. Try Elasticsearch first (fast, ranked, supports highlights and fuzzy matching)
  2. On any ES error, fall back to Postgres ILIKE

The fallback isn't as good (no ranking, no highlights, no fuzzy) but it
keeps search working when ES is down. Search results always include a
"backend" field so the client can show a "search degraded" notice.
"""

import logging
from datetime import date

from django.db.models import Q
from elasticsearch_dsl.query import Q as ESQ

from .documents import JournalEntryDocument
from .models import JournalEntry

logger = logging.getLogger(__name__)


class JournalSearchService:

    def __init__(self, user):
        self.user = user

    def search(
        self,
        query:        str,
        ticker:       str = "",
        tags:         list | None = None,
        from_date:    str = "",
        to_date:      str = "",
        ai_generated: bool | None = None,
        sort:         str = "relevance",
        page:         int = 1,
        page_size:    int = 20,
    ) -> dict:
        """
        Full-text search across the user's journal.

        Returns:
            {
              "backend":   "elasticsearch" | "postgres",
              "total":     int,
              "page":      int,
              "page_size": int,
              "results":   [{ id, title, body, ticker, tags, ai_generated,
                              created_at, highlight: { title?: str, body?: str },
                              score }]
            }
        """
        if not query.strip():
            return {
                "backend": "elasticsearch", "total": 0,
                "page": page, "page_size": page_size, "results": [],
            }

        kwargs = dict(
            query=query, ticker=ticker, tags=tags or [],
            from_date=from_date, to_date=to_date,
            ai_generated=ai_generated, sort=sort,
            page=page, page_size=page_size,
        )
        try:
            return self._es_search(**kwargs)
        except Exception as exc:
            logger.warning("ES search failed, falling back to Postgres: %s", exc)
            return self._postgres_search(**kwargs)


    # ─── Elasticsearch ────────────────────────────────────────

    def _es_search(
        self, query, ticker, tags, from_date, to_date,
        ai_generated, sort, page, page_size,
    ) -> dict:
        match_q = ESQ(
            "multi_match",
            query=query,
            fields=["title^2", "body"],
            fuzziness="AUTO",
            type="best_fields",
        )

        filters = [ESQ("term", user_id=str(self.user.id))]
        if ticker:
            filters.append(ESQ("term", ticker=ticker.upper()))
        for t in tags:
            filters.append(ESQ("term", tags=t))
        if ai_generated is not None:
            filters.append(ESQ("term", ai_generated=ai_generated))
        if from_date or to_date:
            date_range = {}
            if from_date:
                date_range["gte"] = from_date
            if to_date:
                date_range["lte"] = to_date
            filters.append(ESQ("range", created_at=date_range))

        s = (
            JournalEntryDocument.search()
            .query("bool", must=[match_q], filter=filters)
            .highlight("title", "body", fragment_size=150,
                       pre_tags=["<mark>"], post_tags=["</mark>"])
            .extra(size=page_size, from_=(page - 1) * page_size)
        )

        if sort == "date_desc":
            s = s.sort("-created_at")
        elif sort == "date_asc":
            s = s.sort("created_at")
        # default: relevance (ES score order)

        response = s.execute()

        results = []
        for hit in response:
            highlight = {}
            if hasattr(hit.meta, "highlight"):
                for field in ("title", "body"):
                    if field in hit.meta.highlight:
                        highlight[field] = " ... ".join(hit.meta.highlight[field])

            results.append({
                "id":           int(hit.meta.id),
                "title":        hit.title,
                "body":         hit.body,
                "ticker":       hit.ticker or "",
                "tags":         list(hit.tags) if hit.tags else [],
                "ai_generated": bool(hit.ai_generated) if hit.ai_generated is not None else False,
                "created_at":   hit.created_at.isoformat() if hit.created_at else None,
                "highlight":    highlight,
                "score":        hit.meta.score,
            })

        return {
            "backend":   "elasticsearch",
            "total":     response.hits.total.value,
            "page":      page,
            "page_size": page_size,
            "results":   results,
        }

    # ─── Postgres fallback ────────────────────────────────────

    def _postgres_search(
        self, query, ticker, tags, from_date, to_date,
        ai_generated, sort, page, page_size,
    ) -> dict:
        qs = JournalEntry.objects.filter(user=self.user).filter(
            Q(title__icontains=query) | Q(body__icontains=query)
        )
        if ticker:
            qs = qs.filter(ticker=ticker.upper())
        for t in tags:
            qs = qs.filter(tags__contains=[t])
        if ai_generated is not None:
            qs = qs.filter(ai_generated=ai_generated)
        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)

        if sort == "date_asc":
            qs = qs.order_by("created_at")
        else:
            qs = qs.order_by("-created_at")

        total   = qs.count()
        offset  = (page - 1) * page_size
        entries = qs[offset : offset + page_size]

        results = []
        for entry in entries:
            results.append({
                "id":           entry.id,
                "title":        entry.title,
                "body":         entry.body,
                "ticker":       entry.ticker,
                "tags":         entry.tags,
                "ai_generated": entry.ai_generated,
                "created_at":   entry.created_at.isoformat(),
                "highlight":    {},
                "score":        None,
            })

        return {
            "backend":   "postgres",
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "results":   results,
        }
