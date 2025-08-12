import csv
from django.core.management.base import BaseCommand
from tasks.models import Task, TaskName, Project
from customers.models import Customer
from users.models import CustomUser
from django.utils.dateparse import parse_datetime, parse_date
from django.core.files.base import ContentFile
import os

class Command(BaseCommand):
    help = 'Import Tasks from CSV'

    def handle(self, *args, **kwargs):
        with open('exported_tasks.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            status_map = {
                'completed': 'done',
                'closed undelivered': 'closed',
                'canceled': 'canceled',
                'in_progress': 'in_progress',
                'created': 'created'
            }

            paid_status_map = {
                'P': 'P',
                'U': 'U',
                'O': 'O',
            }

            for row in reader:
                try:
                    task_name = TaskName.objects.get(id=row['task_name_id'])
                    customer = Customer.objects.get(customer_id=row['customer_id'])
                    created_by = CustomUser.objects.get(id=row['created_by_id']) if row['created_by_id'] else None
                    user = CustomUser.objects.get(id=row['project_manager_id']) if row['project_manager_id'] else None
                    pm_closed_by = CustomUser.objects.get(id=row['final_user_id']) if row['final_user_id'] else None
                    project = Project.objects.get(id=row['project_id']) if row['project_id'] else None
                except Exception as e:
                    self.stdout.write(f"⚠️ Error resolving FKs: {e}")
                    continue

                file_field = row['file_name'] if row['file_name'] else None

                task, created = Task.objects.update_or_create(
                    id=row['task_id'],
                    defaults={
                        'task_name': task_name,
                        'order_number': row['order_number'],
                        'status': status_map.get(row['status'], 'created'),
                        'customer_name': customer,
                        'created_by': created_by,
                        'user': user,
                        'project': project,
                        'file_name': file_field,
                        'task_priority': row['task_priority'],
                        'paid_status': paid_status_map.get(row['is_paid'], 'U'),
                        'payment_method': row['payment_method'],
                        'frontdesk_price': row['frontdesk_price'],
                        'final_price': row['final_price'],
                        'discount': row['discount'],
                        'currency': row['currency'],
                        'job_due_date': parse_date(row['job_due_date']) if row['job_due_date'] else None,
                        'quote_validity': parse_date(row['quote_validity']) if row['quote_validity'] else None,
                        'notes': row['notes'],
                        'is_quote': row['is_quote'] == 'True',
                        'closed': row['closed'] == 'True',
                        'pm_closed_by': pm_closed_by,
                        'closed_at': parse_datetime(row['modified_date']) if row['closed'] == 'True' else None,
                        'cancel_requested': row['cancel_request'] == 'True',
                        'canceled': row['canceled'] == 'True',
                        'created_at': parse_datetime(row['creation_date']),
                        'updated_at': parse_datetime(row['modified_date']),
                    }
                )

                self.stdout.write(f"✅ {'Created' if created else 'Updated'} task {task.order_number} (ID {task.id})")

        self.stdout.write(self.style.SUCCESS("🎉 All tasks imported successfully!"))
