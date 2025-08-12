from django import template

register = template.Library()

@register.filter
def in_group(user, group_string):
    """
    Usage:
    - Single group: {% if request.user|in_group:"Developer" %}
    - OR groups: {% if request.user|in_group:"Developer|Manager" %}
    - AND groups: {% if request.user|in_group:"Developer&Manager" %}
    Supports:
    - OR: "Graphics|Developer"
    - AND: "Graphics&Manager"
    - Alias group logic using GROUP_ALIASES
    """
    GROUP_ALIASES = {
        "Graphics": ["Graphic", "Typing", "Autocad", "laser", "Outdoor", "FrontDesk"]
    }
    if not user.is_authenticated:
        return False

    def resolve_group_alias(name):
        return GROUP_ALIASES.get(name, [name])

    if '|' in group_string:
        groups = group_string.split('|')
        all_possible = [g for name in groups for g in resolve_group_alias(name)]
        return user.groups.filter(name__in=all_possible).exists()

    elif '&' in group_string:
        groups = group_string.split('&')
        return all(user.groups.filter(name__in=resolve_group_alias(name)).exists() for name in groups)

    else:
        return user.groups.filter(name__in=resolve_group_alias(group_string)).exists()