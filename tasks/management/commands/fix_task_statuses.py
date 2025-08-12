# tasks/management/commands/fix_task_statuses.py

from django.core.management.base import BaseCommand
from tasks.models import Task, Subtask, DeliveredTask

class Command(BaseCommand):
    help = 'Update task.status based on subtasks, delivery, and cancellation'

    def handle(self, *args, **kwargs):
        updated_count = 0

        for task in Task.objects.all():
            original_status = task.status

            # 1. Canceled overrides everything
            if task.canceled:
                task.status = 'canceled'

            # 2. Delivered check
            elif hasattr(task, 'deliveredtask') and task.deliveredtask.is_delivered:
                task.status = 'delivered'

            # 3. Closed manually
            elif task.closed:
                task.status = 'closed'

            else:
                subtasks = Subtask.objects.filter(task=task)

                if not subtasks.exists():
                    task.status = 'created'

                elif subtasks.filter(is_done=False, is_canceled=False).exists():
                    task.status = 'in_progress'

                elif subtasks.filter(is_done=True, is_canceled=False).count() == subtasks.count():
                    task.status = 'done'

                else:
                    task.status = 'in_progress'  # Fallback if mixed/canceled states

            if task.status != original_status:
                task.save(update_fields=['status'])
                updated_count += 1
                self.stdout.write(f"🔄 Task {task.id}: {original_status} → {task.status}")

        self.stdout.write(self.style.SUCCESS(f"✅ Updated status for {updated_count} tasks"))
