from django.core.management.base import BaseCommand
from datetime import date
from decimal import Decimal
from django.db.models import Sum

from tasks.models import Task, DeliveredTask
from payments.models import TaskPaymentStatus, Payment
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Clean and fix tasks created on 2025-05-23:\n'
        '- Remove data for unpaid tasks\n'
        '- Set status to canceled if task is canceled\n'
        '- Auto-deliver closed and paid tasks'
    )

    def handle(self, *args, **options):
        target_date = date(2025, 5, 23)
        tasks = Task.objects.filter(created_at__date=target_date)
        fadygh = User.objects.get(id=1, username='fadygh')

        self.stdout.write(f"🔍 Found {tasks.count()} tasks created on {target_date}")

        modified_count = 0

        for task in tasks:
            total_paid = task.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            changes = []

            # 🔁 Rule 1: If task is canceled, force status and paid_status
            if task.canceled:
                Task.objects.filter(id=task.id).update(status='canceled', paid_status='U')
                task.refresh_from_db()
                changes.append("Forced DB update: status='canceled', paid_status='U'")
                # 🚫 Skip rest of loop to prevent accidental overwrite
                modified_count += 1
                self.stdout.write(f"🛠 Task ID {task.id}: " + " | ".join(changes))
                continue  # ← Important!

            # 🔁 Rule 2: If total paid = 0, delete related data and update status
            if total_paid == 0:
                if hasattr(task, 'deliveredtask'):
                    task.deliveredtask.delete()
                    changes.append("Deleted DeliveredTask")

                try:
                    if task.payment_status:
                        task.payment_status.delete()
                        changes.append("Deleted TaskPaymentStatus")
                except TaskPaymentStatus.DoesNotExist:
                    pass

                payments_qs = task.payments.all()
                if payments_qs.exists():
                    count = payments_qs.count()
                    payments_qs.delete()
                    changes.append(f"Deleted {count} Payment(s)")

                old_status = task.status
                old_paid_status = task.paid_status
                task.status = 'done'
                task.paid_status = 'U'
                task.closed = False
                task.save(update_fields=['status', 'paid_status', 'closed'])
                changes.append(f"Updated status: {old_status} → done, paid_status: {old_paid_status} → U")

            # 🔁 Rule 3: If closed + paid + not delivered → create DeliveredTask
            elif task.closed and task.paid_status == 'P' and not hasattr(task, 'deliveredtask'):
                DeliveredTask.objects.create(
                    main_task=task,
                    delivered_by=fadygh,
                    created_by=fadygh,
                    is_delivered=True,
                    notes="Auto-created for closed+paid task on 2025-05-23"
                )
                changes.append("✅ Created DeliveredTask (paid & closed)")

            if changes:
                modified_count += 1
                self.stdout.write(f"🛠 Task ID {task.id}: " + " | ".join(changes))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Completed:\n  Modified Tasks: {modified_count}"))


    """
    Management command to clean and normalize Task-related records created on 2025-05-23.

    🧼 What this script does:
    -------------------------------------------------------------------
    1. For all tasks created on 2025-05-23:
    
       🔁 If task.canceled is True:
           - Forcefully set task.status = 'canceled'
           - Forcefully set task.paid_status = 'U'

       💸 If the task has no payments (total_paid == 0):
           - Delete any related DeliveredTask
           - Delete any related TaskPaymentStatus
           - Delete all related Payment records
           - Update task.status = 'done'
           - Update task.paid_status = 'U'

       📦 If the task is closed and paid (paid_status = 'P'), but not yet delivered:
           - Create a DeliveredTask instance
           - Assign 'fadygh' (user ID 1) as both delivered_by and created_by
           - Set is_delivered = True

    ✅ The purpose of this script is to ensure data integrity by:
        - Cleaning up orphaned or incomplete financial and delivery records
        - Updating task statuses to match their actual state
        - Ensuring consistency between payment, delivery, and task lifecycle

    🔐 This command is meant to be idempotent and safe to re-run on the target date.
    """
