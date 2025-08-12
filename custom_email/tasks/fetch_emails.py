# fetch_emails.py

import imaplib
import email
import re
import email.utils
import logging

from email.header import decode_header
from django.utils import timezone
from django.utils.timezone import make_aware, get_default_timezone
from django.core.files.base import ContentFile

from custom_email.models import Mailbox, FetchStatus, Email, Attachment
from celery import shared_task

logger = logging.getLogger(__name__)

JUNK_FOLDERS = {'junk', 'junk e-mail', 'spam'}


def sanitize_string(s):
    return s.replace('\x00', '').strip() if s else ''


def decode_header_field(field):
    try:
        decoded, encoding = decode_header(field)[0]
        if isinstance(decoded, bytes):
            decoded = decoded.decode(encoding or 'utf-8', errors='ignore')
        return sanitize_string(decoded)
    except Exception as e:
        logger.warning(f"Header decode failed: {e}")
        return sanitize_string(field)


@shared_task(name="custom_email.tasks.fetch_all_emails") 
def fetch_all_emails():
    logger.info("📥 Starting email fetch task")

    for mb in Mailbox.objects.all():
        logger.info(f"📬 Processing mailbox: {mb.imap_username}")
        status = FetchStatus.objects.create(mailbox=mb)

        try:
            logger.info("🔗 Connecting to IMAP server...")
            mail = imaplib.IMAP4(mb.imap_host, mb.imap_port)
            mail.starttls()
            mail.login(mb.imap_username, mb.imap_password)
            logger.info("✅ Connected and authenticated successfully.")

            logger.info("📂 Fetching available folders...")
            typ, folders = mail.list()
            if typ != 'OK' or not folders:
                raise Exception("Failed to list folders or no folders returned")

            folder_names = []

            for folder_bytes in folders:
                try:
                    folder_line = folder_bytes.decode(errors="ignore").strip()

                    # Extract folder name (either quoted or unquoted at end)
                    match = re.search(r'(?:"([^"]+)"|([^" ]+))\s*$', folder_line)
                    if not match:
                        logger.warning(f"⚠️ Could not parse folder line: {folder_line}")
                        continue

                    folder_name = match.group(1) or match.group(2)
                    folder_name = sanitize_string(folder_name)

                    if any(junk in folder_name.lower() for junk in JUNK_FOLDERS):
                        logger.info(f"🚫 Skipping junk folder: {folder_name}")
                        continue

                    folder_names.append(folder_name)

                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse folder line: {folder_bytes} — {e}")
                    continue

            if not any(name.upper() == "INBOX" for name in folder_names):
                folder_names.insert(0, "INBOX")
                logger.warning("📥 Manually injecting INBOX into folders (not returned by server)")

            logger.info(f"📋 Parsed folders: {', '.join(folder_names)}")

            for folder in folder_names:
                try:
                    logger.info(f"📂 Selecting folder: {folder}")
                    typ, data = mail.select(f'"{folder}"', readonly=True)
                    if typ != 'OK':
                        logger.warning(f"⚠️ Could not select folder: {folder}")
                        continue

                    normalized_folder = folder.lower().replace('.', '').strip()

                    latest_uid_obj = Email.objects.filter(
                        mailbox=mb,
                        folder=normalized_folder,
                        uid__isnull=False
                    ).order_by('-uid').first()
                    last_uid = latest_uid_obj.uid if latest_uid_obj else 0

                    typ, data = mail.uid('SEARCH', None, f'UID {last_uid + 1}:*')
                    if typ != 'OK':
                        logger.warning(f"⚠️ UID search failed in folder: {folder}")
                        continue

                    uid_nums = data[0].split()
                    logger.info(f"📨 Found {len(uid_nums)} new emails in folder '{folder}'")

                    for uid in uid_nums:
                        try:
                            uid_str = uid.decode()
                            typ, msg_data = mail.uid('FETCH', uid, '(RFC822)')
                            if typ != 'OK':
                                continue

                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)

                            subject = decode_header_field(msg.get("Subject", ""))
                            from_ = sanitize_string(msg.get("From", ""))
                            to = sanitize_string(msg.get("To", ""))
                            msg_id = sanitize_string(
                                msg.get("Message-ID", f"{uid_str}@{mb.id}-{folder}")
                            )

                            # Skip duplicates by UID or message_id
                            if Email.objects.filter(
                                mailbox=mb,
                                folder=normalized_folder,
                                uid=int(uid)
                            ).exists() or Email.objects.filter(message_id=msg_id).exists():
                                continue

                            # === Parse the Date: header into a timezone-aware datetime ===
                            date_header = msg.get("Date", "")
                            if date_header:
                                try:
                                    parsed_dt = email.utils.parsedate_to_datetime(date_header)
                                    # If parsed_dt is naive (no tz), make it aware in default TZ
                                    if parsed_dt.tzinfo is None:
                                        parsed_dt = make_aware(parsed_dt, get_default_timezone())
                                except Exception:
                                    parsed_dt = timezone.now()
                            else:
                                parsed_dt = timezone.now()
                            # ==================================================================

                            # Extract plain-text body
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    ctype = part.get_content_type()
                                    disp = part.get("Content-Disposition", "")
                                    if ctype == "text/plain" and "attachment" not in disp:
                                        try:
                                            body = sanitize_string(
                                                part.get_payload(decode=True).decode(errors="ignore")
                                            )
                                            break
                                        except Exception:
                                            continue
                            else:
                                try:
                                    body = sanitize_string(
                                        msg.get_payload(decode=True).decode(errors="ignore")
                                    )
                                except Exception:
                                    pass

                            email_obj = Email.objects.create(
                                mailbox=mb,
                                sender=from_,
                                recipients=to,
                                subject=subject or "(No Subject)",
                                body=body,
                                date_received=parsed_dt,  # use the parsed email date
                                message_id=msg_id,
                                uid=int(uid),
                                folder=normalized_folder,
                                is_read=False,
                                status='new',
                                has_attachments=False,
                            )

                            # === Process attachments ===
                            has_attachments = False
                            for part in msg.walk():
                                filename = part.get_filename()
                                if filename:
                                    try:
                                        decoded_filename, enc = decode_header(filename)[0]
                                        if isinstance(decoded_filename, bytes):
                                            decoded_filename = decoded_filename.decode(
                                                enc or "utf-8", errors="ignore"
                                            )
                                        decoded_filename = sanitize_string(decoded_filename)
                                    except Exception:
                                        decoded_filename = "unknown_filename"

                                    # Avoid saving duplicate attachments
                                    if Attachment.objects.filter(
                                        email=email_obj,
                                        filename=decoded_filename
                                    ).exists():
                                        continue

                                    file_data = part.get_payload(decode=True)
                                    if file_data:
                                        Attachment(
                                            email=email_obj,
                                            filename=decoded_filename
                                        ).file.save(
                                            decoded_filename,
                                            ContentFile(file_data),
                                            save=True
                                        )
                                        has_attachments = True

                            if has_attachments:
                                email_obj.has_attachments = True
                                email_obj.save(update_fields=["has_attachments"])

                        except Exception as email_error:
                            logger.error(f"❌ Error processing UID {uid}: {email_error}")

                except Exception as e:
                    logger.warning(f"⚠️ Exception selecting folder '{folder}': {e}")

            status.success = True
            status.message = f"✅ Fetched folders: {', '.join(folder_names)}"
            mail.logout()
            logger.info(f"✅ Finished fetching for {mb.imap_username}")

        except Exception as e:
            logger.error(f"❌ Fetch failed for mailbox {mb.imap_username}: {e}")
            status.success = False
            status.message = str(e)

        status.finished_at = timezone.now()
        status.save()
        logger.info(f"📦 FetchStatus saved for mailbox: {mb.imap_username}")
