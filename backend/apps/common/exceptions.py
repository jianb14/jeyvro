"""API error conventions (PROJECT_CONTEXT §8, backend-api).

Every DRF-handled error returns {error, detail?, field_errors?} — one-off
shapes forbidden. Unhandled exceptions fall through to the JSON 500 handler
in config.urls, so HTML error pages never leave Django.
"""
from rest_framework.views import exception_handler


def jeyvro_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        # Not DRF-handled (e.g. uncaught crash) — JSON 500 handler takes over.
        return None

    data = response.data
    if isinstance(data, dict):
        payload = {'error': str(data.get('detail', 'validation_error'))}
        if data.get('detail') is not None:
            payload['detail'] = str(data['detail'])
        field_errors = {
            key: value for key, value in data.items() if key != 'detail'
        }
        if field_errors:
            payload['field_errors'] = field_errors
    else:
        payload = {'error': 'validation_error', 'detail': data}

    response.data = payload
    return response
