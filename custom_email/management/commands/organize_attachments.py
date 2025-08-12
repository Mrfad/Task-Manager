import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from custom_email.models import Attachment  # adjust if your app name differs

class Command(BaseCommand):
    help = 'Move attachments into mailbox folders and update paths'

    def handle(self, *args, **options):
        moved = 0
        skipped = 0

        for attachment in Attachment.objects.select_related('email__mailbox'):
            old_path = attachment.file.path
            if not os.path.exists(old_path):
                self.stdout.write(self.style.WARNING(f"Missing: {old_path}"))
                continue

            mailbox_name = attachment.email.mailbox.name.replace(" ", "_")
            new_dir = os.path.join(settings.MEDIA_ROOT, "attachments", mailbox_name)
            os.makedirs(new_dir, exist_ok=True)

            new_path = os.path.join(new_dir, os.path.basename(old_path))

            if old_path == new_path:
                skipped += 1
                continue

            try:
                shutil.move(old_path, new_path)
                # Update path relative to MEDIA_ROOT
                attachment.file.name = f"attachments/{mailbox_name}/{os.path.basename(old_path)}"
                attachment.save(update_fields=["file"])
                moved += 1
                self.stdout.write(self.style.SUCCESS(f"Moved: {old_path} → {new_path}"))
            except Exception as e:
                self.stderr.write(f"Failed to move {old_path}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f"✅ Done. Moved: {moved}, Skipped: {skipped}"))
