from django import template
from django.template.loader import render_to_string

register = template.Library()


@register.filter(name='replace')
def replace(value, arg):
    """Usage: {{ value|replace:'old,new' }}"""
    old, new = arg.split(',')
    return value.replace(old, new)


@register.filter
def index(sequence, position):
    return sequence[position]


@register.filter
def dict_get(d, key):
    return d.get(key, '')


@register.simple_tag
def render_progressbar(task):
    status_flow = ['created', 'in_progress', 'done', 'closed', 'delivered']
    steps = status_flow.copy()

    stage_times = {
        'created': task.created_at,
    }

    if task.updated_at:
        stage_times['in_progress'] = task.updated_at

    if task.check_all_subtasks_done():
        done_log = task.activity_logs.filter(action__icontains='subtask done').order_by('timestamp').first()
        if done_log:
            stage_times['done'] = done_log.timestamp

    if task.closed_at:
        stage_times['closed'] = task.closed_at

    if hasattr(task, 'deliveredtask') and task.deliveredtask and task.deliveredtask.delivery_date:
        stage_times['delivered'] = task.deliveredtask.delivery_date

    current_status = task.status

    # 🔢 Step index
    if current_status in steps:
        step_index = steps.index(current_status)
    else:
        fallback_stages = ['delivered', 'closed', 'done', 'in_progress', 'created']
        step_index = 0
        for status in fallback_stages:
            if status in steps:
                step_index = steps.index(status)
                break

    fill_percentage = int(((step_index + 1) / len(steps)) * 100)

    # Tooltip descriptions
    step_titles = {
        'created': 'Task has been created.',
        'in_progress': 'Task is in progress.',
        'done': 'All subtasks are completed.',
        'closed': 'Task is closed.',
        'delivered': 'Task is delivered to the customer.',
    }

    return render_to_string("tasks/partials/task-detail/progressbar.html", {
        'task': task,
        'steps': steps,
        'step_index': step_index,
        'fill_percentage': fill_percentage,
        'step_titles': step_titles,
    })
