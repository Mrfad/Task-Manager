from django.urls import path
from .views import (home, all_tasks, my_tasks, change_rate,
                    add_task_view, add_taskname_modal, create_task_from_email,
                    task_detail, update_task_view, add_subtask_modal,
                    update_subtask_modal, close_task_modal, deliver_job,
                    cancel_task_modal, send_cancel_request_modal, undo_close_task_modal,
                    undo_cancel_subtask_request_modal, approve_cancel_request_modal,
                    stats ,stats_month, stats_quarter, stats_year, get_customer_by_project,
                    export_excel, export_pdf, projects, project_detail, add_project,
                    clear_payment_notifications, clear_task_notifications,
                    assign_tasks_to_project, remove_task_from_project)


app_name = 'tasks'

urlpatterns = [
    path('', home, name='home'),
    path('all-tasks/', all_tasks, name='all_tasks'),
    path('all-tasks/<str:query>/', all_tasks, name='all_tasks_query'),
    path('my-tasks/', my_tasks, name='my_tasks'),
    path('my-tasks/<str:query>/', my_tasks, name='my_tasks_query'),
    path('add-task/', add_task_view, name='add_task'),
    path('create-from-email/<int:email_id>/', create_task_from_email, name='create_from_email'),

    path('task/detail/<int:pk>/', task_detail, name='task_detail'),
    path('task/close/<int:pk>/', close_task_modal, name='close_task_modal'),
    path('task/undoclose/<int:pk>/', undo_close_task_modal, name='undo_close_task_modal'),
    path('task/edit/<int:pk>/', update_task_view, name='update_task_view'),
    path('add-taskname-modal/', add_taskname_modal, name='add_taskname_modal'),
    path('add-subtask-modal/<str:main_task_id>/', add_subtask_modal, name='add_subtask_modal'),
    path('update-subtask-modal/<str:main_task_id>/', update_subtask_modal, name='update_subtask_modal'),

    path('cancel-request/operator/<int:pk>/', send_cancel_request_modal, name='send_cancel_request_modal'),
    path('undo-cancel-subtask-request/operator/<int:pk>/', undo_cancel_subtask_request_modal, name='undo_cancel_subtask_request_modal'),
    path('approve-cancel-request/<int:pk>/', approve_cancel_request_modal, name='approve_cancel_request_modal'),

    path('cancel_task_modal/<int:pk>/', cancel_task_modal, name='cancel_task_modal'),

    path('export/excel/', export_excel, name='export_excel'),
    path('export/pdf/', export_pdf, name='export_pdf'),

    path('deliver-job/<str:job_id>/', deliver_job, name='deliver_job'),

    # charts
    path('stats/', stats, name='stats'),
    path('stats-month/<str:month_number>/', stats_month, name='stats_month'),
    path('stats-year/<str:year_number>/', stats_year, name='stats_year'),
    path('stats-quarter/<str:quarter_number>/', stats_quarter, name='stats_quarter'),

    path('change-rate/', change_rate, name='change_rate'),

    path('projects/', projects, name='projects'),
    path('project-detail/<int:pk>/', project_detail, name='project_detail'),
    path('add-project/', add_project, name='add_project'),
    path('project/<int:project_id>/assign-tasks/', assign_tasks_to_project, name='assign_tasks_to_project'),
    path('project/<int:task_id>/remove-tasks/', remove_task_from_project, name='remove_task_from_project'),


    # AJAX view
    path('get-customer-by-project/', get_customer_by_project, name='get_customer_by_project'),
    
    path('notifications/clear/tasks/', clear_task_notifications, name='clear_task_notifications'),
    path('notifications/clear/payments/', clear_payment_notifications, name='clear_payment_notifications'),

]