from django.contrib import admin
from .models import Email, Attachment, EmailUserStatus, OutgoingEmail, Mailbox, UserEmailAccount, FetchStatus


@admin.register(FetchStatus)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('mailbox', 'started_at', 'finished_at', 'success', 'message')
    list_filter = ('mailbox', 'message')
    search_fields = ('mailbox', 'message')


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'sender', 'date_received', 'folder', 'assigned_to', 'status')
    list_filter = ('status', 'assigned_to')
    search_fields = ('id', 'subject', 'body', 'sender')

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'email')

@admin.register(EmailUserStatus)
class EmailUserStatusAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'is_read', 'read_at')

@admin.register(OutgoingEmail)
class OutgoingEmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender_user', 'date_sent')

@admin.register(Mailbox)
class MailboxAdmin(admin.ModelAdmin):
    list_display = ('name', 'imap_username', 'smtp_host')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # Automatically link mailbox to creator if not already linked
        if not UserEmailAccount.objects.filter(user=request.user, mailbox=obj).exists():
            UserEmailAccount.objects.create(user=request.user, mailbox=obj)

@admin.register(UserEmailAccount)
class UserEmailAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'mailbox')