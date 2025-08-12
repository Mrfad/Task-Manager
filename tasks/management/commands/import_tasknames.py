import csv
from django.core.management.base import BaseCommand
from tasks.models import TaskName
from users.models import CustomUser
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Import TaskName from CSV'

    def handle(self, *args, **kwargs):
        with open('exported_tasknames.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    created_by = CustomUser.objects.get(id=row['created_by_id']) if row['created_by_id'] else None
                except CustomUser.DoesNotExist:
                    created_by = None

                TaskName.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'name': row['name'],
                        'code': row['code'],
                        'created_by': created_by,
                        'creation_date': parse_datetime(row['creation_date']),
                        'modified_date': parse_datetime(row['modified_date']),
                    }
                )

        self.stdout.write(self.style.SUCCESS("✅ Task names imported"))
