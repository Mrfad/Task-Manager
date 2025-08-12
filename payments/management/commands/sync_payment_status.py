from django.core.management.base import BaseCommand
from django.db.models import Sum
from tasks.models import Task
from payments.models import TaskPaymentStatus, Payment
from decimal import Decimal

class Command(BaseCommand):
    help = 'Syncs payment statuses for tasks based on their payment records'

    def handle(self, *args, **options):
        # Find all tasks with payments
        tasks_with_payments = Task.objects.filter(
            payments__isnull=False
        ).distinct()

        self.stdout.write(f"Found {tasks_with_payments.count()} tasks with payments")

        processed_count = 0
        updated_count = 0

        for task in tasks_with_payments:
            self.stdout.write(f"\nProcessing Task ID: {task.id} - {task.task_name}")

            # Get or create payment status
            payment_status, created = TaskPaymentStatus.objects.get_or_create(task=task)
            if created:
                processed_count += 1
                self.stdout.write("  - Created new payment status record")
            else:
                self.stdout.write("  - Updating existing payment status record")

            # Calculate total paid amount
            payments = task.payments.all()
            total_paid = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            payment_status.paid_amount = total_paid

            # Determine payment status based on payment types
            has_full_payment = payments.filter(payment_type='full').exists()
            has_down_payment = payments.filter(payment_type='down').exists()

            if has_full_payment:
                payment_status.is_fully_paid = True
                payment_status.is_down_payment_only = False
                self.stdout.write(f"  - Marked as FULLY PAID (Full payment exists)")
            elif has_down_payment:
                payment_status.is_fully_paid = False
                payment_status.is_down_payment_only = True
                self.stdout.write(f"  - Marked as DOWN PAYMENT ONLY")
            else:
                # Handle case where payment type isn't specified
                if total_paid >= task.final_price:
                    payment_status.is_fully_paid = True
                    payment_status.is_down_payment_only = False
                    self.stdout.write(f"  - Marked as FULLY PAID by amount ({total_paid}/{task.final_price})")
                elif total_paid > 0:
                    payment_status.is_fully_paid = False
                    payment_status.is_down_payment_only = True
                    self.stdout.write(f"  - Marked as PARTIAL PAYMENT by amount ({total_paid}/{task.final_price})")
                else:
                    payment_status.is_fully_paid = False
                    payment_status.is_down_payment_only = False
                    self.stdout.write("  - No valid payments found")

            payment_status.save()
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nSuccessfully processed {processed_count} new records and updated {updated_count} records!"
        ))