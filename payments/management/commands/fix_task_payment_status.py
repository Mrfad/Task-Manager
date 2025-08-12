# payments/management/commands/fix_task_payment_status.py

from django.core.management.base import BaseCommand
from payments.models import TaskPaymentStatus
from tasks.models import Task

class Command(BaseCommand):  # ✅ THIS MUST EXIST AND BE NAMED EXACTLY 'Command'
    help = 'Recalculate TaskPaymentStatus for all tasks'

    def handle(self, *args, **kwargs):
        tasks = Task.objects.all()
        updated = 0
        for task in tasks:
            if task.final_price == 0:
                continue

            status, created = TaskPaymentStatus.objects.get_or_create(task=task)
            status.total_price = task.final_price
            status.update_status()
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated} task payment statuses"))
