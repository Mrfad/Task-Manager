from rest_framework import serializers
from tasks.models import Task, Subtask, Project, TaskName
from django.contrib.auth import get_user_model

User = get_user_model()

# --- User Short Serializer ---
class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

# --- Subtask Nested Serializer ---
class SubtaskSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Subtask
        fields = ['id', 'name', 'user', 'is_done', 'total_price']

    def get_total_price(self, obj):
        return obj.total_price()

# --- Project Minimal Serializer ---
class ProjectMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']

# --- Task Name Serializer ---
class TaskNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskName
        fields = ['id', 'name']

# --- Task Nested Serializer ---
class TaskSerializer(serializers.ModelSerializer):
    task_name = TaskNameSerializer()
    customer_name = serializers.StringRelatedField()
    assigned_employees = UserShortSerializer(many=True)
    project = ProjectMiniSerializer()
    subtasks = SubtaskSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'order_number', 'task_name', 'customer_name', 'assigned_employees',
            'project', 'frontdesk_price', 'final_price', 'discount',
            'currency', 'task_priority', 'paid_status', 'status',
            'job_due_date', 'is_delivered', 'subtasks', 'created_at'
        ]
        

class TaskCreateSerializer(serializers.ModelSerializer):
    assigned_employees = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all()
    )

    class Meta:
        model = Task
        fields = [
            'task_name', 'order_number', 'status', 'project',
            'customer_name', 'created_by', 'assigned_employees',
            'user', 'file_name', 'frontdesk_price',
            'final_price', 'discount', 'currency', 'task_priority',
            'paid_status', 'payment_method', 'job_due_date',
            'quote_validity', 'notes', 'is_delivered',
            'is_quote', 'closed', 'cancel_requested', 'canceled'
        ]

    def create(self, validated_data):
        assigned_employees = validated_data.pop('assigned_employees', [])
        task = Task.objects.create(**validated_data)
        task.assigned_employees.set(assigned_employees)
        return task
