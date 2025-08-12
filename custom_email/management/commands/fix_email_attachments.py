from django.core.management.base import BaseCommand
from custom_email.models import Email, Attachment

class Command(BaseCommand):
    help = "Update has_attachments field for existing emails"

    def handle(self, *args, **options):
        total = 0
        updated = 0

        for email in Email.objects.all():
            total += 1
            has_attachments = Attachment.objects.filter(email=email).exists()
            if email.has_attachments != has_attachments:
                email.has_attachments = has_attachments
                email.save(update_fields=["has_attachments"])
                updated += 1
                self.stdout.write(f"Updated email {email.id} -> has_attachments={has_attachments}")

        self.stdout.write(self.style.SUCCESS(f"Checked {total} emails, updated {updated}"))
