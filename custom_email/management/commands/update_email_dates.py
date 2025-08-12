import imaplib
import email
import email.utils
import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.timezone import make_aware, get_default_timezone

from custom_email.models import Mailbox, Email, FetchStatus

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Re‐fetch 'Date:' headers for existing Email records and correct date_received."

    def handle(self, *args, **options):
        mailboxes = Mailbox.objects.all()

        for mb in mailboxes:
            self.stdout.write(f"Processing mailbox: {mb.imap_username}")
            try:
                mail = imaplib.IMAP4(mb.imap_host, mb.imap_port)
                mail.starttls()
                mail.login(mb.imap_username, mb.imap_password)
            except Exception as e:
                raise CommandError(f"Cannot connect to {mb.imap_username}: {e}")

            # Iterate emails for this mailbox that have a UID and need updating
            qs = Email.objects.filter(mailbox=mb).exclude(uid__isnull=True)

            for email_obj in qs:
                uid = email_obj.uid
                folder = email_obj.folder

                try:
                    # Select the correct folder
                    typ, _ = mail.select(f'"{folder}"', readonly=True)
                    if typ != 'OK':
                        self.stdout.write(f"  Skipping UID {uid} (cannot select folder '{folder}').")
                        continue

                    # Fetch only the Date header via UID
                    typ, msg_data = mail.uid('FETCH', str(uid), '(BODY.PEEK[HEADER.FIELDS (DATE)])')
                    if typ != 'OK' or not msg_data or msg_data[0] is None:
                        self.stdout.write(f"  Skipping UID {uid} (no response from FETCH).")
                        continue

                    raw_header = msg_data[0][1]  # bytes containing "Date: …"
                    if not raw_header:
                        self.stdout.write(f"  No Date header for UID {uid}.")
                        continue

                    # Parse the header bytes into a message object, extract Date field
                    msg = email.message_from_bytes(raw_header)
                    date_header = msg.get("Date", "")
                    if not date_header:
                        self.stdout.write(f"  Empty Date header for UID {uid}.")
                        continue

                    # Convert to datetime
                    try:
                        parsed_dt = email.utils.parsedate_to_datetime(date_header)
                        if parsed_dt is None:
                            raise ValueError("parsedate_to_datetime returned None")
                        # If naive, make aware
                        if parsed_dt.tzinfo is None:
                            parsed_dt = make_aware(parsed_dt, get_default_timezone())
                    except Exception:
                        self.stdout.write(f"  Failed to parse Date header '{date_header}' for UID {uid}.")
                        continue

                    # Only update if different
                    if email_obj.date_received != parsed_dt:
                        old = email_obj.date_received
                        email_obj.date_received = parsed_dt
                        email_obj.save(update_fields=["date_received"])
                        self.stdout.write(
                            f"  Updated UID {uid}: {old.isoformat()} → {parsed_dt.isoformat()}"
                        )
                    else:
                        self.stdout.write(f"  UID {uid} already up-to-date.")

                except Exception as e:
                    self.stdout.write(f"  Error on UID {uid}: {e}")
                    continue

            mail.logout()
            self.stdout.write(f"Finished mailbox: {mb.imap_username}\n")

        self.stdout.write(self.style.SUCCESS("All done."))
