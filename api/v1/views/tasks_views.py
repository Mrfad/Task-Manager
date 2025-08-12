from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from tasks.models import Task
from api.v1.serializers.tasks_serializers import TaskSerializer, TaskCreateSerializer
from api.v1.pagination import CustomPagination

class TaskViewset(viewsets.ModelViewSet):
    queryset = Task.objects.all().select_related('project', 'customer_name', 'task_name')
    # permission_classes = [permissions.IsAuthenticated]  # Optional: restrict access
    pagination_class = CustomPagination

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status', 'paid_status', 'customer_name', 'project']  # Add your filters here
    search_fields = ['order_number', 'task_name__name', 'customer_name__customer_name']
    ordering_fields = ['created_at', 'job_due_date', 'final_price']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCreateSerializer
        return TaskSerializer