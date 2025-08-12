import csv
from django.core.management.base import BaseCommand
from tasks.models import Notification, Task, NotificationType
from users.models import CustomUser
from django.utils import timezone

class Command(BaseCommand):
    help = 'Import notifications from CSV as viewed Task notifications'

    def handle(self, *args, **kwargs):
        notif_type, _ = NotificationType.objects.get_or_create(name='Viewed Task')

        with open('exported_notifications.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    task = Task.objects.get(id=row['task_id'])
                    user = CustomUser.objects.get(id=row['user_id'])
                except Exception as e:
                    self.stdout.write(f"⚠️ FK error: {e}")
                    continue

                Notification.objects.create(
                    user=user,
                    task=task,
                    type=notif_type,
                    message=f"You viewed task {task.order_number}",
                    is_read=True,
                    created_at=timezone.now(),
                )

        self.stdout.write(self.style.SUCCESS("✅ Notifications imported"))
