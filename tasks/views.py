from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.urls import reverse
from urllib.parse import urlencode
from django.db.models import Sum, Count, Q, Exists, OuterRef, Max, Prefetch, Subquery, CharField, Value, Case, When, Min, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from customers.models import Customer, CountryCodes
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from django.conf import settings
from django.utils.text import slugify
from tasks.utilities.navigation import get_back_url
from email.utils import parseaddr
from .models import Task, TaskName, Subtask, TaskName, TaskActivityLog, DeliveredTask, CurrencyRate, Project, Branch
from .forms import (TaskForm, SubtaskForm, UpdateSubtaskForm, 
                    RateForm, DeliveredTaskForm, RequestCancelSubtaskForm, 
                    CloseTaskForm, projectForm)
from payments.models import Payment, TaskPaymentStatus
from payments.utils.payments_utils import update_payment_summary
from .utils import *
from .buttons_export import export_tasks_to_excel, export_tasks_to_pdf
from custom_email.models import Email
import tldextract
from tasks.decorators import disallow_groups
from activity_logs.models import ActivityLog
from customers.views import log_activity
import logging
import random
from datetime import datetime, date
from django.utils import timezone
from django.utils.timezone import now
from django.db.models.functions import ExtractYear
import calendar
import os



User = get_user_model()
logger = logging.getLogger(__name__)

# AJAX Call TO GET THE CUSTOMER RELATED TO SELECTED PROJECT
def get_customer_by_project(request):
    project_id = request.GET.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
        customer = project.customer
        return JsonResponse({
            'customer_id': customer.customer_id,  # Make sure this matches your model's PK field name
            'customer_name': f"{customer.customer_name} - {customer.customer_phone}"
        })
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def clear_task_notifications(request):
    Notification.objects.filter(user=request.user, is_read=False).exclude(type__name='payment').update(is_read=True)
    return JsonResponse({'status': 'success'})

@require_POST
@login_required
def clear_payment_notifications(request):
    Notification.objects.filter(user=request.user, is_read=False, type__name='payment').update(is_read=True)
    return JsonResponse({'status': 'success'})

def custom_permission_denied_view(request, exception=None):
    return render(request, '403.html', status=403)


def download(request, path):
    file_path=os.path.join(settings.MEDIA_ROOT,path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response=HttpResponse(fh.read(),content_type="application/file_name")
            response['Content-Disposition']='inline;filename='+os.path.basename(file_path)
            return response
    raise Http404

def error_404_view(request, exception):
    return render(request, '404.html',{})

def handle_server_error(request):
    return render(request, 'page_500.html')

@disallow_groups(['Graphics'])
@login_required
def change_rate(request):
    usd_to_lbp = CurrencyRate.objects.get(id=1)
    rate_form = RateForm(instance=usd_to_lbp)
    if request.method == 'POST':
        rate_form = RateForm(request.POST, instance=usd_to_lbp)
        rate_form.save()
        messages.success(request, 'Rate Changed Successfuly')
        return redirect('tasks:all_tasks')
    context = {"rate_form":rate_form}
    return render(request, 'tasks/change-rate.html', context)



#################################
######################### Start Statisrtics section ###########################
def get_random_color():
    return '#' + ''.join(random.choices('0123456789ABCDEF', k=6))

@disallow_groups(['Cashier'])
@login_required
def stats(request):
    from django.db.models import Sum

    year_number = datetime.now().year

    users = User.objects.filter(
        Q(groups__name__in=[
            'Graphic', 'Laser', 'Outdoor', 'Typing', 'ManagerAssistant'
        ]),
        is_active=True
    ).distinct()

    user_statsusd = []
    user_statslbp = []

    for user in users:
        usd_total = Task.objects.filter(
            user=user,
            created_at__year=year_number,
            currency='USD'
        ).aggregate(total=Sum('final_price'))['total'] or 0

        lbp_total = Task.objects.filter(
            user=user,
            created_at__year=year_number,
            currency='LBP'
        ).aggregate(total=Sum('final_price'))['total'] or 0

        user_statsusd.append({'user': user, 'final_price': round(usd_total, 2)})
        user_statslbp.append({'user': user, 'final_price': round(lbp_total, 2)})

    # Monthly totals
    month_statsusd = [
        {
            'month': m,
            'Amount': Task.objects.filter(
                created_at__year=year_number,
                created_at__month=m,
                currency='USD'
            ).aggregate(total=Sum('final_price'))['total'] or 0
        } for m in range(1, 13)
    ]

    month_statslbp = [
        {
            'month': m,
            'Amount': Task.objects.filter(
                created_at__year=year_number,
                created_at__month=m,
                currency='LBP'
            ).aggregate(total=Sum('final_price'))['total'] or 0
        } for m in range(1, 13)
    ]

    usd_colors = [get_random_color() for _ in user_statsusd]
    lbp_colors = [get_random_color() for _ in user_statslbp]

    context = {
        "year_number": year_number,
        "user_statsusd": user_statsusd,
        "user_statslbp": user_statslbp,
        "month_statsusd": month_statsusd,
        "month_statslbp": month_statslbp,
        'usd_colors': usd_colors,
        'lbp_colors': lbp_colors,
        'nav_title': 'Statistics',
    }

    return render(request, 'tasks/stats/stats-year.html', context)


@disallow_groups(['Cashier'])
@login_required
def stats_month(request, month_number):
    users = User.objects.filter(
        Q(groups__name='Graphic') | Q(groups__name='Laser') | 
        Q(groups__name='Outdoor') | Q(groups__name='Typing') | 
        Q(groups__name='Outdoor') | Q(groups__name='ManagerAssistant') |
        Q(groups__name='Typing'), is_active=True).distinct()
    user_statsusd = []
    user_statslbp = []

    if str(month_number) in [str(i) for i in range(1, 13)]:
        for user in users:
            tasksusd = Task.objects.filter(user=user, currency='USD', created_at__month=month_number)
            total_usd = sum(task.final_price for task in tasksusd)
            user_statsusd.append({'user': user, 'final_price': total_usd})

            taskslbp = Task.objects.filter(user=user, currency='LBP', created_at__month=month_number)
            total_lbp = sum(task.final_price for task in taskslbp)
            user_statslbp.append({'user': user, 'final_price': total_lbp})

    # ✅ Now it's safe to generate colors
    usd_colors = [get_random_color() for _ in user_statsusd]
    lbp_colors = [get_random_color() for _ in user_statslbp]

    context = {
        "month_number": month_number,
        'user_statsusd': user_statsusd,
        'user_statslbp': user_statslbp,
        'usd_colors': usd_colors,
        'lbp_colors': lbp_colors,
        'nav_title': 'Statistics',
    }
    return render(request, 'tasks/stats/stats-month.html', context)

@disallow_groups(['Cashier'])
@login_required
def stats_quarter(request, quarter_number):
    from calendar import monthrange
    from django.db.models import Sum
    year_number = datetime.now().year
    quarter_number = int(quarter_number)
    month_map = {
        1: [1, 2, 3],
        2: [4, 5, 6],
        3: [7, 8, 9],
        4: [10, 11, 12],
    }
    months = month_map.get(quarter_number, [])

    users = User.objects.filter(
        Q(groups__name__in=[
            'Graphic', 'Laser', 'Outdoor', 'Typing', 'ManagerAssistant'
        ]),
        is_active=True
    ).distinct()

    quarter_statsusd = []
    quarter_statslbp = []

    for user in users:
        usd_total = Task.objects.filter(
            user=user,
            created_at__year=year_number,
            created_at__month__in=months,
            currency='USD'
        ).aggregate(total=Sum('final_price'))['total'] or 0

        lbp_total = Task.objects.filter(
            user=user,
            created_at__year=year_number,
            created_at__month__in=months,
            currency='LBP'
        ).aggregate(total=Sum('final_price'))['total'] or 0

        quarter_statsusd.append({
            'user': user,
            'total_final_price': round(usd_total, 2),
        })
        quarter_statslbp.append({
            'user': user,
            'total_price_with_vat_with_discount_designer': round(lbp_total, 2),
        })

    # Month totals for each currency (like before)
    month_usd = [
        {
            'month': month,
            'Amount': Task.objects.filter(
                created_at__year=year_number,
                created_at__month=month,
                currency='USD'
            ).aggregate(total=Sum('final_price'))['total'] or 0
        }
        for month in months
    ]

    month_lbp = [
        {
            'month': month,
            'Amount': Task.objects.filter(
                created_at__year=year_number,
                created_at__month=month,
                currency='LBP'
            ).aggregate(total=Sum('final_price'))['total'] or 0
        }
        for month in months
    ]

    context = {
        "year_number": year_number,
        "quarter_number": quarter_number,
        "quarter_statsusd": quarter_statsusd,
        "quarter_statslbp": quarter_statslbp,
        "month_usd": month_usd,
        "month_lbp": month_lbp,
        'nav_title': 'Statistics',
    }
    return render(request, 'tasks/stats/stats-quarter.html', context)

@disallow_groups(['Cashier'])
@login_required
def stats_year(request, year_number):
    from django.db.models import Sum

    year_number = int(year_number)

    users = User.objects.filter(
        Q(groups__name__in=[
            'Graphic', 'Laser', 'Outdoor', 'Typing', 'ManagerAssistant'
        ]),
        is_active=True
    ).distinct()

    user_statsusd = []
    user_statslbp = []

    for user in users:
        usd_total = Task.objects.filter(
            user=user,
            created_at__year=year_number,
            currency='USD'
        ).aggregate(total=Sum('final_price'))['total'] or 0

        lbp_total = Task.objects.filter(
            user=user,
            created_at__year=year_number,
            currency='LBP'
        ).aggregate(total=Sum('final_price'))['total'] or 0

        user_statsusd.append({'user': user, 'final_price': round(usd_total, 2)})
        user_statslbp.append({'user': user, 'final_price': round(lbp_total, 2)})

    # Monthly totals (for monthly bar charts)
    month_statsusd = [
        {
            'month': m,
            'Amount': Task.objects.filter(
                created_at__year=year_number,
                created_at__month=m,
                currency='USD'
            ).aggregate(total=Sum('final_price'))['total'] or 0
        } for m in range(1, 13)
    ]

    month_statslbp = [
        {
            'month': m,
            'Amount': Task.objects.filter(
                created_at__year=year_number,
                created_at__month=m,
                currency='LBP'
            ).aggregate(total=Sum('final_price'))['total'] or 0
        } for m in range(1, 13)
    ]

    usd_colors = [get_random_color() for _ in user_statsusd]
    lbp_colors = [get_random_color() for _ in user_statslbp]

    context = {
        "year_number": year_number,
        "user_statsusd": user_statsusd,
        "user_statslbp": user_statslbp,
        "month_statsusd": month_statsusd,
        "month_statslbp": month_statslbp,
        'usd_colors': usd_colors,
        'lbp_colors': lbp_colors,
        'nav_title': 'Statistics',
    }
    return render(request, 'tasks/stats/stats-year.html', context)

######################### End Statisrtics section ###########################

@login_required()
def home(request):
    context = {
    }
    return render(request,'home.html', context)

@disallow_groups(['Cashier'])
@login_required
def export_excel(request):
    queryset = Task.objects.select_related('task_name', 'customer_name')
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__customer_name__icontains=search_query)
        )
    sort_by = request.GET.get('sort', '-id')
    allowed_sorts = ['id', '-id', 'order_number', '-order_number', 'task_name__name', '-task_name__name', 'status', '-status', 'customer_name__customer_name', '-customer_name__customer_name']
    if sort_by in allowed_sorts:
        queryset = queryset.order_by(sort_by)

    return export_tasks_to_excel(queryset)


@disallow_groups(['Cashier'])
@login_required
def export_pdf(request):
    queryset = Task.objects.select_related('task_name', 'customer_name')
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__customer_name__icontains=search_query)
        )
    sort_by = request.GET.get('sort', '-id')
    allowed_sorts = ['id', '-id', 'order_number', '-order_number', 'task_name__name', '-task_name__name', 'status', '-status', 'customer_name__customer_name', '-customer_name__customer_name']
    if sort_by in allowed_sorts:
        queryset = queryset.order_by(sort_by)

    return export_tasks_to_pdf(queryset)

@disallow_groups(['Cashier'])
@login_required
def all_tasks(request, query=None):
    user = request.user
    current_year = int(request.GET.get('year', now().year))
    search_query = request.GET.get('search', '')
    per_page = request.GET.get('per_page', '10')
    page = request.GET.get('page', 1)
    sort_by = request.GET.get('sort', '-id')

    target_group_names = ['Typing', 'Graphic', 'Outdoor', 'Laser', 'Autocad']
    selected_group = request.GET.get('group_filter')
    assigned_employee_id = request.GET.get('assigned_employee')

    # Base filters
    year_filter = Q(is_quote=False, created_at__year=current_year)
    not_canceled = Q(canceled=False)
    not_closed = Q(closed=False)

    # Filter employees dropdown based on selected group
    if selected_group in target_group_names:
        employees = User.objects.filter(is_active=True, groups__name=selected_group)
    else:
        employees = User.objects.filter(is_active=True, groups__name__in=target_group_names)

    
    # Start with base queryset
    tasks = Task.objects.select_related('task_name', 'customer_name', 'user', 'created_by', 'project') \
                       .prefetch_related('assigned_employees') \
                       .filter(year_filter)
    
    selected_branch = request.GET.get('branch_filter')
    if selected_branch:
        tasks = tasks.filter(branch_id=selected_branch)

    # Apply group filter if selected
    if selected_group in target_group_names:
        tasks = tasks.filter(assigned_employees__groups__name=selected_group)

    # Apply assigned employee filter if selected
    if assigned_employee_id:
        tasks = tasks.filter(assigned_employees__id=assigned_employee_id)

    # Handle different query types
    if query is None:
        query = 'undelivered'
        tasks = tasks.filter(not_canceled).exclude(
            id__in=DeliveredTask.objects.values_list('main_task_id', flat=True)
        )
    elif query == 'finished':
        tasks = tasks.filter(not_canceled, closed=True).exclude(
            id__in=DeliveredTask.objects.values_list('main_task_id', flat=True)
        )
    elif query == 'today':
        tasks = tasks.filter(not_canceled, created_at__date=date.today())
    elif query == 'undelivered':
        tasks = tasks.filter(not_canceled, not_closed).exclude(
            id__in=DeliveredTask.objects.values_list('main_task_id', flat=True)
        )
    elif query == 'delivered':
        tasks = tasks.filter(not_canceled, deliveredtask__is_delivered=True)
    elif query == 'cancel_request':
        tasks = tasks.filter(cancel_requested=True, canceled=False)
    elif query == 'canceled':
        tasks = tasks.filter(canceled=True)
    else:
        tasks = tasks.filter(not_canceled)

    # Apply search
    if search_query:
        tasks = tasks.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__customer_name__icontains=search_query)
        )

    # Annotate total_paid and highlighted status
    tasks = tasks.annotate(
        total_paid=Coalesce(
            Sum('payments__amount'),
            Decimal('0.00'),
            output_field=DecimalField(max_digits=20, decimal_places=2)
        ),
        is_highlighted=Exists(
            Subtask.objects.filter(
                task=OuterRef('pk'),
                is_highlighted=True,
                user=user
            )
        )
    )

    # Handle sorting
    allowed_sorts = [
        'id', '-id', 
        'order_number', '-order_number', 
        'task_name__name', '-task_name__name',
        'status', '-status', 
        'customer_name__customer_name', '-customer_name__customer_name',
        'assigned_employees__username', '-assigned_employees__username',
        'final_price', '-final_price',
        'total_paid', '-total_paid',
        'paid_status', '-paid_status',
    ]
    if sort_by not in allowed_sorts:
        sort_by = '-id'

    # Special handling for username sorting
    if sort_by in ['assigned_employees__username', '-assigned_employees__username']:
        tasks = tasks.annotate(
            first_employee_username=Min('assigned_employees__username')
        ).order_by(sort_by.replace('assigned_employees__username', 'first_employee_username'))
    else:
        tasks = tasks.order_by(sort_by)

    # Pagination
    paginator = Paginator(tasks, per_page)
    try:
        tasks = paginator.page(page)
    except PageNotAnInteger:
        tasks = paginator.page(1)
    except EmptyPage:
        tasks = paginator.page(paginator.num_pages)

    # Project Groups (exclude canceled and closed here)
    project_groups = Project.objects.filter(
        task__in=Task.objects.filter(year_filter, not_canceled, not_closed)
    ).distinct().prefetch_related(
        Prefetch('task_set',
                queryset=Task.objects.filter(year_filter, not_canceled, not_closed)
                                    .select_related('task_name', 'customer_name', 'user', 'created_by')
                                    .prefetch_related('assigned_employees')
                                    .order_by(sort_by)),  # Add sorting here
        'customer'
    ).order_by('-created_at')

    # Dashboard counters - updated to exclude closed from undelivered
    today = date.today()
    total_all = Task.objects.filter(year_filter, not_canceled).count()
    finished_count_all = Task.objects.filter(year_filter, not_canceled, closed=True) \
                                    .exclude(id__in=DeliveredTask.objects.values_list('main_task_id', flat=True)) \
                                    .count()
    pending_count_all = Task.objects.filter(year_filter, not_canceled, closed=False).count()
    new_all = Task.objects.filter(year_filter, not_canceled, created_at__date=today).count()
    undelivered_count_all = Task.objects.filter(year_filter, not_canceled, not_closed) \
                                        .exclude(id__in=DeliveredTask.objects.values_list('main_task_id', flat=True)) \
                                        .count()
    delivered_count_all = Task.objects.filter(year_filter, not_canceled, deliveredtask__is_delivered=True).distinct().count()
    canceled_count = Task.objects.filter(year_filter, canceled=True).count()
    cancel_request_count = Task.objects.filter(year_filter, cancel_requested=True, canceled=False).count()

    available_years = Task.objects.filter(is_quote=False) \
                                .annotate(year=ExtractYear('created_at')) \
                                .values_list('year', flat=True).distinct().order_by('-year')
    branches = Branch.objects.all()

    return render(request, 'tasks/all-tasks.html', {
        'tasks': tasks,
        'project_groups': project_groups,
        'employees': employees,
        'selected_group': selected_group,
        'target_group_names': target_group_names,
        'per_page': per_page,
        'search_query': search_query,
        'sort_by': sort_by,
        'query': query,
        'current_year': current_year,
        'available_years': available_years,
        'today': today,
        'total_all': total_all,
        'finished_count_all': finished_count_all,
        'pending_count_all': pending_count_all,
        'new_all': new_all,
        'undelivered_count_all': undelivered_count_all,
        'delivered_count_all': delivered_count_all,
        'canceled': canceled_count,
        'cancel_request': cancel_request_count,
        'nav_title': 'All Tasks',
        'branches': branches,
        'selected_branch': selected_branch,
    })

@disallow_groups(['Cashier'])
@login_required
def my_tasks(request, query=None):
    user = request.user
    per_page = request.GET.get('per_page', '10')
    page = request.GET.get('page', 1)

    tasks = Task.objects.prefetch_related('assigned_employees').select_related('task_name', 'customer_name', 'user', 'created_by', 'project').filter(
        assigned_employees=user.id,
        canceled=False
    ).filter(
        Q(closed=False) | # if not closed
        Q(paid_status='U') | # or if not paid
        Q(status='in_progress') | # or status is in progress
        ~Q(id__in=DeliveredTask.objects.values_list('main_task_id', flat=True)) # or not delivered
        
    ).exclude(branch_id=1).distinct() # except that belongs to branch1

    # Properly defined subquery using Exists
    tasks = tasks.annotate(
        is_highlighted=Exists(
            Subtask.objects.filter(
                task=OuterRef('pk'),
                is_highlighted=True,
                user=user
            )
        )
    )

    #-------------------Dashboard counter -------------------------|
    # 1- Total
    total = Task.objects.prefetch_related('assigned_employees').filter(assigned_employees=request.user.id).filter(canceled=False).count()
    
    # 2- Finished
    finished_count = Task.objects.prefetch_related('assigned_employees').filter(assigned_employees=request.user.id).filter(closed=True).filter(canceled=False).count()
    
    # 3- pending
    unfinished_count = Task.objects.prefetch_related('assigned_employees').filter(
        assigned_employees=request.user.id,
        canceled=False
    ).filter(
        Q(closed=False) |
        Q(paid_status='U') |
        Q(status='in_progress') |
        ~Q(id__in=DeliveredTask.objects.values_list('main_task_id', flat=True))
    ).exclude(branch_id=1).distinct().count()

    # 4- Today
    today = date.today()
    new = Task.objects.filter(assigned_employees=request.user.id).filter(canceled=False).filter(created_at__date=today).count()

    # 5- Closed Waiting Delivery
    close_waiting_delivery_count = Task.objects.prefetch_related('assigned_employees').filter(assigned_employees=request.user,canceled=False, closed=True).exclude(id__in=DeliveredTask.objects.values_list('main_task_id', flat=True)).count()

    # 3- Unpaid
    unpaid_count = Task.objects.prefetch_related('assigned_employees').filter(assigned_employees=request.user.id, canceled=False, closed=False, paid_status='U').count()
    
    if query == 'finished':
        tasks = Task.objects.prefetch_related(
            'assigned_employees'
            ).select_related(
            'task_name', 'customer_name', 'user', 'created_by', 'project'
            ).filter(assigned_employees=request.user.id).filter(closed=True).filter(canceled=False)
    elif query == 'today':
        today = date.today()
        tasks = Task.objects.prefetch_related(
            'assigned_employees'
            ).select_related(
            'task_name', 'customer_name', 'user', 'created_by', 'project'
            ).filter(assigned_employees=request.user.id).filter(canceled=False).filter(created_at__date=today)
    elif query == 'all':
        tasks = Task.objects.prefetch_related(
            'assigned_employees'
            ).select_related(
            'task_name', 'customer_name', 'user', 'created_by', 'project'
            ).filter(assigned_employees=request.user.id).filter(canceled=False)
    elif query == 'pending':
        tasks = Task.objects.prefetch_related(
            'assigned_employees'
        ).select_related(
            'task_name', 'customer_name', 'user', 'created_by', 'project'
        ).filter(
            assigned_employees=request.user.id,
            canceled=False
        ).filter(
            Q(closed=False) |
            Q(paid_status='U') |
            Q(status='in_progress') |
            ~Q(id__in=DeliveredTask.objects.values_list('main_task_id', flat=True))
        ).exclude(branch_id=1).distinct()

    elif query == 'closed-waiting-delivery':
        tasks = Task.objects.prefetch_related('assigned_employees').select_related('task_name', 'customer_name', 'user', 'created_by', 'project').filter(assigned_employees=request.user.id,canceled=False, closed=True).exclude(id__in=DeliveredTask.objects.values_list('main_task_id', flat=True))

    elif query == 'unpaid':
        tasks = Task.objects.prefetch_related('assigned_employees').select_related('task_name', 'customer_name', 'user', 'created_by', 'project').filter(assigned_employees=request.user.id,canceled=False, closed=False, paid_status='U')
        
    paginator = Paginator(tasks, per_page)
    try:
        tasks = paginator.page(page)
    except PageNotAnInteger:
        tasks = paginator.page(1)
    except EmptyPage:
        tasks = paginator.page(paginator.num_pages)

    context = {
        'tasks':tasks, 'total':total, 
        'finished_count':finished_count, 
        'unpaid_count': unpaid_count,
        'unfinished_count':unfinished_count, 
        'new':new, 
        'close_waiting_delivery_count':close_waiting_delivery_count,
        'nav_title': 'My Tasks',
    }
    return render(request, 'tasks/my-tasks.html', context)


@disallow_groups(['Cashier'])
@login_required
def add_task_view(request):
    customers = Customer.objects.all()
    tasknames = TaskName.objects.all()
    country_codes = CountryCodes.objects.all()
    request.session.pop('show_add_customer_modal', None)
    new_customer_id = request.session.pop('new_customer_id', None)
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    task = form.save(commit=False)
                    task.created_by = request.user
                    task.final_price = task.frontdesk_price
                    task.save()
                    task.assigned_employees.add(task.user)
                    form.save_m2m()

                    try:
                        notify_user_about_task(task.user, task, message="New Task assigned", type_name="Task")
                    except Exception as e:
                        print("❌ Error in notify_user_about_task:", e)
                        messages.warning(request, f"Notification failed: {e}")
                    
                    # Log the action
                    action = f"Created Task, assigned {task.user.get_full_name()} as project manager"

                    if task.branch:
                        action += f", for branch: {task.branch.name}"

                    if task.frontdesk_price:
                        action += f". Set frontdesk price: {task.frontdesk_price}$"

                    

                    TaskActivityLog.objects.create(
                        task=task,
                        user=request.user,
                        action=action,
                        note=f"Task created by {request.user.get_full_name()}"
                    )

                messages.success(request, "Task successfully created!")
                return redirect('tasks:all_tasks')
            except Exception as e:
                messages.error(request, f"Error saving task: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
            print(form.errors)
    else:
        form = TaskForm()

    return render(request, 'tasks/add-task.html', {
        'form': form,
        'customers': customers,
        'tasknames': tasknames,
        'projects':projects,
        'country_codes':country_codes,
        'selected_customer_id': new_customer_id,
        'nav_title': 'Add Tasks',
    })


@login_required
def create_task_from_email(request, email_id):
    email = get_object_or_404(Email, id=email_id)

    customers = Customer.objects.all()
    tasknames = TaskName.objects.all()
    country_codes = CountryCodes.objects.all()
    attachments = email.attachment_set.all()

    # ✅ Filter out useless attachments
    valid_attachments = [
        a for a in attachments
        if not is_useless_attachment(a.file.path, a.filename or os.path.basename(a.file.name))
    ]

    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    task = form.save(commit=False)
                    task.created_by = request.user
                    task.final_price = task.frontdesk_price
                    task.from_email = True

                    # ✅ Link filtered attachment(s)
                    if len(valid_attachments) > 1:
                        zip_file, zip_name = zip_email_attachments(email)
                        if zip_file:
                            task.file_name.save(zip_name, zip_file, save=False)
                    elif len(valid_attachments) == 1:
                        task.file_name = valid_attachments[0].file

                    task.save()

                    task.email = email
                    task.save(update_fields=["email"])

                    task.assigned_employees.add(task.user)
                    form.save_m2m()

                    # Link email to task
                    email.assigned_to = task.user
                    email.status = 'in_progress'
                    email.save()

                    # Log the action
                    TaskActivityLog.objects.create(
                        task=task,
                        user=request.user,
                        action=f"Task created from email by {request.user.get_full_name()}",
                        note=f"Created from email: {email.subject}"
                    )

                    # Notify assigned user
                    notify_user_about_task(task.user, task, message="Task from email assigned", type_name="Task")

                messages.success(request, "✅ Task created and linked to email.")
                return redirect('tasks:all_tasks')

            except Exception as e:
                messages.error(request, f"❌ Error creating task: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # 📩 Try to match or create Customer based on email sender
        sender_email = parseaddr(email.sender)[1].strip().lower()
        customer_match = Customer.objects.filter(email__iexact=sender_email).first()

        if not customer_match:
            local_part, domain = sender_email.split('@')
            generic_names = ['noreply', 'info', 'support', 'contact', 'admin', 'sales']

            if local_part in generic_names:
                # Use only the domain name (e.g., radissonhotels)
                extracted = tldextract.extract(domain)
                name_guess = extracted.domain.capitalize()
            else:
                # Use local part as fallback (e.g., john.doe → John Doe)
                name_guess = slugify(local_part).replace('-', ' ').title()

            customer_match = Customer.objects.create(
                customer_name=name_guess,
                email=sender_email,
                created_by=request.user
            )
            messages.info(request, f'📌 Customer "{customer_match.customer_name}" was auto-created from email.')

        initial_data = {
            'notes': email.body,
            'customer_name': customer_match.pk,
            'task_priority': 'Normal',
            'job_due_date': now().date(),
        }

        form = TaskForm(initial=initial_data)

        # ✅ Attach filtered file to preview in form
        first_valid = valid_attachments[0] if valid_attachments else None
        if first_valid:
            form.instance.file_name = first_valid.file

    return render(request, 'tasks/create-task-from-email.html', {
        'form': form,
        'email': email,
        'customers': customers,
        'tasknames': tasknames,
        'country_codes': country_codes,
    })



@disallow_groups(['Cashier'])
@login_required
def update_task_view(request, pk):
    customers = Customer.objects.all()
    tasknames = TaskName.objects.all()
    country_codes = CountryCodes.objects.all()
    task = get_object_or_404(Task, pk=pk)
    old_user = task.user  # store original assigned project manager
    old_price = task.frontdesk_price  # store original price
    old_customer = task.customer_name  # store original customer
    is_paid = task.is_paid
    task_form = TaskForm(instance=task)
    print('is paid from method before submit', task.is_paid)
    print('is paid from variable before submit', is_paid)
    if request.method == 'POST':
        task_form = TaskForm(request.POST, request.FILES, instance=task)
        if task_form.is_valid():
            try:
                with transaction.atomic():
                    task = task_form.save(commit=False)

                    # Store original final price
                    old_final_price = task.final_price

                    # Calculate updated final price
                    subtasks_sum = task.subtasks.aggregate(total=Sum('subtask_amount'))['total'] or Decimal('0.00')
                    task.final_price = task.frontdesk_price + subtasks_sum

                    # Adjust paid status based on updated price and paid amount
                    paid_amount = task.total_paid_amount  # from @property
                    if paid_amount >= task.final_price:
                        if paid_amount > task.final_price:
                            task.paid_status = 'O'
                        else:
                            task.paid_status = 'P'
                    else:
                        task.paid_status = 'U'

                    task.save()

                    # ✅ Update payment status properly
                    update_payment_summary(task)

                    if task.user:
                        task.assigned_employees.set([task.user])
                        task_form.save_m2m()

                    # notification section
                    if old_user != task.user:
                        new_user = task.user
                        message = f"You have been assigned as the new project manager for task '{task.task_name}'."
                        notify_user_about_task(new_user, task, message, type_name="Task")

                    # Prepare action log
                    log_parts = [f"updated Task"]

                    # Compare project manager
                    if old_user != task.user:
                        if old_user:
                            log_parts.append(f"unassigned {old_user.get_full_name()} from project manager")
                        if task.user:
                            log_parts.append(f"assigned {task.user.get_full_name()} as project manager")

                    # Compare price
                    if old_price != task.frontdesk_price:
                        log_parts.append(f"changed price from {old_price}$ to {task.frontdesk_price}$")

                    # Compare customer name
                    if old_customer != task.customer_name:
                        log_parts.append(f"changed Cutomer from {old_customer} to {task.customer_name}")

                    if len(log_parts) > 1:
                        TaskActivityLog.objects.create(
                            task=task,
                            user=request.user,
                            action=', '.join(log_parts),
                            note=f"Updated by {request.user.get_full_name()}"
                        )

                    messages.success(request, "Task successfully updated!")
                    return redirect('tasks:task_detail', pk)
            except Exception as e:
                messages.error(request, f"Error saving task: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
            print(task_form.errors)

    return render(request, 'tasks/update-task.html', {
        'form': task_form,
        'customers': customers,
        'tasknames': tasknames,
        'country_codes':country_codes,
        'task': task,
        'nav_title': 'Update Tasks',
    })

@disallow_groups(['Cashier'])
@login_required
def add_taskname_modal(request):
    if request.method == 'POST':
        name = request.POST.get('task_name')
        if name:
            TaskName.objects.create(name=name, created_by=request.user)
            messages.success(request, 'Task name added.')
    return redirect('tasks:add_task')

@disallow_groups(['Cashier'])
@login_required
def task_detail(request, pk):
    # task = get_object_or_404(Task.objects.prefetch_related('payments', 'payment_status'), pk=pk)
    task = Task.objects.select_related('payment_status').prefetch_related('payments').get(id=pk)

    total_paid = task.payments.aggregate(total=Sum('amount'))['total'] or 0
    balance = task.final_price - total_paid
    print('is paid', task.is_paid)
    close_task_form = CloseTaskForm()
    is_assigned_user = request.user in task.assigned_employees.all()
    is_pm = request.user == task.user
    has_subtask = Subtask.objects.filter(task=task, user=request.user).exists()

    if task.status == 'created' and (is_assigned_user or is_pm or has_subtask):
        task.status = 'in_progress'
        task.save(update_fields=['status'])

    subtasks = Subtask.objects.filter(task=task)
    task_names = TaskName.objects.all()
    non_pm_subtasks = subtasks.exclude(user=task.user)
    pm_logs = task.activity_logs.filter(action__icontains='as project manager')
    subtask_form = SubtaskForm(task=task)

    Notification.objects.filter(user=request.user, task=task, is_read=False).update(is_read=True)

    user_subtasks = subtasks.filter(user=request.user)
    if user_subtasks.exists():
        user_subtasks.update(is_highlighted=False)

    try:
        delivered_task = task.deliveredtask
    except DeliveredTask.DoesNotExist:
        delivered_task = None

    # Prepare cancel request form if eligible
    cancel_request_form = None
    try:
        subtask = Subtask.objects.get(
            task=task,
            user=request.user,
            # is_project_manager=False,
            is_done=False,
            is_canceled=False
        )
        cancel_request_form = RequestCancelSubtaskForm(instance=subtask)
    except Subtask.DoesNotExist:
        pass  # User does not have a valid subtask to cancel

     # ✅ Use GET parameter 'next' first
    back_url = request.GET.get("next")
    if not back_url:
        back_url = get_back_url(
            request,
            routes={
                'task/detail': request.META.get('HTTP_REFERER', ''),  # dynamic path fallback
                'my-tasks': 'tasks:my_tasks',
            },
            default='tasks:all_tasks'
        )

    context = {
        'task': task,
        'total_paid': total_paid,
        'balance': balance,
        'subtasks': subtasks,
        'non_pm_subtasks': non_pm_subtasks,
        'subtask_form': subtask_form,
        'task_names': task_names,
        'pm_logs': pm_logs,
        'previous_url': request.META.get('HTTP_REFERER'),
        'delivered_task': delivered_task,
        'is_pm': is_pm,
        'cancel_request_form': cancel_request_form,
        'close_task_form':close_task_form,
        "can_assign_operator": task.can_user_assign_operator(request.user),
        'back_url': back_url,
        'nav_title': 'Task Detail',
    }

    return render(request, 'tasks/task-detail.html', context)

@disallow_groups(['Cashier'])
@login_required
def add_subtask_modal(request, main_task_id):
    main_task = get_object_or_404(Task, id=main_task_id)

    # Ensure only the project manager can access this view
    if request.user != main_task.user:
        messages.error(request, "Only the assigned Project Manager can add a subtask.")
        return redirect('tasks:task_detail', pk=main_task_id)

    if request.method == 'POST':
        subtask_form = SubtaskForm(request.POST, task=main_task)
        
        if subtask_form.is_valid():
            subtask = subtask_form.save(commit=False)
            subtask.task = main_task
            subtask.added_by = request.user
            subtask.is_project_manager = False
            subtask.save()


            try:
                notify_user_about_task(subtask.user, subtask.task, message="New Task assigned", type_name="Task")
            except Exception as e:
                print("❌ Error in notify_user_about_task:", e)
                messages.warning(request, f"Notification failed: {e}")

            # Log the action
            TaskActivityLog.objects.create(
                task=main_task,
                user=request.user,
                action=f"assigned {subtask.user.get_full_name()} operator to subtask",
                note=subtask.user.get_full_name()
            )
            
            # Add the user to task's assigned employees
            main_task.assigned_employees.add(subtask.user)
            # change status to in progress
            main_task.status = "in_progress"
            main_task.save()
            
            messages.success(request, "Subtask successfully created.")
            return redirect('tasks:task_detail', pk=main_task_id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        subtask_form = SubtaskForm(task=main_task)

    return redirect('tasks:task_detail', main_task.pk)

@disallow_groups(['Cashier'])
@login_required
def update_subtask_modal(request, main_task_id):
    main_task = get_object_or_404(Task, id=main_task_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                subtask_id = request.POST.get('subtask_id')
                subtask = get_object_or_404(Subtask, id=subtask_id, task=main_task)

                # Capture old values BEFORE form binds
                was_done = subtask.is_done
                old_subtask_amount = subtask.subtask_amount

                form = UpdateSubtaskForm(request.POST, instance=subtask)
                if form.is_valid():
                    updated_subtask = form.save(commit=False)
                    updated_subtask.is_updated = True

                    just_completed = not was_done and updated_subtask.is_done

                    # Auto-set finished_at if newly marked as done
                    if just_completed and not updated_subtask.finished_at:
                        updated_subtask.finished_at = timezone.now()

                    updated_subtask.save()

                    # Update Task Final Price
                    price_diff = updated_subtask.subtask_amount - old_subtask_amount
                    main_task.final_price += price_diff
                    main_task.save(update_fields=['final_price'])

                    # Recalculate payment status if TaskPaymentStatus exists
                    if hasattr(main_task, 'payment_status'):
                        main_task.payment_status.update_status()

                    # Update Task Status
                    main_task.status = 'done' if main_task.check_all_subtasks_done() else 'in_progress'

                    # Handle Location Update if just marked as done
                    if updated_subtask.is_done:
                        final_location = request.POST.get('final_location', '').strip()
                        other_location = request.POST.get('other_location', '').strip()

                        # Normalize: final_location takes priority
                        if final_location:
                            main_task.final_location = final_location
                            main_task.other_location = None
                        elif other_location:
                            main_task.final_location = None
                            main_task.other_location = other_location
                        else:
                            main_task.final_location = None
                            main_task.other_location = None

                    main_task.save()

                    # Log activity
                    price_info = f", price changed by {price_diff:.2f} {updated_subtask.currency}" if price_diff != 0 else ""
                    done_info = ", marked as done" if just_completed else ""
                    location_info = ""
                    if just_completed and (final_location or other_location):
                        location_info = f", location set to: {main_task.resolved_final_location}"

                    TaskActivityLog.objects.create(
                        task=main_task,
                        user=request.user,
                        action=f"Updated subtask: {updated_subtask.name}{price_info}{done_info}{location_info}",
                        note=f"Subtask updated by {updated_subtask.user.get_full_name()}"
                    )

                    messages.success(request, "Subtask updated successfully.")
                else:
                    # Add form errors to messages
                    for field, errors in form.errors.items():
                        for error in errors:
                            if field == '__all__':
                                messages.error(request, f"{error}")
                            else:
                                label = form.fields.get(field).label or field.replace('_', ' ').capitalize()
                                messages.error(request, f"{label}: {error}")

                    # Add modal ID as URL parameter to re-trigger modal
                    query_string = urlencode({'error_modal': f'u{subtask.id}'})
                    redirect_url = reverse('tasks:task_detail', kwargs={'pk': main_task_id})
                    full_redirect = f"{redirect_url}?{query_string}"
                    return redirect(full_redirect)

                return redirect('tasks:task_detail', pk=main_task_id)
        except Exception as e:
            messages.error(request, f"Error saving task: {e}")

    return redirect('tasks:task_detail', pk=main_task_id)


@disallow_groups(['Cashier'])
@login_required
def close_task_modal(request, pk):
    task = get_object_or_404(Task, id=pk)
    subtasks = Subtask.objects.filter(task=task)
    non_pm_subtasks = subtasks.exclude(user=task.user)
    subtask_form = SubtaskForm(task=task)
    task_names = TaskName.objects.all()
    pm_logs = task.activity_logs.filter(action__icontains='as project manager')
    try:
        delivered_task = task.deliveredtask
    except DeliveredTask.DoesNotExist:
        delivered_task = None
    is_pm = request.user == task.user
    # Prepare cancel request form if eligible
    cancel_request_form = None
    try:
        subtask = Subtask.objects.get(
            task=task,
            user=request.user,
            # is_project_manager=False,
            is_done=False,
            is_canceled=False
        )
        cancel_request_form = RequestCancelSubtaskForm(instance=subtask)
    except Subtask.DoesNotExist:
        pass  # User does not have a valid subtask to cancel
    close_task_form = CloseTaskForm()


    if request.method == 'POST':
        form = CloseTaskForm(request.POST, instance=task)

        # Prefer using form.cleaned_data for validation
        if form.is_valid():
            final_location = form.cleaned_data.get('final_location')
            other_location = form.cleaned_data.get('other_location')

            if not final_location and not other_location:
                form.add_error(None, "Please select a final location or enter a custom one before submitting.")

            else:
                form.save()
                task.closed = True
                task.closed_at = timezone.now()
                task.status = 'closed'
                task.save()

                # Get the final location (resolved property)
                resolved_location = task.resolved_final_location or "Not specified"

                # Log the action with location
                TaskActivityLog.objects.create(
                    task=task,
                    user=request.user,
                    action=f"Task closed by: {request.user.get_full_name()}, Final location: {resolved_location}",
                    note=f"Closed at: {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                )
                messages.success(request, "Task has been closed successfully.")
                return redirect('tasks:task_detail', task.pk)

        # If form is invalid or both fields are empty
        messages.error(request, "Please fix the errors below.")
        return render(request, 'tasks/task-detail.html', {
            'task': task,
            'close_task_form': form
        })

    else:
        form = CloseTaskForm(instance=task)
        return render(request, 'tasks/task-detail.html', {
            'task': task,
            'subtasks': subtasks,
            'close_task_form': form,
            'non_pm_subtasks': non_pm_subtasks,
            'subtask_form': subtask_form,
            'task_names': task_names,
            'pm_logs': pm_logs,
            'delivered_task': delivered_task,
            'is_pm': is_pm,
            'cancel_request_form': cancel_request_form,
            'close_task_form':close_task_form,
        })
    
@disallow_groups(['Cashier'])
@login_required
def undo_close_task_modal(request, pk):
    task = get_object_or_404(Task, id=pk)
    if request.method == 'POST':
        task.closed = False
        task.status = 'done'
        task.final_location = None
        task.other_location = ''
        task.save()

        # Log the action with location
        TaskActivityLog.objects.create(
            task=task,
            user=request.user,
            action=f"Task unclosed by: {request.user.get_full_name()}",
            note=f"unclosed at: {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            )
        
        messages.success(request, "Task has been closed successfully.")
        return redirect('tasks:task_detail', task.pk)
        

@disallow_groups(['Cashier'])
@login_required
def send_cancel_request_modal(request, pk):
    task = get_object_or_404(Task, id=pk)
    user = request.user

    if request.method == 'POST':
        subtask_id = request.POST.get('subtask_id')
        try:
            subtask = Subtask.objects.get(
                id=subtask_id,
                task=task,
                user=user,
                is_done=False,
                is_canceled=False
            )
        except Subtask.DoesNotExist:
            messages.error(request, "You don’t have a valid operator subtask for this task.")
            return redirect('tasks:task_detail', task.pk)

        form = RequestCancelSubtaskForm(request.POST, instance=subtask)
        if form.is_valid():
            subtask.cancel_requested = True
            form.save()

            TaskActivityLog.objects.create(
                task=task,
                user=user,
                action="Cancel request submitted by operator",
                note=form.cleaned_data['cancel_subtask_reason']
            )
            messages.success(request, "Your cancel request has been submitted.")
        else:
            print(form.errors)
            messages.error(request, "Please provide a valid cancellation reason.")

    return redirect('tasks:task_detail', task.pk)

@disallow_groups(['Cashier'])
@login_required
def undo_cancel_subtask_request_modal(request, pk):
    if request.method == 'POST':
        subtask_id = request.POST.get('subtask_id')
        user = request.user
        task = get_object_or_404(Task, id=pk)

        try:
            subtask = Subtask.objects.get(id=subtask_id, task=task, user=user, cancel_requested=True)
        except Subtask.DoesNotExist:
            messages.error(request, "No cancel request found or you're not authorized to undo it.")
            return redirect('tasks:task_detail', pk)

        subtask.cancel_requested = False
        subtask.cancel_subtask_reason  = ''
        subtask.save()

        TaskActivityLog.objects.create(
            task=task,
            user=user,
            action="Cancel request undone by operator",
            note="User canceled the cancel request."
        )
        messages.success(request, "Cancel request has been undone.")

    return redirect('tasks:task_detail', pk)

@disallow_groups(['Cashier'])
@login_required
@login_required
def approve_cancel_request_modal(request, pk):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('tasks:task_detail', pk)

    subtask_id = request.POST.get('subtask_id')
    user = request.user
    task = get_object_or_404(Task, id=pk)
    subtask = get_object_or_404(Subtask, id=subtask_id, task=task)

    # Permission check: task creator or user in Developer/Manager groups
    if not (
        task.created_by == user or
        user.groups.filter(name__in=['Developer', 'Managers', 'ManagerAssistant', 'FrontDesk']).exists()
    ):
        messages.error(request, "You are not authorized to approve this cancel request.")
        return redirect('tasks:task_detail', task.id)

    # Approve cancellation
    if subtask.cancel_requested and not subtask.is_canceled:
        subtask.is_canceled = True
        subtask.cancel_requested = False
        subtask.save()

        TaskActivityLog.objects.create(
            task=task,
            user=user,
            action="Cancel request approved",
            note=f"Subtask '{subtask}' has been canceled."
        )

        # Check if it's the only subtask for the task
        active_subtasks = task.subtask_set.filter(is_canceled=False, is_closed=False)
        if active_subtasks.count() == 0:
            task.canceled = True
            task.status= 'canceled'
            task.save()
            TaskActivityLog.objects.create(
                task=task,
                user=user,
                action="Main task canceled due to single subtask cancellation",
                note="All subtasks are canceled. Task canceled automatically."
            )
            messages.success(request, "The subtask and main task have been canceled.")
        else:
            messages.success(request, "The subtask has been canceled.")

    else:
        messages.warning(request, "This subtask has no pending cancel request or is already canceled.")

    return redirect('tasks:task_detail', task.id)

@disallow_groups(['Cashier'])
@login_required
def cancel_task_modal(request, pk):
    task = get_object_or_404(Task, id=pk)
    user = request.user

    # Add optional permission check if needed
    is_pm = Subtask.objects.filter(task=task, user=user, is_project_manager=True).exists()
    is_creator = task.created_by == user

    if request.method == 'POST':
        if is_pm or is_creator or user.is_superuser:
            task.canceled = True
            task.status = 'canceled'
            task.save()

            TaskActivityLog.objects.create(
                task=task,
                user=user,
                action="Task has been canceled",
                note=user.get_full_name()
            )
            messages.success(request, "Task has been canceled successfully.")
        else:
            messages.error(request, "You do not have permission to cancel this task.")

        return redirect('tasks:task_detail', task.pk)

    return render(request, 'tasks/cancel-task-modal.html', {'task': task})

@disallow_groups(['Cashier'])
@login_required
def deliver_job(request, job_id):
    task = get_object_or_404(Task, id=job_id)

    if request.method == 'POST':
        form = DeliveredTaskForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    delivered_form = form.save(commit=False)
                    delivered_form.main_task = task
                    delivered_form.created_by = request.user
                    delivered_form.is_delivered = True
                    delivered_form.save()

                    task.status = 'delivered'
                    task.save()

                    TaskActivityLog.objects.create(
                        task=task,
                        user=request.user,
                        action=f"Job has been delivered by {delivered_form.delivered_by} to {delivered_form.received_person}",
                        note=request.user.get_full_name()
                    )

                    messages.success(request, "Task has been closed successfully.")
                    return redirect('tasks:task_detail', job_id)
            except Exception as e:
                # 💥 Rollback will automatically occur
                print("❌ Delivery Failed:", e)
                messages.error(request, "Something went wrong while delivering the job. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
            print(form.errors)
    else:
        form = DeliveredTaskForm()

    context = {'form': form, 'task': task}
    return render(request, 'tasks/deliver-job.html', context)

@disallow_groups(['Cashier'])
@login_required       
def projects(request):
    projects = Project.objects.select_related('customer').all()
    

    # ✅ Use GET parameter 'next' first
    back_url = request.GET.get("next")
    if not back_url:
        back_url = get_back_url(
            request,
            routes={
                'task/detail': request.META.get('HTTP_REFERER', ''),  # dynamic path fallback
                'all-tasks': 'tasks:all_tasks',
            },
            default='tasks:projects'
        )

    context = {'projects':projects, 'back_url': back_url, 'nav_title': 'Projects',}
    return render(request, 'tasks/projects.html', context)


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    tasks = Task.objects.filter(project=project).select_related('task_name', 'customer_name')
    tasks_with_no_project = Task.objects.select_related('task_name', 'customer_name', 'user', 'created_by', 'project').filter(project__isnull=True).exclude(canceled=True)
    back_url = request.GET.get("next") or get_back_url(
        request,
        routes={
            'task-detail': 'tasks:task_detail',
            'all-tasks': 'tasks:all_tasks',
        },
        default='tasks:projects'
    )
    context = {
        'project': project,
        'tasks': tasks,
        'back_url': back_url,
        'tasks_with_no_project':tasks_with_no_project,
        'nav_title': 'Project Detail',
    }
    return render(request, 'tasks/project-detail.html', context)


@login_required
@require_POST
def assign_tasks_to_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    task_ids = request.POST.getlist('tasks')

    Task.objects.filter(id__in=task_ids).update(project=project)

    messages.success(request, f"{len(task_ids)} task(s) assigned to project {project.name}.")
    return redirect('tasks:project_detail', pk=project_id)

@login_required
@require_POST
def remove_task_from_project(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    project = task.project
    if request.method == 'POST':
        task.project = None
        task.save()
        messages.success(request, f"task has been removed from assigned to project {project.name}.")
        return redirect('tasks:project_detail', pk=project.id)


@disallow_groups(['Cashier'])
@login_required       
def add_project(request):
    project_form = projectForm()
    tasknames = TaskName.objects.all()
    country_codes = CountryCodes.objects.all()
    customers = Customer.objects.all()
    if request.method == 'POST':
        project_form = projectForm(request.POST)
        if project_form.is_valid():
            form = project_form.save(commit=False)
            form.created_by = request.user
            form.save()
            
            log_activity(request.user, f'Created new project "{form.name}" via modal', form)

            messages.success(request, "Task has been closed successfully.")
            return redirect('tasks:projects')
        else:
            messages.error(request, "Please correct the errors below.")
            print(project_form.errors)
    context = {'project_form':project_form, 
               'tasknames':tasknames,
               'country_codes':country_codes,
               'customers':customers,
               'nav_title': 'Add project',
               }
    return render(request, 'tasks/add-project.html', context)
