"""Foundation health probe — the first JEYVRO API endpoint.

Rules honoured (backend-api): versioned path (/api/v1/health), JSON only,
explicit permission intent (public on purpose — it is an ops probe).
"""
from django.db import connection
from django.http import JsonResponse


def health(request):
    """Return service status; report database reachability without failing."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        database = 'ok'
    except Exception:
        # Database may legitimately be absent during early foundation work;
        # the probe stays honest about it instead of lying with a 500.
        database = 'unavailable'

    return JsonResponse({
        'status': 'ok',
        'service': 'jeyvro-backend',
        'database': database,
    })
