"""
Serializers for the journal app.

Three serializers:
  JournalEntrySerializer        — list / retrieve / update
  JournalEntryCreateSerializer  — POST body
  JournalSearchResultSerializer — items returned from the search endpoint

Security note:
  ai_generated is server-controlled. The user cannot set it via the API:
    - JournalEntrySerializer marks it read-only
    - JournalEntryCreateSerializer also keeps it read-only
    - The view's perform_create() pins it to False
  The AI Celery task bypasses the serializer entirely and sets it
  directly on Model.objects.create(ai_generated=True).
"""

from rest_framework import serializers

from .models import JournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model  = JournalEntry
        fields = (
            "id", "title", "body", "ticker", "tags",
            "ai_generated", "trade_id",
            "created_at", "updated_at",
        )
        # ai_generated and trade_id are server-controlled — never let
        # the client override them through the public API.
        read_only_fields = (
            "id", "ai_generated", "trade_id", "created_at", "updated_at",
        )

    def validate_ticker(self, value: str) -> str:
        return value.upper().strip() if value else value

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list of strings.")
        # Normalize: strip whitespace, lowercase, dedupe, drop empties
        seen = set()
        cleaned: list[str] = []
        for tag in value:
            t = str(tag).strip().lower()
            if t and t not in seen:
                cleaned.append(t)
                seen.add(t)
        return cleaned


class JournalEntryCreateSerializer(JournalEntrySerializer):
    """Used for POST. Same field shape — ai_generated still read-only."""

    class Meta(JournalEntrySerializer.Meta):
        # Even on create, the client cannot set ai_generated or trade_id.
        # The view's perform_create() pins ai_generated to False.
        read_only_fields = (
            "id", "ai_generated", "trade_id", "created_at", "updated_at",
        )


class JournalSearchResultSerializer(serializers.Serializer):
    """
    Each item returned by /api/v1/journal/search/.

    `highlight` is a dict of field name → list of snippet strings with
    matched terms wrapped in <em></em>. Returned by Elasticsearch; empty
    in the Postgres fallback.
    """
    id           = serializers.IntegerField()
    title        = serializers.CharField()
    body         = serializers.CharField()
    ticker       = serializers.CharField(allow_blank=True)
    tags         = serializers.ListField(child=serializers.CharField())
    ai_generated = serializers.BooleanField()
    created_at   = serializers.DateTimeField()
    # dict of field name → highlighted snippet string; empty in Postgres fallback
    highlight    = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default=dict,
    )
    score = serializers.FloatField(required=False, allow_null=True, default=None)
