"""Search app config (Phase 18 — ROADMAP §18.1, §18.2)."""
from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.search'
