from django import template

register = template.Library()

@register.filter
def status_color(status):
    return {
        'created': 'secondary',
        'in_progress': 'info',
        'done': 'primary',
        'closed': 'dark',
        'delivered': 'success',
        'canceled': 'danger',
    }.get(status, 'light')