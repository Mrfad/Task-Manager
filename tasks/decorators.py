from django.core.exceptions import PermissionDenied
from functools import wraps

def disallow_groups(group_names):
    """
    Decorator to restrict access to users in certain groups.
    Usage: @disallow_groups(['Cashier'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.groups.filter(name__in=group_names).exists():
                raise PermissionDenied("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator