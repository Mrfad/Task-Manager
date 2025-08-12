from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from datetime import datetime
from decimal import Decimal

from tasks.models import Task, DeliveredTask
from payments.models import TaskPaymentStatus, Payment
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Ensure each task on 2025-05-23 has related DeliveredTask, TaskPaymentStatus (and optionally Payment).'

    def handle(self, *args, **options):
        date_str = "2025-05-23"
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        start = make_aware(datetime.combine(target_date, datetime.min.time()))
        end = make_aware(datetime.combine(target_date, datetime.max.time()))

        admin_user = User.objects.get(id=1, username='fadygh')

        tasks = Task.objects.filter(created_at__range=(start, end))
        self.stdout.write(f"🔍 Found {tasks.count()} tasks on {date_str}")

        created_delivered = 0
        created_status = 0
        skipped = 0

        for task in tasks:
            changes = []

            # Check DeliveredTask
            if not hasattr(task, 'deliveredtask'):
                DeliveredTask.objects.create(
                    main_task=task,
                    delivered_by=admin_user,
                    is_delivered=False,
                    created_by=admin_user,
                    notes="Auto-created by fix_missing_task_links"
                )
                created_delivered += 1
                changes.append("DeliveredTask")

            # Check TaskPaymentStatus
            if not hasattr(task, 'payment_status'):
                tps = TaskPaymentStatus.objects.create(
                    task=task,
                    paid_amount=Decimal('0.00'),
                    is_fully_paid=False,
                    is_down_payment_only=False
                )
                tps.update_status()
                created_status += 1
                changes.append("TaskPaymentStatus")

            # Optional: auto-create dummy Payment only if you really need to
            # if not task.payments.exists() and task.final_price > 0:
            #     Payment.objects.create(
            #         task=task,
            #         amount=Decimal('0.00'),
            #         payment_type='down',
            #         payment_method='cash',
            #         paid_by=admin_user,
            #         notes='Auto-created placeholder payment'
            #     )
            #     changes.append("Payment")

            if changes:
                self.stdout.write(f"🛠️ Task ID {task.id} — created: {', '.join(changes)}")
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"\n✅ DONE:\n  DeliveredTask: {created_delivered} created\n  TaskPaymentStatus: {created_status} created\n  Skipped: {skipped} tasks already complete\n"))
