import threading

_log_context = threading.local()

def get_log_context():
    return {
        "user": getattr(_log_context, "user", "???"),
        "path": getattr(_log_context, "path", "???")
    }

class RequestLogContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _log_context.user = str(request.user) if hasattr(request, "user") and request.user.is_authenticated else "Anonymous"
        _log_context.path = request.get_full_path() if hasattr(request, "get_full_path") else "???"
        return self.get_response(request)
