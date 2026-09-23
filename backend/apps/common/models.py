"""Shared model foundations.

Every concrete model that needs audit timestamps inherits TimeStampedModel
(Phase 2.2 — created/updated timestamps convention).
"""
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
