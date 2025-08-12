# tasks/management/commands/import_task_assignments.py

import csv
from django.core.management.base import BaseCommand
from tasks.models import Task
from users.models import CustomUser

class Command(BaseCommand):  # ✅ this class must exist and be named Command
    help = 'Import task assignment M2M relationships from CSV'

    def handle(self, *args, **kwargs):
        with open('exported_task_assignments.csv', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    task = Task.objects.get(id=row['task_id'])
                    user = CustomUser.objects.get(id=row['user_id'])
                    task.assigned_employees.add(user)
                    self.stdout.write(f"✅ Linked user {user.id} to task {task.id}")
                except Exception as e:
                    self.stdout.write(f"⚠️ Error linking task {row['task_id']} and user {row['user_id']}: {e}")

        self.stdout.write(self.style.SUCCESS("🎉 Assigned users imported successfully!"))
