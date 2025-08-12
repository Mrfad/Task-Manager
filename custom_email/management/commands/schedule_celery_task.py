from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from json import dumps

class Command(BaseCommand):
    help = 'Set up periodic tasks like daily fetch cleanup.'

    def handle(self, *args, **kwargs):
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='6',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Beirut',
        )

        PeriodicTask.objects.filter(name='Clean old FetchStatus records daily at 6AM').delete()

        PeriodicTask.objects.create(
            crontab=schedule,
            name='Clean old FetchStatus records daily at 6AM',
            task='custom_email.tasks.cleanup_old_fetch_statuses',
            kwargs=dumps({"days": 1}),
            enabled=True
        )
        self.stdout.write(self.style.SUCCESS("✅ Periodic task scheduled for 6AM daily."))