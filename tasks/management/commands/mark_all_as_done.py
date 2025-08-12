from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import Task, Subtask, DeliveredTask

class Command(BaseCommand):
    help = 'Mark all tasks, subtasks, and deliveries as finished'

    def handle(self, *args, **kwargs):
        now = timezone.now()

        tasks = Task.objects.all()
        total = tasks.count()

        for task in tasks:
            updated = False

            # Update subtasks
            subtasks = task.subtask_set.all()
            for subtask in subtasks:
                if not subtask.is_done or not subtask.is_done:
                    subtask.is_done = True
                    subtask.save()
                    updated = True

            # Update task status and payment
            if task.status not in ['done', 'delivered', 'closed']:
                task.status = 'delivered'
                updated = True

            if task.paid_status != 'P':
                task.paid_status = 'P'
                updated = True

            if not task.closed:
                task.closed = True
                task.closed_at = now
                updated = True

            # Set delivered task if exists
            try:
                delivery = DeliveredTask.objects.get(main_task=task)
                if not delivery.is_delivered:
                    delivery.is_delivered = True
                    delivery.delivery_date = now
                    delivery.save()
                    updated = True
            except DeliveredTask.DoesNotExist:
                pass

            if updated:
                task.save()

        self.stdout.write(self.style.SUCCESS(f'✅ Successfully updated {total} tasks and their subtasks/deliveries.'))
