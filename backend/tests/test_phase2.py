"""
Phase 2 tests — journal CRUD, Elasticsearch search, AI journal saving,
and the updated AI agent integration with real portfolio data.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()


# ─── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="ethan", email="ethan@example.com", password="testpass123"
    )


@pytest.fixture
def auth_token(client, user):
    resp = client.post(
        "/api/auth/token/",
        {"email": "ethan@example.com", "password": "testpass123"},
        content_type="application/json",
    )
    return resp.json()["access"]


@pytest.fixture
def auth_headers(auth_token):
    return {"HTTP_AUTHORIZATION": f"Bearer {auth_token}"}


@pytest.fixture
def journal_entry(db, user):
    from apps.journal.models import JournalEntry
    with patch("apps.journal.models.JournalEntryDocument"):
        return JournalEntry.objects.create(
            user=user,
            title="Bought PLTR calls — thesis",
            body="PLTR breaking out above $160. Bought 2 July $160 calls at $4.50. Thesis: earnings catalyst.",
            ticker="PLTR",
            tags=["options", "earnings", "pltr"],
            ai_generated=False,
        )


@pytest.fixture
def ai_journal_entry(db, user):
    from apps.journal.models import JournalEntry
    with patch("apps.journal.models.JournalEntryDocument"):
        return JournalEntry.objects.create(
            user=user,
            title="BUY NVDA — AI Trade Journal",
            body="Bought 10 shares of NVDA at $820. Thesis: AI infrastructure play.",
            ticker="NVDA",
            tags=["stock", "buy", "ai-generated"],
            ai_generated=True,
        )


# ─── Journal Model tests ──────────────────────────────────────

@pytest.mark.django_db
class TestJournalEntryModel:

    def test_str_with_ticker(self, journal_entry):
        assert "PLTR" in str(journal_entry)
        assert "Bought PLTR calls" in str(journal_entry)

    def test_str_without_ticker(self, user):
        from apps.journal.models import JournalEntry
        with patch("apps.journal.models.JournalEntryDocument"):
            entry = JournalEntry.objects.create(
                user=user, title="General thoughts", body="Market is choppy."
            )
        assert str(entry) == "General thoughts"

    def test_default_tags_is_list(self, user):
        from apps.journal.models import JournalEntry
        with patch("apps.journal.models.JournalEntryDocument"):
            entry = JournalEntry.objects.create(
                user=user, title="No tags", body="Body text."
            )
        assert entry.tags == []

    def test_ticker_auto_uppercase_via_serializer(self, client, auth_headers):
        with patch("apps.journal.models.JournalEntryDocument"):
            resp = client.post(
                "/api/journal/",
                {"title": "Test", "body": "Body", "ticker": "pltr", "tags": []},
                content_type="application/json",
                **auth_headers,
            )
        assert resp.status_code == 201
        assert resp.json()["ticker"] == "PLTR"


# ─── Journal API tests ────────────────────────────────────────

@pytest.mark.django_db
class TestJournalAPI:

    def test_list_requires_auth(self, client):
        assert client.get("/api/journal/").status_code == 401

    def test_create_entry(self, client, auth_headers):
        with patch("apps.journal.models.JournalEntryDocument"):
            resp = client.post(
                "/api/journal/",
                {
                    "title": "PLTR breakout play",
                    "body": "Entering PLTR ahead of earnings.",
                    "ticker": "PLTR",
                    "tags": ["earnings", "options"],
                },
                content_type="application/json",
                **auth_headers,
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "PLTR breakout play"
        assert data["ticker"] == "PLTR"
        assert "earnings" in data["tags"]

    def test_list_entries(self, client, auth_headers, journal_entry):
        resp = client.get("/api/journal/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_filter_by_ticker(self, client, auth_headers, journal_entry, ai_journal_entry):
        resp = client.get("/api/journal/?ticker=PLTR", **auth_headers)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert all(r["ticker"] == "PLTR" for r in results)

    def test_filter_by_ai(self, client, auth_headers, journal_entry, ai_journal_entry):
        resp = client.get("/api/journal/?ai=true", **auth_headers)
        assert resp.status_code == 200
        assert all(r["ai_generated"] for r in resp.json()["results"])

    def test_retrieve_entry(self, client, auth_headers, journal_entry):
        resp = client.get(f"/api/journal/{journal_entry.id}/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == journal_entry.id

    def test_update_entry(self, client, auth_headers, journal_entry):
        with patch("apps.journal.models.JournalEntryDocument"):
            resp = client.patch(
                f"/api/journal/{journal_entry.id}/",
                {"title": "Updated title"},
                content_type="application/json",
                **auth_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated title"

    def test_delete_entry(self, client, auth_headers, journal_entry):
        with patch("apps.journal.models.JournalEntryDocument"):
            resp = client.delete(
                f"/api/journal/{journal_entry.id}/", **auth_headers
            )
        assert resp.status_code == 204

    def test_cannot_access_other_users_entry(self, client, auth_headers, db):
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass123"
        )
        from apps.journal.models import JournalEntry
        with patch("apps.journal.models.JournalEntryDocument"):
            other_entry = JournalEntry.objects.create(
                user=other_user, title="Private", body="..."
            )
        resp = client.get(f"/api/journal/{other_entry.id}/", **auth_headers)
        assert resp.status_code == 404


# ─── Elasticsearch search tests ───────────────────────────────

@pytest.mark.django_db
class TestJournalSearch:

    def test_search_requires_auth(self, client):
        assert client.get("/api/journal/search/?q=PLTR").status_code == 401

    def test_search_calls_es_service(self, client, auth_headers, journal_entry):
        mock_result = {
            "total": 1,
            "page": 1,
            "page_size": 20,
            "results": [
                {
                    "id": journal_entry.id,
                    "title": journal_entry.title,
                    "ticker": "PLTR",
                    "tags": ["options"],
                    "ai_generated": False,
                    "created_at": journal_entry.created_at,
                    "highlight": {"body": ["bought <em>PLTR</em> calls"]},
                    "score": 1.23,
                }
            ],
        }
        with patch("apps.journal.views.JournalSearchService.search", return_value=mock_result):
            resp = client.get("/api/journal/search/?q=PLTR", **auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["ticker"] == "PLTR"
        assert "highlight" in data["results"][0]

    def test_search_passes_filters(self, client, auth_headers):
        with patch("apps.journal.views.JournalSearchService.search", return_value={
            "total": 0, "page": 1, "page_size": 20, "results": []
        }) as mock_search:
            client.get(
                "/api/journal/search/?q=earnings&ticker=PLTR&tag=options&sort=date_desc",
                **auth_headers,
            )
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["query"] == "earnings"
        assert call_kwargs["ticker"] == "PLTR"
        assert "options" in call_kwargs["tags"]
        assert call_kwargs["sort"] == "date_desc"

    def test_search_page_size_capped_at_50(self, client, auth_headers):
        with patch("apps.journal.views.JournalSearchService.search", return_value={
            "total": 0, "page": 1, "page_size": 50, "results": []
        }) as mock_search:
            client.get("/api/journal/search/?page_size=999", **auth_headers)
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["page_size"] == 50


# ─── ES signal tests ──────────────────────────────────────────

@pytest.mark.django_db
class TestElasticsearchSignals:

    def test_post_save_triggers_es_sync(self, user):
        from apps.journal.models import JournalEntry
        with patch("apps.journal.models.JournalEntryDocument") as mock_doc_class:
            mock_doc = MagicMock()
            mock_doc_class.return_value = mock_doc
            entry = JournalEntry.objects.create(
                user=user, title="Signal test", body="Body."
            )
        mock_doc.update.assert_called_once_with(entry)

    def test_post_delete_triggers_es_removal(self, user):
        from apps.journal.models import JournalEntry
        with patch("apps.journal.models.JournalEntryDocument"):
            entry = JournalEntry.objects.create(
                user=user, title="Delete test", body="Body."
            )
        with patch("apps.journal.models.JournalEntryDocument") as mock_doc_class:
            mock_doc = MagicMock()
            mock_doc_class.return_value = mock_doc
            entry.delete()
        mock_doc.update.assert_called_once_with(entry, action="delete")


# ─── AI Journal saving tests ──────────────────────────────────

@pytest.mark.django_db
class TestAIJournalSaving:

    def test_journal_writer_api_saves_to_db(self, client, auth_headers):
        with patch("apps.ai.tasks.run_ai_agent.delay") as mock_task:
            mock_task.return_value = MagicMock(id="fake-task-id")
            resp = client.post(
                "/api/ai/journal/",
                {"trade_data": {"ticker": "PLTR", "asset_type": "call",
                                "side": "buy", "quantity": 2, "price": 4.50,
                                "strike": 160, "expiry": "2025-07-18"}},
                content_type="application/json",
                **auth_headers,
            )
        assert resp.status_code == 202
        assert resp.json()["saves_to_journal"] is True

    def test_save_journal_entry_creates_db_row(self, user):
        from apps.ai.tasks import _save_journal_entry
        from apps.journal.models import JournalEntry

        with patch("apps.journal.models.JournalEntryDocument"):
            _save_journal_entry(
                user = user,
                result="**Trade**: Bought 2 PLTR $160 calls at $4.50\n\n**Thesis**: Earnings play.",
                trade_data={"ticker": "PLTR", "asset_type": "call", "side": "buy"},
            )

        entry = JournalEntry.objects.get(user=user, ticker="PLTR")
        assert entry.ai_generated is True
        assert "pltr" in entry.tags
        assert "ai-generated" in entry.tags

    def test_analyze_view_uses_real_data(self, client, auth_headers, user):
        with patch("apps.ai.tasks.run_ai_agent.delay") as mock_task:
            mock_task.return_value = MagicMock(id="fake-task-id")
            resp = client.post("/api/ai/analyze/", **auth_headers,
                               content_type="application/json")
        assert resp.status_code == 202
        call_args = mock_task.call_args
        assert call_args[0][0] == "analyze"
        assert call_args[1]["user_id"] == user.id
