import csv
from django.core.management.base import BaseCommand
from tasks.models import Subtask, Task, TaskName, Vat
from users.models import CustomUser
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Import Subtasks from CSV'

    def handle(self, *args, **kwargs):
        with open('exported_subtasks.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    task = Task.objects.get(id=row['main_task_id'])
                    name = TaskName.objects.get(id=row['subtask_name_id']) if row['subtask_name_id'] else None
                    user = CustomUser.objects.get(id=row['user_id']) if row['user_id'] else None
                    vat = Vat.objects.get(value=row['vat']) if row['vat'] else None
                except Exception as e:
                    self.stdout.write(f"⚠️ FK resolution error: {e}")
                    continue

                sub, created = Subtask.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'task': task,
                        'name': name,
                        'user': user,
                        'discount': row['discount'],
                        'currency': row['currency'],
                        'subtask_amount': row['subtask_amount'],
                        'vat': vat,
                        'job_is_zero': row['job_is_zero'] == 'True',
                        'is_done': row['done'] == 'True',
                        'is_project_manager': row['project_manager'] == 'True',
                        'location': row['job_location'],
                        'notes_from_top': row['notes'],
                        'notes_from_operator': row['note_cashier'],
                        'created_at': parse_datetime(row['creation_date']),
                        'finished_at': parse_datetime(row['finished_date']),
                    }
                )

                self.stdout.write(f"✅ {'Created' if created else 'Updated'} subtask ID {sub.id}")

        self.stdout.write(self.style.SUCCESS("🎉 All subtasks imported successfully"))
