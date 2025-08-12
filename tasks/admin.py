# tasks/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget
from .models import Vat, Project, TaskName, Task, Subtask, TaskActivityLog, CurrencyRate, Notification, NotificationType, DeliveredTask, Branch
from customers.models import Customer
from decimal import Decimal
from payments.models import Payment, TaskPaymentStatus


admin.site.register(TaskActivityLog)
admin.site.register(CurrencyRate)
admin.site.register(DeliveredTask)
admin.site.register(NotificationType)
admin.site.register(Branch)

# Resource classes for import_export
class VatResource(resources.ModelResource):
    class Meta:
        model = Vat
        fields = ('id', 'name', 'value')
        export_order = fields


class ProjectResource(resources.ModelResource):
    customer = Field(
        column_name='customer',
        attribute='customer',
        widget=ForeignKeyWidget(Customer, 'customer_name')
    )
    
    created_by = Field(
        column_name='created_by',
        attribute='created_by',
        widget=ForeignKeyWidget(User, 'username')
    )
    
    class Meta:
        model = Project
        fields = ('id', 'name', 'customer', 'balance', 'spent', 'currency', 'notes', 'created_by', 'created_at')
        export_order = fields


class TaskNameResource(resources.ModelResource):
    class Meta:
        model = TaskName
        fields = ('id', 'name', 'code')
        export_order = fields


class TaskResource(resources.ModelResource):
    name = Field(
        column_name='task_name',
        attribute='task_name',
        widget=ForeignKeyWidget(TaskName, 'name')  # Fixed: was 'task_namename'
    )
     
    project = Field(
        column_name='project',
        attribute='project',
        widget=ForeignKeyWidget(Project, 'name')
    )
    
    created_by = Field(
        column_name='created_by',
        attribute='created_by',
        widget=ForeignKeyWidget(User, 'username')
    )
    
    user = Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    
    class Meta:
        model = Task
        fields = ('id', 'order_number', 'task_name', 'customer_name', 'project', 'status', 'frontdesk_price', 
                 'final_price', 'discount', 'currency', 'task_priority', 'paid_status', 'payment_method',
                 'created_by', 'user', 'job_due_date', 'quote_validity', 'notes',
                 'is_quote', 'closed', 'cancel_requested', 'canceled',
                 'created_at', 'updated_at')
        export_order = fields


class SubtaskResource(resources.ModelResource):
    task = Field(
        column_name='task',
        attribute='task',
        widget=ForeignKeyWidget(Task, 'order_number')
    )
    
    name = Field(
        column_name='name',
        attribute='name',
        widget=ForeignKeyWidget(TaskName, 'name')
    )
    
    user = Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    
    class Meta:
        model = Subtask
        fields = ('id', 'task', 'name', 'user', 'is_done', 'is_project_manager', 'subtask_amount',
                 'discount', 'vat', 'currency', 'job_is_zero', 'location', 'notes_from_top',
                 'created_at', 'finished_at')
        export_order = fields

@admin.register(Notification)
class NotificationAdmin(ImportExportModelAdmin):
    list_display = ('user', 'truncated_message', 'type', 'is_read', 'created_at')
    list_filter = ('is_read', 'type', 'created_at')
    search_fields = ('user__username', 'user__email', 'message')
    list_editable = ('is_read',)
    readonly_fields = ('created_at',)
    list_per_page = 50
    
    def truncated_message(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    truncated_message.short_description = 'Message'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'type', 'task')

# Admin classes with ImportExportModelAdmin
@admin.register(Vat)
class VatAdmin(ImportExportModelAdmin):
    resource_class = VatResource
    list_display = ('name', 'value')
    search_fields = ('name',)
    ordering = ('value',)
    list_per_page = 25


@admin.register(Project)
class ProjectAdmin(ImportExportModelAdmin):
    resource_class = ProjectResource
    list_display = ('name', 'customer', 'currency', 'balance', 'spent', 'created_at')
    list_filter = ('currency', 'created_at')
    search_fields = ('name', 'customer__customer_name')
    raw_id_fields = ('customer', 'created_by')
    readonly_fields = ('created_at',)
    list_per_page = 50
    
    # def remaining_balance_display(self, obj):
    #     return obj.remaining_balance
    # remaining_balance_display.short_description = 'Remaining Balance'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'created_by')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'customer', 'currency', 'project_number', 'notes')
        }),
        ('Financials', {
            'fields': ('balance', 'spent')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at')
        }),
    )


@admin.register(TaskName)
class TaskNameAdmin(ImportExportModelAdmin):
    resource_class = TaskNameResource
    list_display = ('name', 'code', 'created_by', 'creation_date')
    search_fields = ('name', 'code')
    list_filter = ('creation_date',)
    ordering = ('name',)
    list_per_page = 50
    raw_id_fields = ('created_by',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


# Optimized Inline Classes
class OptimizedSubtaskInline(admin.TabularInline):
    model = Subtask
    extra = 0
    max_num = 15  # Reasonable limit for subtasks
    fields = ('name_display', 'user_display', 'is_done', 'is_project_manager', 'subtask_amount', 'currency', 'total_price_display', 'is_canceled')
    readonly_fields = ('name_display', 'user_display', 'total_price_display')
    classes = ('collapse',)  # Collapsed by default
    
    def name_display(self, obj):
        return obj.name.name if obj.name else "—"
    name_display.short_description = "Task Name"
    
    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.get_full_name()})" if obj.user.get_full_name() else obj.user.username
        return "—"
    user_display.short_description = "Assigned User"
    
    def total_price_display(self, obj):
        try:
            total = obj.total_price()
            return f"{total} {obj.currency}" if total else f"0 {obj.currency}"
        except:
            return f"0 {obj.currency}"
    total_price_display.short_description = "Total Price"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'name', 'user', 'vat', 'added_by'
        ).order_by('-created_at')

class OptimizedDeliveredTaskInline(admin.TabularInline):
    model = DeliveredTask
    extra = 0
    max_num = 1  # Usually only one delivery per task
    fields = ('delivered_by_display', 'received_person', 'is_delivered', 'delivery_date_display', 'created_by_display', 'notes')
    readonly_fields = ('delivered_by_display', 'delivery_date_display', 'created_by_display')
    classes = ('collapse',)
    
    def delivered_by_display(self, obj):
        if obj.delivered_by:
            return f"{obj.delivered_by.username} ({obj.delivered_by.get_full_name()})" if obj.delivered_by.get_full_name() else obj.delivered_by.username
        return "—"
    delivered_by_display.short_description = "Delivered By"
    
    def created_by_display(self, obj):
        if obj.created_by:
            return f"{obj.created_by.username} ({obj.created_by.get_full_name()})" if obj.created_by.get_full_name() else obj.created_by.username
        return "—"
    created_by_display.short_description = "Created By"
    
    def delivery_date_display(self, obj):
        return obj.delivery_date.strftime('%Y-%m-%d %H:%M') if obj.delivery_date else "—"
    delivery_date_display.short_description = "Delivery Date"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'delivered_by', 'created_by'
        ).order_by('-delivery_date')

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    max_num = 8  # Reasonable limit for payments
    fields = ('amount', 'payment_type', 'payment_method', 'paid_by_display', 'paid_at_display', 'notes')
    readonly_fields = ('paid_by_display', 'paid_at_display')
    classes = ('collapse',)  # Collapsed by default
    
    def paid_by_display(self, obj):
        if obj.paid_by:
            return f"{obj.paid_by.username} ({obj.paid_by.get_full_name()})" if obj.paid_by.get_full_name() else obj.paid_by.username
        return "—"
    paid_by_display.short_description = "Paid By"
    
    def paid_at_display(self, obj):
        return obj.paid_at.strftime('%Y-%m-%d %H:%M') if obj.paid_at else "—"
    paid_at_display.short_description = "Payment Date"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('paid_by').order_by('-paid_at')

class TaskPaymentStatusInline(admin.TabularInline):
    model = TaskPaymentStatus
    extra = 0
    max_num = 1  # Only one payment status per task
    fields = ('paid_amount', 'is_fully_paid', 'is_down_payment_only', 'updated_display')
    readonly_fields = ('paid_amount', 'is_fully_paid', 'is_down_payment_only', 'updated_display')
    classes = ('collapse',)
    
    def updated_display(self, obj):
        return obj.updated.strftime('%Y-%m-%d %H:%M') if obj.updated else "—"
    updated_display.short_description = "Last Updated"


@admin.register(Task)
class TaskAdmin(ImportExportModelAdmin):
    resource_class = TaskResource
    
    # Simplified list_display for better performance
    list_display = (
        'order_number', 
        'task_name_display', 
        'customer_display', 
        'project_display',
        'branch',
        'status', 
        'final_price_display',
        'paid_status',
        'closed',
        'created_at_display'
    )
    
    list_filter = (
        'status', 
        'paid_status',
        'task_priority', 
        'is_quote', 
        'closed',
        'canceled',
        ('created_at', admin.DateFieldListFilter),
        'currency'
    )
    
    list_editable = ('closed', 'paid_status')
    
    search_fields = (
        'order_number', 
        'task_name__name', 
        'customer_name__customer_name', 
        'project__name'
    )
    
    raw_id_fields = (
        'task_name', 
        'customer_name', 
        'project', 
        'created_by', 
        'user'
    )
    
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'total_paid_amount_display',
        'remaining_amount_display'
    )
    
    # Optimized inlines - ordered by importance and frequency of use
    inlines = [
        TaskPaymentStatusInline,  # Most important - payment status
        PaymentInline,            # Payment details
        OptimizedSubtaskInline,   # Subtasks - core functionality
        OptimizedDeliveredTaskInline,  # Delivery information

    ]
    
    list_per_page = 25  # Reduced from default 100
    list_max_show_all = 100
    
    # Custom display methods for better performance
    def task_name_display(self, obj):
        return obj.task_name.name if obj.task_name else "—"
    task_name_display.short_description = "Task Name"
    task_name_display.admin_order_field = 'task_name__name'
    
    def customer_display(self, obj):
        return obj.customer_name.customer_name if obj.customer_name else "—"
    customer_display.short_description = "Customer"
    customer_display.admin_order_field = 'customer_name__customer_name'
    
    def project_display(self, obj):
        return obj.project.name if obj.project else "—"
    project_display.short_description = "Project"
    project_display.admin_order_field = 'project__name'
    
    def final_price_display(self, obj):
        return f"{obj.final_price} {obj.currency}"
    final_price_display.short_description = "Final Price"
    final_price_display.admin_order_field = 'final_price'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = "Created"
    created_at_display.admin_order_field = 'created_at'
    
    def total_paid_amount_display(self, obj):
        return f"{obj.total_paid_amount} {obj.currency}"
    total_paid_amount_display.short_description = "Total Paid"
    
    def remaining_amount_display(self, obj):
        return f"{obj.remaining_amount} {obj.currency}"
    remaining_amount_display.short_description = "Remaining"

    fieldsets = (
        ('Basic Info', {
            'fields': ('order_number', 'task_name', 'status', 'project', 'customer_name', 'task_priority')
        }),
        ('Assignment', {
            'fields': ('created_by', 'user'),
            # 'classes': ('collapse',)
        }),
        ('Financials', {
            'fields': ('frontdesk_price', 'final_price', 'discount', 'currency', 'paid_status', 'payment_method', 'total_paid_amount_display', 'remaining_amount_display')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'job_due_date', 'quote_validity'),
            # 'classes': ('collapse',)
        }),
        ('Status & Location', {
            'fields': ('is_quote', 'closed', 'cancel_requested', 'canceled', 'final_location', 'other_location'),
            # 'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            # 'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_completed', 'mark_as_paid', 'mark_as_closed']

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='done')
        self.message_user(request, f"{updated} tasks marked as completed.")
    mark_as_completed.short_description = "Mark selected tasks as completed"
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(paid_status='P')
        self.message_user(request, f"{updated} tasks marked as paid.")
    mark_as_paid.short_description = "Mark selected tasks as paid"
    
    def mark_as_closed(self, request, queryset):
        updated = queryset.update(closed=True)
        self.message_user(request, f"{updated} tasks marked as closed.")
    mark_as_closed.short_description = "Mark selected tasks as closed"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Optimized query with essential relations for inlines
        qs = qs.select_related(
            'task_name', 
            'customer_name', 
            'project', 
            'created_by', 
            'user'
        ).prefetch_related(
            # Optimized prefetch for inlines
            models.Prefetch(
                'payments', 
                queryset=Payment.objects.select_related('paid_by').order_by('-paid_at')
            ),
            models.Prefetch(
                'subtask_set',
                queryset=Subtask.objects.select_related('name', 'user', 'vat', 'added_by').order_by('-created_at')
            ),
            models.Prefetch(
                'deliveredtask',
                queryset=DeliveredTask.objects.select_related('delivered_by', 'created_by')
            ),
            models.Prefetch(
                'activity_logs',
                queryset=TaskActivityLog.objects.select_related('user').order_by('-timestamp')
            ),
            'payment_status'
        )
        return qs

    def get_form(self, request, obj=None, **kwargs):
        # Optimize form queries
        form = super().get_form(request, obj, **kwargs)
        if 'assigned_employees' in form.base_fields:
            form.base_fields['assigned_employees'].queryset = User.objects.select_related().order_by('username')
        return form


@admin.register(Subtask)
class SubtaskAdmin(ImportExportModelAdmin):
    resource_class = SubtaskResource
    list_display = (
        'task_display', 
        'name_display', 
        'user_display', 
        'is_done', 
        'subtask_amount', 
        'currency_display',
        'created_at_display'
    )
    list_filter = (
        'is_done', 
        'currency',
        'is_project_manager',
        ('created_at', admin.DateFieldListFilter)
    )
    list_editable = ('is_done',)
    search_fields = (
        'task__order_number', 
        'name__name', 
        'user__username',
        'user__first_name',
        'user__last_name'
    )
    raw_id_fields = ('task', 'name', 'user', 'added_by', 'parent_subtask')
    readonly_fields = ('created_at', 'finished_at')
    list_per_page = 50
    
    def task_display(self, obj):
        return obj.task.order_number if obj.task else "—"
    task_display.short_description = "Task"
    task_display.admin_order_field = 'task__order_number'
    
    def name_display(self, obj):
        return obj.name.name if obj.name else "—"
    name_display.short_description = "Name"
    name_display.admin_order_field = 'name__name'
    
    def user_display(self, obj):
        return obj.user.username if obj.user else "—"
    user_display.short_description = "User"
    user_display.admin_order_field = 'user__username'
    
    def currency_display(self, obj):
        return obj.currency
    currency_display.short_description = "Currency"
    currency_display.admin_order_field = 'currency'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = "Created"
    created_at_display.admin_order_field = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'task', 'name', 'user', 'vat', 'added_by'
        )

    fieldsets = (
        ('Basic Info', {
            'fields': ('task', 'name', 'user', 'is_done', 'is_project_manager')
        }),
        ('Pricing', {
            'fields': ('subtask_amount', 'discount', 'vat', 'currency', 'job_is_zero')
        }),
        ('Details', {
            'fields': ('location', 'notes_from_top', 'notes_from_operator'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('added_by', 'parent_subtask', 'created_at', 'finished_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('cancel_requested', 'is_canceled', 'cancel_subtask_reason', 'is_updated', 'is_highlighted'),
            'classes': ('collapse',)
        }),
    )


# Custom Admin Site
class CustomAdminSite(admin.AdminSite):
    site_header = 'Bookstop Administration'
    site_title = 'Bookstop Admin Portal'
    index_title = 'Welcome to Bookstop Admin'

custom_admin_site = CustomAdminSite(name='custom_admin')