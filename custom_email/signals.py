# custom_email/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.db.utils import OperationalError, ProgrammingError

@receiver(post_migrate)
def create_fetch_email_task(sender, **kwargs):
    if sender.label != 'custom_email':
        return

    try:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )

        PeriodicTask.objects.get_or_create(
            interval=schedule,
            name='Fetch all mailbox emails',
            task='custom_email.tasks.fetch_all_emails',
        )
    except (OperationalError, ProgrammingError):
        # This is still necessary during early migration phases
        pass
