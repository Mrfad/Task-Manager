from django.contrib import admin
from .models import ActivityLog



@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'content_type', 'content_object')
    list_filter = ('user', 'content_type')
    search_fields = ('user', 'action', 'timestamp', 'content_type', 'content_object')
    list_editable = ('action',)
    readonly_fields = ('timestamp',)

