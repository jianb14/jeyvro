"""Enable `pg_trgm` — the typo-tolerance foundation (§18.1, §18.2).

PostgreSQL ships full-text search in core (`tsvector`/`tsquery`), so the ranked
search in `apps.search.services` needs no schema work at all and computes its
vectors on the fly. Trigram similarity is the one piece that is *not* in core:
`similarity()` is undefined until `pg_trgm` is installed, which would make the
typo fallback raise at query time rather than degrade. Installing it here makes
that failure impossible on a fresh database.

`pg_trgm` is a *trusted* extension since PostgreSQL 13, so the database owner
can create it without superuser rights — this migration will not fail on a
normal managed database.

Index strategy is deliberately deferred: `docs/ROADMAP.md` §18.2 owns "search
indexing strategy", and choosing GIN index shapes before there is a query
pattern to measure would be guessing. The on-the-fly design is correct first;
indexes are the optimisation that follows measurement.
"""
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        TrigramExtension(),
    ]
