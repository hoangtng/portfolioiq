"""
JournalEntryDocument — maps JournalEntry to Elasticsearch.

Index:    journal_entries
Analyzer: standard (English-aware tokenization, lowercase folding)

Fields:
  title          → text  (full-text search, title.raw for sorting)
  body           → text  (full-text search)
  ticker         → keyword (exact match for filters)
  tags           → keyword[] (exact match for filters)
  user_id        → integer (scope all searches to one user)
  ai_generated   → boolean (filter manual vs AI entries)
  created_at     → date (range filter + sort)
"""

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

# Canonical relative import — JournalEntry is in the same app.
from .models import JournalEntry


@registry.register_document
class JournalEntryDocument(Document):

    title = fields.TextField(
        analyzer="standard",
        fields={"raw": fields.KeywordField()},   # for exact match / sort
    )
    body = fields.TextField(analyzer="standard")

    ticker = fields.KeywordField()
    tags   = fields.KeywordField(multi=True)

    user_id      = fields.IntegerField()
    ai_generated = fields.BooleanField()
    created_at   = fields.DateField()

    class Index:
        name = "journal_entries"
        settings = {
            "number_of_shards":   1,    # single-node dev setup
            "number_of_replicas": 0,
        }

    class Django:
        model  = JournalEntry
        fields = ["id"]   # include PK so we can fetch full rows from Postgres

    def prepare_user_id(self, instance):
        return instance.user_id

    def prepare_tags(self, instance):
        # JSONField could be None on a malformed row — coerce to []
        return list(instance.tags or [])
