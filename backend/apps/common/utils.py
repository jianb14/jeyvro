"""Shared model-adjacent helpers (one implementation, many domains — §13)."""
from django.utils.text import slugify


def slugify_unique(model, base, *, field='slug', exclude_pk=None):
    """Returns a unique slug for `model` derived from `base`.

    Shared by stores.Store and catalog.Product — slugs are unique across
    all rows, including non-public ones. One rule, one implementation.
    """
    cleaned = slugify(base) or 'item'
    candidate = cleaned
    counter = 2
    queryset = model.objects.all()
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    while queryset.filter(**{field: candidate}).exists():
        candidate = f'{cleaned}-{counter}'
        counter += 1
    return candidate