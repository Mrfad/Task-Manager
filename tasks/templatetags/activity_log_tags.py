import random
from django import template

register = template.Library()

BADGE_CLASSES = [
    "bg-primary", "bg-secondary", "bg-success",
    "bg-danger", "bg-warning", "bg-info", "bg-dark"
]


@register.simple_tag(takes_context=True)
def get_note_badge(context, note):
    note_key = str(note) if note else ""
    if not note_key:
        return ""
    
    # Deterministic color based on note content hash
    color_index = hash(note_key) % len(BADGE_CLASSES)
    return BADGE_CLASSES[color_index]


# @register.simple_tag(takes_context=True)
# def get_note_badge(context, note):
#     """
#     Assign a consistent badge class to each unique note content during one render cycle.
#     """
#     if 'note_color_map' not in context.render_context:
#         context.render_context['note_color_map'] = {}

#     note_map = context.render_context['note_color_map']
    
#     # Create a key from the note content (or empty string if None)
#     note_key = str(note) if note else ""
    
#     if note_key not in note_map:
#         # Use remaining colors or fallback
#         used_colors = set(note_map.values())
#         available = list(set(BADGE_CLASSES) - used_colors)
#         note_map[note_key] = random.choice(available) if available else random.choice(BADGE_CLASSES)
    
#     return note_map[note_key]