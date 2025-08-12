# core/models/base.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from customers.models import Customer
from custom_email.models import Email
from django.contrib.auth import get_user_model 
from decimal import Decimal
import datetime
User = get_user_model()


class CurrencyRate(models.Model):
    usd_to_lbp = models.DecimalField(max_digits=20, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"1 USD = {self.usd_to_lbp} LBP (updated {self.updated_at:%Y-%m-%d %H:%M})"


CURRENCY_CHOICES = [
    ('LBP', 'LBP'),
    ('USD', 'USD'),
]
# ------- VAT -------
class Vat(models.Model):
    name = models.CharField(max_length=200, default="Taxname")
    value = models.PositiveIntegerField(default=11, unique=True)

    def __str__(self):
        return f"{self.name} ({self.value}%)"

    class Meta:
        verbose_name_plural = "VAT"

class Branch(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name
# ------- Project -------
class Project(models.Model):
    name = models.CharField(max_length=200)
    project_number = models.CharField(max_length=20, null=True, blank=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    spent = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Auto-fill project_number only once after first save
        if is_new and not self.project_number:
            self.project_number = f"PRJ{self.pk}"
            super().save(update_fields=['project_number'])


    @property
    def paid_project_amount(self):
        from payments.models import TaskPaymentStatus, Payment
        """Sum of all actual payment amounts from related tasks."""
        return Payment.objects.filter(task__project=self).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')


    @property
    def unpaid_project_amount(self):
        from payments.models import TaskPaymentStatus, Payment
        """Sum of all (final_price - paid_amount) for tasks in this project."""
        tasks = Task.objects.filter(project=self).select_related('payment_status')
        total_unpaid = Decimal('0.00')

        for task in tasks:
            if hasattr(task, 'payment_status'):
                unpaid = task.final_price - task.payment_status.paid_amount
                if unpaid > 0:
                    total_unpaid += unpaid
            else:
                total_unpaid += task.final_price  # No payment yet

        return total_unpaid


    @property
    def overpaid_amount(self):
        from payments.models import TaskPaymentStatus, Payment
        """Sum of extra paid amounts if any tasks are overpaid."""
        tasks = Task.objects.filter(project=self).select_related('payment_status')
        overpaid = Decimal('0.00')

        for task in tasks:
            if hasattr(task, 'payment_status'):
                extra = task.payment_status.paid_amount - task.final_price
                if extra > 0:
                    overpaid += extra

        return overpaid
    
    @property
    def total_project_amount(self):
        """Returns the total of all final_price values for tasks in this project."""
        total = self.task_set.aggregate(
            total=Sum('final_price')
        )['total'] or Decimal('0.00')
        return total

        def __str__(self):
            return self.name

# ------- Task Name -------
class TaskName(models.Model):
    name = models.CharField(max_length=350, unique=True)
    code = models.CharField(max_length=30, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ------- Task -------
class Task(models.Model):

    PRIORITY_CHOICES = [
        ('Urgent', 'Urgent'),
        ('Normal', 'Normal'),
    ]

    STATUS_CHOICES = [
        ('created', 'Created'),
        ('in_progress', 'In Progress'),
        ('done', 'All Subtasks Done'),
        ('closed', 'Closed'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
    ]

    PAID_STATUS_CHOICES = [
        ('P', 'Paid'),
        ('U', 'Unpaid'),
        ('O', 'Overpaid'),
    ]

    PAYMENT_METHODS = [
        ('DO', 'DO'),
        ('Invoice', 'Invoice'),
        ('Wallet', 'Wallet (Wish, OMT, ETC...)'),
        ('cash', 'Cash'),
    ]

    FINAL_LOCATION = [
        ('FRONT DESK', 'FRONT DESK'),
        ('OPERATOR DESK', 'OPERATOR DESK'),
        ('BEHIND KHALED', 'BEHIND KHALED'),

    ]

    task_name = models.ForeignKey(TaskName, on_delete=models.PROTECT)
    order_number = models.CharField(max_length=1000, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', db_index=True)

    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.OneToOneField(Email, null=True, blank=True, on_delete=models.SET_NULL, related_name='task')
    customer_name = models.ForeignKey(Customer, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_employees = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='assigned_tasks')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="managed_tasks")
    file_name = models.FileField(upload_to='projects_files', null=True, blank=True)
    
    frontdesk_price = models.DecimalField(max_digits=20, decimal_places=2, default=0, blank=True)
    final_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    discount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")
    task_priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Normal')
    paid_status = models.CharField(max_length=1, choices=PAID_STATUS_CHOICES, default='U')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='cash')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    job_due_date = models.DateField(default=datetime.date.today)
    quote_validity = models.DateField(blank=True, null=True)

    final_location = models.CharField(max_length=100, choices=FINAL_LOCATION, blank=True, null=True, help_text="Predefined location")
    other_location = models.CharField(max_length=100, blank=True, null=True, help_text="Custom location (used only if final_location is not selected)")

    notes = models.TextField()
    is_quote = models.BooleanField(default=False)
    pm_closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='closed_tasks_as_pm', on_delete=models.SET_NULL)
    closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    from_email = models.BooleanField(default=False)
    cancel_requested = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['paid_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['order_number']),
            models.Index(fields=['customer_name', 'status']),
        ]

    def __str__(self):
        """
        Returns a human-readable string representation of the task.
        Format: "Task {id}: {task_name} for {customer_name}"
        """
        return f"Task {self.id}: {self.task_name.name} for {self.customer_name.customer_name}"
    
    @property
    def is_created_by_current_user(self):
        """
        Checks if the current user is the creator of this task.
        Returns:
            bool: True if current user matches created_by, False otherwise.
            Returns False if no request/user is available.
        """
        try:
            from crum import get_current_user
            current_user = get_current_user()
            if current_user and current_user.is_authenticated:
                return current_user == self.created_by
            return False
        except Exception:
            return False

    def total_employees(self):
        """
        Calculates the number of unique employees assigned to subtasks of this task.
        Returns:
            int: Count of distinct users with subtasks.
        """
        return self.subtasks.values('user').distinct().count()
    
    def calculate_final_price(self):
        """
        Calculates the total price of the task by summing:
        - Total price of all subtasks (including VAT and discounts)
        - Frontdesk price
        Returns:
            Decimal: Total calculated price of the task.
        """
        subtask_total = sum(s.total_price() for s in self.subtasks.all())
        return subtask_total + self.frontdesk_price
    
    @property
    def resolved_final_location(self):
        return self.final_location or self.other_location

    @property
    def requires_pricing(self):
        return self.final_price == 0

    @property
    def total_paid_amount(self):
        total = self.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        return total

    @property
    def is_fully_paid(self):
        return self.final_price and self.total_paid_amount >= self.final_price
    
    @property
    def badge_color(self):
        if self.remaining_amount == 0:
            return 'success'
        elif self.final_price > 0:
            return 'danger'
        return 'secondary'
    
    @property
    def remaining_amount(self):
        remaining = self.final_price - self.total_paid_amount
        # prevent negative remaining in case of overpayment
        return remaining if remaining > 0 else 0
    
    def check_all_subtasks_done(self):
        """
        Checks if all subtasks of this task are marked as done.
        Returns:
            bool: True if no undone subtasks exist, False otherwise.
        """
        return not self.subtasks.filter(is_done=False).exists()

    def all_subtasks_resolved(self):
        """
        Checks if all subtasks are either closed or canceled.
        Returns:
            bool: True if all subtasks are resolved, False otherwise.
        """
        return all(sub.is_done or sub.is_canceled for sub in self.subtasks.all())

    def can_be_closed_by_pm(self):
        """
        Determines if the task can be closed by the project manager.
        Conditions:
        - Task must be paid (paid_status == 'P')
        - All subtasks must be resolved (closed or canceled)
        Returns:
            bool: True if task can be closed by PM, False otherwise.
        """
        return self.paid_status == 'P' and self.all_subtasks_resolved()

    @property
    def get_price_in_lbp(self):
        if self.currency == 'LBP':
            return self.final_price
        try:
            rate = CurrencyRate.objects.latest('updated_at').usd_to_lbp
            return self.final_price * rate
        except (CurrencyRate.DoesNotExist, AttributeError):
            return Decimal(0)

    @property
    def is_paid(self):
        """
        Checks if the task is fully paid.
        Returns:
            bool: True if paid_status is 'P' (Paid), False otherwise.
        """
        return self.paid_status == 'P'

    @property
    def subtasks(self):
        """
        Returns all subtasks related to this task.
        Returns:
            QuerySet: Subtask objects linked to this task.
        """
        return self.subtask_set.all()

    @property
    def is_project_manager_done(self):
        """
        Checks if the project manager has at least one subtask marked as done.
        Returns:
            bool: True if the project manager has any done subtask, False otherwise.
        """
        if not self.user:
            return False  # No project manager assigned
        return self.subtasks.filter(user=self.user, is_done=True).exists()

    @property
    def get_all_subtasks_progess_percentage(self):
        """
        Calculates the percentage of employees who have completed at least one subtask.
        Logic:
        - Total employees = total_employees()
        - Done employees = users with at least one done subtask
        - Percentage = (done_employees / total_employees) * 100
        Returns:
            int: Percentage of employees with completed subtasks (0 if no employees).
        """
        total_employees = self.total_employees()
        if total_employees == 0:
            return 0  # Avoid division by zero
        done_employees = self.subtasks.filter(is_done=True).values('user').distinct().count()
        return int((done_employees / total_employees) * 100)

    def can_be_closed(self):
        """
        Determines if the task can be closed.
        Conditions:
        - All subtasks must be done (check_all_subtasks_done())
        - Task must be paid (is_paid)
        Returns:
            bool: True if task can be closed, False otherwise.
        """
        return self.check_all_subtasks_done() and self.is_paid
    
    def can_user_assign_operator(self, user):
        has_delivered = hasattr(self, 'deliveredtask')
        return (
            user in self.assigned_employees.all() and
            self.subtasks.filter(user=user, is_done=True).exists() and
            not has_delivered and
            not self.canceled and
            not self.closed
        )
        
    @property
    def is_delivered(self):
        return DeliveredTask.objects.filter(main_task=self).exists()
    
    # def save(self, *args, **kwargs):
    #     if self.is_second_branch():
    #         self.final_price = Decimal('0.00')
    #         self.paid_status = 'P'
    #     super().save(*args, **kwargs)

    # def clean(self):
    #     if self.is_second_branch() and self.final_price > 0:
    #         raise ValidationError("Tasks from the second branch must be free (final_price = 0).")

    

# ------- Subtask -------
class Subtask(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    name = models.ForeignKey(TaskName, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='subtasks')
    is_done = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False) #not used
    is_project_manager = models.BooleanField(default=False)

    cancel_requested = models.BooleanField(default=False)
    is_canceled = models.BooleanField(default=False)
    cancel_subtask_reason = models.TextField(null=True, blank=True)

    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_subtasks')
    parent_subtask = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_subtasks')

    subtask_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    discount = models.PositiveIntegerField(default=0)
    vat = models.ForeignKey(Vat, on_delete=models.SET_NULL, null=True)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default="USD")
    job_is_zero = models.BooleanField(default=False)

    location = models.CharField(max_length=255, blank=True)
    notes_from_top = models.TextField()
    notes_from_operator = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(auto_now=True)
    is_updated = models.BooleanField(default=False)
    is_highlighted = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['task', 'is_done']),
            models.Index(fields=['user', 'is_done']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.task} - {self.name} - {self.user}"
    
    def total_price(self):
        discount_factor = Decimal(1) - (Decimal(self.discount) / Decimal(100))
        vat_multiplier = Decimal(1)
        if self.vat:
            vat_multiplier = Decimal(1) + (Decimal(self.vat.value) / Decimal(100))
            discounted = self.subtask_amount * discount_factor
            return discounted * vat_multiplier

    def clean(self):
        if self.is_canceled and self.is_done:
            raise ValidationError("Canceled subtask cannot be marked as done.")



class NotificationType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)  # ✅ Must have this
    message = models.TextField()
    type = models.ForeignKey(NotificationType, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    extra_data = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Notification for {self.user.email}: {self.message[:30]}"
    
# ------- Delivered -------
class DeliveredTask(models.Model):
    main_task = models.OneToOneField(Task, on_delete=models.CASCADE, null=True, blank=True)
    delivered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='delivered_by')
    received_person = models.CharField(max_length=255, null=True, blank=True)
    is_delivered = models.BooleanField(default=False)
    delivery_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='created_by')
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.main_task)

    class Meta:
        ordering = ["-delivery_date"]
   
# ----------------- TaskActivityLog (Optional but Recommended) -----------------
class TaskActivityLog(models.Model):
    task = models.ForeignKey(Task, related_name='activity_logs', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.timestamp} | {self.user} | {self.action}"
    
    class Meta:
        ordering = ['timestamp']  # newest first
    
