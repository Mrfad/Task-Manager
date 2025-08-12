# payments/utils/payments_utils.py
from decimal import Decimal
from django.db.models import Sum
from payments.models import Payment, TaskPaymentStatus

def update_payment_summary(task):
    """
    Recalculate and update only TaskPaymentStatus:
    - paid_amount
    - is_fully_paid
    - is_down_payment_only

    Does NOT modify the Task model or create Payment records.
    """

    total_paid = (
        Payment.objects.filter(task=task)
        .exclude(amount=0)  # Optional: skip 0-amount audit logs
        .aggregate(total=Sum('amount'))['total'] or Decimal('0')
    )

    status, _ = TaskPaymentStatus.objects.get_or_create(task=task)
    status.paid_amount = total_paid
    status.is_fully_paid = total_paid >= task.final_price
    status.is_down_payment_only = 0 < total_paid < task.final_price
    status.save(update_fields=['paid_amount', 'is_fully_paid', 'is_down_payment_only'])

