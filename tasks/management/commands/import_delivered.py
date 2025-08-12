import csv
from django.core.management.base import BaseCommand
from tasks.models import DeliveredTask, Task
from users.models import CustomUser
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Import DeliveredTask from CSV'

    def handle(self, *args, **kwargs):
        with open('exported_delivered.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    main_task = Task.objects.get(id=row['main_task_id'])
                    delivered_by = CustomUser.objects.get(id=row['delivered_by_id']) if row['delivered_by_id'] else None
                    created_by = CustomUser.objects.get(id=row['closed_by_id']) if row['closed_by_id'] else None
                except Exception as e:
                    self.stdout.write(f"⚠️ FK resolution error: {e}")
                    continue

                obj, created = DeliveredTask.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'main_task': main_task,
                        'delivered_by': delivered_by,
                        'created_by': created_by,
                        'received_person': row['received_person'],
                        'is_delivered': row['is_delivered'] == 'True',
                        'delivery_date': parse_datetime(row['delivery_date']),
                        'notes': row['notes'],
                    }
                )

                self.stdout.write(f"✅ {'Created' if created else 'Updated'} DeliveredTask ID {obj.id}")

        self.stdout.write(self.style.SUCCESS("🎉 Delivered tasks imported successfully"))
