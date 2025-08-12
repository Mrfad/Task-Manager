# payments/urls.py
from django.urls import path
from .views import make_payment, paid_jobs, unpaid_jobs, task_table_data


app_name = 'payments'

urlpatterns = [
    path('unpaid-jobs/', unpaid_jobs, name='unpaid_jobs'),
    path('paid-jobs/', paid_jobs, name='paid_jobs'),
    path('task/<int:task_id>/pay/', make_payment, name='make_payment'),
    

    # Unified AJAX data route for DataTables
    path('data/<str:status>/', task_table_data, name='task_table_data'),
]