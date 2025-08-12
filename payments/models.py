# payments/models.py
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

class Payment(models.Model):
    from tasks.models import Task
    PAYMENT_TYPE_CHOICES = [
        ('down', 'Down Payment'),
        ('full', 'Full Payment'),
    ]

    PAYMENT_METHODS = [
        ('DO', 'DO'),
        ('Invoice', 'Invoice'),
        ('Wallet', 'Wallet (Wish, OMT, ETC...)'),
        ('cash', 'Cash'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='cash')
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)
    def __str__(self):
        return f"{self.task} - {self.payment_type} - {self.amount}"


class TaskPaymentStatus(models.Model):
    from tasks.models import Task
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='payment_status')
    # total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_fully_paid = models.BooleanField(default=False)
    is_down_payment_only = models.BooleanField(default=False)

    updated = models.DateTimeField(auto_now=True)


    # In payments/models.py inside TaskPaymentStatus class
    def update_status(self):
        payments = self.task.payments.all()
        total_paid = sum([p.amount for p in payments])
        self.paid_amount = total_paid

        self.is_fully_paid = total_paid >= self.task.final_price
        self.is_down_payment_only = 0 < total_paid < self.task.final_price
        self.save()

        # ✅ Update paid_status on the Task model too
        if total_paid == self.task.final_price:
            self.task.paid_status = 'P'
        elif total_paid > self.task.final_price:
            self.task.paid_status = 'O'
        elif total_paid > 0:
            self.task.paid_status = 'U'
        else:
            self.task.paid_status = 'U'

        self.task.save(update_fields=['paid_status'])


    def __str__(self):
        return f"{self.task} - Paid: {self.paid_amount}/{self.task.final_price}"
