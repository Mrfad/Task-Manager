from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """
    Build a query string, preserving existing GET parameters and overriding with any new values.
    Usage: {% querystring sort='sender' page=2 %}
    """
    request = context['request']
    query = request.GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    return query.urlencode()