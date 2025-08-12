import csv
from django.core.management.base import BaseCommand
from payments.models import Payment, TaskPaymentStatus
from tasks.models import Task
from users.models import CustomUser
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Import payments into new Payment model'

    def handle(self, *args, **kwargs):
        with open('exported_payments.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    task = Task.objects.get(id=row['task_id'])
                    paid_by = CustomUser.objects.get(id=row['cashier_id']) if row['cashier_id'] else None
                except Exception as e:
                    self.stdout.write(f"⚠️ FK error: {e}")
                    continue

                payment, created = Payment.objects.update_or_create(
                    task=task,
                    amount=row['amount'],
                    payment_type=row['type'],
                    paid_by=paid_by,
                    defaults={
                        'paid_at': parse_datetime(row['paid_at']) if row['paid_at'] else None
                    }
                )

                self.stdout.write(f"✅ {payment.payment_type.title()} payment imported for task {task.id}")

        self.stdout.write(self.style.SUCCESS("🎉 Payments imported!"))
