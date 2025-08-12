# templatetags/active_link.py
# this is responsible for marking link as active if in request.path
from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()

@register.simple_tag(takes_context=True)
def active_link(context, url_name):
    request = context['request']
    try:
        if request.path == reverse(url_name):
            return 'active'
    except NoReverseMatch:
        return ''
    return ''

@register.simple_tag(takes_context=True)
def active_dropdown(context, *url_names):
    request = context['request']
    for name in url_names:
        try:
            if request.path == reverse(name):
                return 'active'
        except NoReverseMatch:
            continue
    return ''


@register.simple_tag(takes_context=True)
def bg_info(context, url_name):
    request = context['request']
    if request.path == reverse(url_name):
        return 'bg-info'
    return ''