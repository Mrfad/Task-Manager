from django.contrib import admin
from .models import Payment, TaskPaymentStatus

admin.site.register(TaskPaymentStatus)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('task', 'amount', 'payment_type', 'paid_by', 'paid_at')
    list_filter = ('task', 'payment_type')
    search_fields = ('task__order_number', 'task__customer_name__customer_name', 'payment_type')
    list_editable = ('amount', 'payment_type')
    readonly_fields = ('paid_at',)
