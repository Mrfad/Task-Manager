from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone
from django.contrib.auth import get_user_model
import os


User = get_user_model()


class FetchStatus(models.Model):
    mailbox = models.ForeignKey('Mailbox', on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=False)
    message = models.TextField(blank=True)

class Mailbox(models.Model):
    name = models.CharField(max_length=100, help_text="Label for this mailbox")
    
    # IMAP Settings
    imap_host = models.CharField(max_length=255, default="mail.bookstop.co")
    imap_port = models.PositiveIntegerField(default=143)
    imap_username = models.CharField(max_length=255)
    imap_password = models.CharField(max_length=255)
    use_ssl = models.BooleanField(default=True)

    # SMTP Settings
    smtp_host = models.CharField(max_length=255, default="mail.bookstop.co")
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=255)
    smtp_password = models.CharField(max_length=255)
    smtp_use_tls = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.imap_username})"
    

class UserEmailAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mailbox = models.ForeignKey(Mailbox, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} → {self.mailbox.name}"
    

STATUS_CHOICES = [
    ('new', 'New'),
    ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'),
]

class Email(models.Model):
    mailbox = models.ForeignKey('Mailbox', on_delete=models.CASCADE)
    sender = models.CharField(max_length=512)
    recipients = models.TextField()
    subject = models.CharField(max_length=2024)
    body = models.TextField()
    date_received = models.DateTimeField()
    has_attachments = models.BooleanField(default=False)
    message_id = models.CharField(max_length=2048, unique=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_emails')
    folder = models.CharField(max_length=20, choices=[('inbox', 'Inbox'), ('sent', 'Sent'), ('outbox', 'Outbox')])
    is_read = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    uid = models.BigIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['mailbox', 'folder', 'is_read', 'date_received']),
            models.Index(fields=['mailbox', 'folder', 'status', 'date_received']),
            models.Index(fields=['mailbox', 'folder', 'date_received']),
            models.Index(fields=['mailbox', 'folder']),
            models.Index(fields=['subject']),
            models.Index(fields=['sender']),
            models.Index(fields=['message_id']),
            models.Index(fields=['uid']),
        ]

    def __str__(self):
        return f"{self.subject} from {self.sender}"

def mailbox_attachment_path(instance, filename):
    mailbox_name = instance.email.mailbox.name.replace(" ", "_")
    return f"attachments/{mailbox_name}/{filename}"

class Attachment(models.Model):
    email = models.ForeignKey(
        Email, 
        on_delete=models.CASCADE,
        db_index=True  # Added index to foreign key
    )
    file = models.FileField(upload_to=mailbox_attachment_path)
    filename = models.CharField(max_length=255)

    class Meta:
        indexes = [
            # Composite index for common query patterns
            models.Index(fields=['email', 'filename']),
            
            # Index for filename searches if you frequently filter by filename
            models.Index(fields=['filename']),
            
            # Partial index for small files if you often query by size
            # models.Index(fields=['file'], name='small_files_idx', 
            #            condition=Q(file__size__lt=5*1024)),
        ]
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"

    def __str__(self):
        return self.filename or os.path.basename(self.file.name)

class EmailUserStatus(models.Model):
    email = models.ForeignKey(Email, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('email', 'user')

class OutgoingEmail(models.Model):
    original_email = models.ForeignKey(Email, on_delete=models.SET_NULL, null=True, blank=True)
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recipients = models.TextField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
