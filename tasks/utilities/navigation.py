from urllib.parse import urlparse
from django.urls import reverse

def get_back_url(request, routes: dict, default: str):
    from urllib.parse import urlparse
    from django.urls import reverse, NoReverseMatch

    referer = request.META.get('HTTP_REFERER', '')
    path = urlparse(referer).path if referer else ''

    for key, target in routes.items():
        if key in path:
            # ✅ If target is a full path (like /task/detail/123/) → just return it
            if target.startswith('/'):
                return target
            else:
                try:
                    return reverse(target)
                except NoReverseMatch:
                    # ❌ fallback if required args are missing
                    return path or reverse(default)

    return reverse(default) if not default.startswith('/') else default