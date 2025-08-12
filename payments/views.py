# payments/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from django.db.models import Sum, Q
from django.utils.timezone import now
from decimal import Decimal, ROUND_HALF_UP
from django.contrib import messages
from tasks.utils import notify_user_about_task
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models import Payment, TaskPaymentStatus
from tasks.models import Task
from tasks.decorators import disallow_groups
from .forms import PaymentForm
from tasks.models import TaskActivityLog, CurrencyRate


User = get_user_model()

def get_usd_to_lbp_rate():
    try:
        return CurrencyRate.objects.latest('updated_at').usd_to_lbp
    except CurrencyRate.DoesNotExist:
        return Decimal('0')

@login_required
@disallow_groups(['Graphics'])
def task_table_data(request, status):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    # ✅ Show both 'U' and 'O' when status is 'U'
    if status == 'U':
        queryset = Task.objects.filter(Q(paid_status='U') | Q(paid_status='O'), canceled=False).filter(~Q(status='delivered'))
    else:
        queryset = Task.objects.filter(Q(paid_status=status, canceled=False) | Q(status='delivered'))
    if search_value:
        queryset = queryset.filter(
            Q(task_name__name__icontains=search_value) |
            Q(order_number__icontains=search_value) |
            Q(customer_name__customer_name__icontains=search_value)
        )

    total = queryset.count()
    tasks = queryset[start:start + length]

    data = []
    for task in tasks:
        # Normalize values
        final_price = Decimal(task.final_price or 0).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
        remaining = Decimal(task.remaining_amount or 0).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
        paid = Decimal(task.total_paid_amount or 0).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

        print(f"DEBUG ❗ Task {task.id}: final_price={final_price}, paid={paid}, remaining={remaining}")

        # 💰 Badge logic with popovers
        if final_price == Decimal('0.00'):
            paid_amount_display = (
                '<span class="badge bg-secondary" data-bs-toggle="popover" data-bs-trigger="hover" '
                'title="No Price Set" data-bs-content="Final price has not been set yet.">No Price</span>'
            )
            remain_amount_display = (
                '<span class="badge bg-secondary" data-bs-toggle="popover" data-bs-trigger="hover" '
                'title="No Price Set" data-bs-content="Final price has not been set yet.">No Price</span>'
            )
        elif remaining == Decimal('0.00'):
            paid_amount_display = (
                f'<span class="badge bg-success" data-bs-toggle="popover" data-bs-trigger="hover" '
                f'title="Amount Paid" data-bs-content="Customer has fully paid.">{paid}</span>'
            )
            remain_amount_display = (
                '<span class="badge bg-success" data-bs-toggle="popover" data-bs-trigger="hover" '
                'title="Payment Complete" data-bs-content="No remaining amount.">Paid</span>'
            )
        else:
            if paid == Decimal('0.00'):
                paid_amount_display = (
                    '<span class="badge bg-danger" data-bs-toggle="popover" data-bs-trigger="hover" '
                    'title="Unpaid" data-bs-content="Customer has not paid anything yet.">0</span>'
                )
            else:
                paid_amount_display = (
                    f'<span class="badge bg-success" data-bs-toggle="popover" data-bs-trigger="hover" '
                    f'title="Partial Payment" data-bs-content="Customer has partially paid.">{paid}</span>'
                )
            remain_amount_display = (
                f'<span class="badge bg-danger" data-bs-toggle="popover" data-bs-trigger="hover" '
                f'title="Amount Left " data-bs-content="This amount is still due.">{remaining}</span>'
            )

        task_data = {
        'id': task.id,
        'order_number': task.order_number,
        'task_name': f'<a href="{reverse("tasks:task_detail", args=[task.pk])}">{task.task_name}</a>',
        'status': task.get_status_display(),
        'customer_name': f'<a href="{reverse("customers:customer_detail", args=[task.customer_name.customer_id])}">{task.customer_name}</a>',
        'employees': ', '.join([e.get_full_name() for e in task.assigned_employees.all()]),
        'final_price': task.final_price,
        'paid_amount': paid_amount_display,
        'remain_amount': remain_amount_display,
        'created_at': task.created_at.strftime('%Y-%m-%d %H:%M'),
        'created_by': str(task.created_by),
        'payment_status': task.get_paid_status_display(),
    }

        if status == 'P':
            task_data['actions'] = f'<a href="{reverse("payments:make_payment", args=[task.id])}" class="btn btn-success"><i class="fa-solid fa-eye"></i></a>'
        else:
            task_data['total_paid_amount'] = task.total_paid_amount
            task_data['remaining_amount'] = task.remaining_amount
            task_data['actions'] = f'<a href="{reverse("payments:make_payment", args=[task.id])}" class="btn btn-success"><i class="fa fa-dollar-sign"></i> Make Payment</a>'

        data.append(task_data)

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': data
    })


@disallow_groups(['Graphics'])
@login_required
def unpaid_jobs(request):
    tasks = Task.objects.filter(Q(paid_status='U') | Q(paid_status='O'), canceled=False)
    context = {'tasks':tasks}
    return render(request, 'payments/unpaid.html', context)

@disallow_groups(['Graphics'])
@login_required
def paid_jobs(request):
    tasks = Task.objects.filter(paid_status='P').filter(canceled=False)
    context = {'tasks':tasks}
    return render(request, 'payments/paid.html', context)

@disallow_groups(['Graphics'])
@login_required
def make_payment(request, task_id):
    # Fetch the task object
    task = get_object_or_404(Task, id=task_id)

    # Calculate total paid so far across all payments linked to this task
    paid_so_far = Payment.objects.filter(task=task).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate how much remains to be paid
    remaining = task.final_price - paid_so_far

    # Handle currency conversion for UI display (assumes get_usd_to_lbp_rate() returns numeric value)
    usd_to_lbp = get_usd_to_lbp_rate()
    if task.currency == "USD":
        final_price_lbp = task.final_price * usd_to_lbp
        paid_so_far_lbp = paid_so_far * usd_to_lbp
        remain_amount_lbp = remaining * usd_to_lbp
    else:
        final_price_lbp = task.final_price
        paid_so_far_lbp = paid_so_far
        remain_amount_lbp = remaining

    if request.method == 'POST':
        if request.POST.get('fix_overpaid') == '1':
            paid_so_far = Payment.objects.filter(task=task).aggregate(total=Sum('amount'))['total'] or 0
            old_price = task.final_price
            task.final_price = paid_so_far
            task.save(update_fields=['final_price'])

            if hasattr(task, 'payment_status'):
                task.payment_status.update_status()

            if task.payment_status.is_fully_paid:
                task.paid_status = 'P'
                task.save(update_fields=['paid_status'])

            TaskActivityLog.objects.create(
                task=task,
                user=request.user,
                action="🛠 Fixed Overpaid Task",
                note=f"Adjusted final price from {old_price} to {paid_so_far} to resolve overpayment"
            )

            messages.success(request, "Overpayment resolved: final price adjusted to match payments.")
            return redirect(request.path)

        if request.POST.get("cancel_last_payment") == "1":
            last_payment = Payment.objects.filter(task=task).order_by('-paid_at').first()
            if last_payment:
                amount = last_payment.amount
                last_payment.delete()

                # Recalculate status
                TaskPaymentStatus.objects.get_or_create(task=task)[0].update_status()
                task.refresh_from_db()

                if task.final_price > 0 and (
                    Payment.objects.filter(task=task).aggregate(total=Sum('amount'))['total'] or 0
                ) < task.final_price:
                    task.paid_status = 'U'
                    task.save(update_fields=['paid_status'])

                TaskActivityLog.objects.create(
                    task=task,
                    user=request.user,
                    action="❌ Canceled Last Payment",
                    note=f"Canceled payment of {amount} {task.currency}"
                )
                messages.warning(request, f"Last payment of {amount} {task.currency} has been canceled.")
            else:
                messages.error(request, "No payment found to cancel.")
            return redirect(request.path)
    
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.task = task
            payment.paid_by = request.user
            payment.paid_at = now()

            # --- HANDLE PAYMENT TYPE VALIDATION ---

            if payment.payment_type == 'full':
                # Full payment must match the remaining amount exactly
                if remaining <= 0:
                    messages.error(request, "This task is already fully paid.")
                    return redirect(request.path)

                payment.amount = remaining  # Enforce exact remaining value
            elif payment.payment_type == 'down':
                # Prevent overpaying through down payments
                if payment.amount > remaining:
                    messages.error(request, f"Down payment exceeds remaining amount ({remaining:.2f} {task.currency}).")
                    return redirect(request.path)

            # Save payment
            payment.save()

            payment_status, created = TaskPaymentStatus.objects.get_or_create(task=task)
            payment_status.update_status()

            # --- ACTIVITY LOG ---
            TaskActivityLog.objects.create(
                task=task,
                user=request.user,
                action="Full Payment" if payment.payment_type == "full" else "Down Payment",
                note=f"Amount: {payment.amount} {task.currency}",
            )

            # Who should be notified
            manager_groups = Group.objects.filter(name__in=["ManagerAssistant", "FrontDesk"])
            managers = User.objects.filter(groups__in=manager_groups)

            assigned_users = task.assigned_employees.all()
            subtask_users = User.objects.filter(subtasks__task=task).distinct()

            from itertools import chain

            all_users = set(chain(
                managers,
                assigned_users,
                subtask_users
            ))

            # Remove the user who made the payment
            all_users.discard(request.user)

            # Define the notification message
            payment_status = "fully" if task.paid_status == "P" else "Down Payment"
            message = f"Task #{task.id} has {payment_status} paid."

            # Notify all relevant users
            for user in all_users:
                notify_user_about_task(user, task, message, type_name="Payment")

            messages.success(request, "Payment recorded successfully.")
            return redirect('payments:unpaid_jobs')
    else:
        form = PaymentForm()

    return render(request, 'payments/make-payment.html', {
        'form': form,
        'task': task,
        'paid_so_far': paid_so_far,
        'final_price_lbp': final_price_lbp,
        'paid_so_far_lbp': paid_so_far_lbp,
        'usd_to_lbp': usd_to_lbp,
        'remain_amount_lbp': remain_amount_lbp,
    })