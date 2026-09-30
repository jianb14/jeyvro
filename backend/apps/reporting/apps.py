"""Reporting app config (Phase 19 — ROADMAP §19.1)."""
from django.apps import AppConfig


class ReportingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reporting'
