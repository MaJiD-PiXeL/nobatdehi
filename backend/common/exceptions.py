from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):  # type: ignore[no-untyped-def]
    """Return a stable JSON error envelope without leaking implementation details."""
    response = exception_handler(exc, context)
    if response is None:
        return response
    response.data = {
        "error": {
            "code": getattr(exc, "default_code", "validation_error"),
            "details": response.data,
        }
    }
    return Response(response.data, status=response.status_code, headers=response.headers)

