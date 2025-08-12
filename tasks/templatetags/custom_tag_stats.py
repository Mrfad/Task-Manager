from django import template

register = template.Library()

@register.filter
def to_int(value):
    return int(value)

@register.filter(name='make_range')
def make_range(value, end):
    return range(value, end)

@register.filter
def map_attr(objects, attr_path):
    def get_attr(obj, attr_path):
        for attr in attr_path.split("."):
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj

    return [get_attr(obj, attr_path) for obj in objects]

@register.filter
def split(value, delimiter=","):
    return value.split(delimiter)

@register.filter
def index(sequence, position):
    try:
        return sequence[int(position) - 1]  # Convert position to int, subtract 1 for 0-based index
    except (IndexError, ValueError, TypeError):
        return ""
