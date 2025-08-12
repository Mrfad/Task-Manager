# payments/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Payment

# Auto update payment status when payment change
@receiver([post_save, post_delete], sender=Payment)
def update_task_payment_status(sender, instance, **kwargs):
    task = instance.task
    if hasattr(task, 'payment_status'):
        task.payment_status.update_status()