from django.db.models.signals import (m2m_changed, pre_save, post_save, post_delete, pre_delete )
from django.contrib.auth.models import User, Group
from django.db.models import Q, Avg, Sum
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F
from django.conf import settings
from .models import (Task, Subtask)
from users.models import Profile
import logging
import traceback

logger = logging.getLogger("myapp")


@receiver(post_save, sender=Task)
def assign_order_number_to_task(sender, instance, created, **kwargs):
    if created and not instance.order_number:
        try:
            with transaction.atomic():
                order_number = f"BK{instance.pk:05}"
                instance.order_number = order_number
                instance.save(update_fields=['order_number'])
        except Exception as e:
            print(f"Error assigning order_number: {e}")


@receiver(post_save, sender=Task)
def auto_create_or_update_pm_subtask(sender, instance, created, **kwargs):
    # Prevent running this twice if triggered by order_number update
    if hasattr(instance, '_pm_subtask_created'):
        return

    pm_subtask = Subtask.objects.filter(task=instance, is_project_manager=True).first()
    if pm_subtask:
        if pm_subtask.user != instance.user:
            pm_subtask.user = instance.user
            pm_subtask.save()
    else:
        pm_subtask = Subtask.objects.create(
            task=instance,
            name=instance.task_name,
            user=instance.user,
            notes_from_top=instance.notes,
            is_project_manager=True,
            added_by=instance.created_by,
        )

    # Mark that this was processed to prevent it from triggering again
    instance._pm_subtask_created = True