from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse, JsonResponse
from .models import Email, Mailbox, UserEmailAccount, Attachment, OutgoingEmail
from django.core.paginator import Paginator
from .forms import ReplyEmailForm, SendEmailForm
from django.core.mail import send_mail, EmailMessage, get_connection
from django.core.cache import cache
from django.conf import settings
from django.contrib import messages
from collections import defaultdict
from email.utils import parseaddr
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models.functions import Substr
from tasks.utils import *
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.exceptions import ValidationError
from customers.models import Customer
import os
import re
import logging
import json


logger = logging.getLogger(__name__)

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB


@login_required
def customer_email_suggestions(request):
    q = request.GET.get("q", "").strip().lower()
    print("🔍 Raw query string from GET:", request.GET.get("q", ""))
    print("🧹 Cleaned query string:", q)

    if not q or len(q) < 2:
        print("⚠️ Query too short or empty.")
        return JsonResponse([], safe=False)

    # Step 1: Try istartswith for all fields
    startswith_matches = Customer.objects.filter(
        Q(email__istartswith=q) |
        Q(customer_phone__istartswith=q) |
        Q(customer_address__istartswith=q)
    ).values_list('email', 'customer_phone', 'customer_address').distinct()
    print("✅ istartswith matches:", list(startswith_matches))

    # Step 2: If no matches, try icontains for all fields
    if not startswith_matches:
        contains_matches = Customer.objects.filter(
            Q(email__icontains=q) |
            Q(customer_phone__icontains=q) |
            Q(customer_address__icontains=q)
        ).values_list('email', 'customer_phone', 'customer_address').distinct()
        print("📦 icontains fallback matches:", list(contains_matches))
        matches = contains_matches
    else:
        matches = startswith_matches

    # Step 3: Clean and prepare results
    suggestions = []
    seen_emails = set()  # To avoid duplicates
    
    for email, phone, address in matches:
        # Check email field first
        if email:
            name, actual_email = parseaddr(email)
            if actual_email and actual_email.lower().startswith(q.lower()):
                if actual_email not in seen_emails:
                    suggestions.append({'value': actual_email})
                    seen_emails.add(actual_email)
        
        # Check phone field for email-like patterns
        if phone and '@' in phone.lower() and '.' in phone.lower():
            possible_email = phone.strip()
            if possible_email not in seen_emails:
                suggestions.append({'value': possible_email})
                seen_emails.add(possible_email)
        
        # Check address field for email-like patterns
        if address and '@' in address.lower() and '.' in address.lower():
            # Simple email extraction from address (could be improved)
            parts = address.split()
            for part in parts:
                if '@' in part and '.' in part:
                    possible_email = part.strip(',;')
                    if possible_email not in seen_emails:
                        suggestions.append({'value': possible_email})
                        seen_emails.add(possible_email)

    print("📤 Final suggestion list:", suggestions[:20])
    return JsonResponse(suggestions[:20], safe=False)



def clean_email_list(raw_value):
    if not raw_value:
        return []
    
    try:
        # If it's a Tagify-style JSON string
        parsed = json.loads(raw_value)
        if isinstance(parsed, list) and all('value' in item for item in parsed):
            return [item['value'].strip() for item in parsed]
    except json.JSONDecodeError:
        pass

    # Fallback to plain string split
    return [e.strip() for e in re.split(r'[;,]', raw_value) if e.strip()]



def format_tagify_string(email_string):
    """
    Converts a string of comma/semicolon-separated emails into a Tagify-compatible list.
    """
    return [{"value": e} for e in clean_email_list(email_string)]


@login_required
def mail_detail(request, pk):
    email_obj = get_object_or_404(Email, pk=pk)
    attachments = email_obj.attachment_set.all()

    # Prefill for modal
    prefill = {
        "recipients": format_tagify_string(email_obj.sender),
        "cc": [],
        "bcc": [],
        "subject": f"Re: {email_obj.subject}",
        "quoted_body": (
            f"\n\n\nOn {email_obj.date_received.strftime('%Y-%m-%d %H:%M')}, "
            f"{email_obj.sender} wrote:\n{email_obj.body}"
        )
    }

    logger.debug("📨 Prefill for reply modal: %s", prefill)

    return render(request, 'custom_email/mail-detail.html', {
        "email": email_obj,
        "attachments": attachments,
        "prefill": prefill,
        'nav_title': 'Email Detail',
    })


@login_required
def reply_email(request, email_id):
    original_email = get_object_or_404(Email, id=email_id)

    if request.method == 'POST':
        try:
            recipients = clean_email_list(request.POST.get('recipients'))
            cc = clean_email_list(request.POST.get('cc'))
            bcc = clean_email_list(request.POST.get('bcc'))
            subject = request.POST.get('subject', '')
            body = request.POST.get('body', '')
            attachments = request.FILES.getlist('attachments')

            logger.debug(f"Reply form received: To={recipients}, CC={cc}, BCC={bcc}, Subject={subject}")

            if not recipients:
                messages.error(request, "Please provide at least one recipient.")
                return redirect('mail:mail_detail', original_email.pk)

            mailbox = original_email.mailbox
            connection = get_connection(
                host=mailbox.smtp_host,
                port=mailbox.smtp_port,
                username=mailbox.smtp_username,
                password=mailbox.smtp_password,
                use_tls=mailbox.smtp_use_tls
            )

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=mailbox.smtp_username,
                to=recipients,
                cc=cc,
                bcc=bcc,
                connection=connection
            )

            for attachment in attachments:
                if attachment.size > MAX_ATTACHMENT_SIZE:
                    raise ValidationError(f"Attachment '{attachment.name}' exceeds 10MB limit.")
                email.attach(attachment.name, attachment.read(), attachment.content_type)

            sent = email.send()
            logger.info("Email sent successfully. Count: %d", sent)

            OutgoingEmail.objects.create(
                original_email=original_email,
                sender_user=request.user,
                recipients=", ".join(recipients),
                subject=subject,
                body=body
            )

            if sent > 0:
                messages.success(request, "✅ Reply sent successfully.")
            else:
                messages.warning(request, "⚠️ Email sent but with no recipient response.")

        except Exception as e:
            logger.exception("Error sending reply email")
            messages.error(request, f"Failed to send reply: {e}")

        return redirect('mail:mail_detail', email_id)

    return redirect('mail:mail_detail', email_id)

@login_required
def inbox(request):
    # 1. Initial setup with efficient parameter handling
    folder = request.GET.get('folder', 'inbox')
    mailbox_id = request.GET.get('mailbox')
    search_query = request.GET.get('search', '').strip()
    
    try:
        per_page = int(request.GET.get('per_page', '10'))
    except ValueError:
        per_page = 10

    # 2. Optimized mailbox querying
    user_mailboxes = Mailbox.objects.filter(
        useremailaccount__user=request.user
    ).only('id', 'name')  # Only fetch needed fields

    selected_mailbox = (
        user_mailboxes.filter(id=mailbox_id).first() or 
        user_mailboxes.first()
    )

    if not selected_mailbox:
        return render(request, 'custom_email/inbox.html', {
            'no_mailbox': True,
            'user_mailboxes': user_mailboxes,
        })

    # 3. Cached folder structure
    cache_key = f'mailbox_folders_{request.user.id}'
    mailbox_folders = cache.get(cache_key)
    
    if not mailbox_folders:
        folders_query = Email.objects.filter(
            mailbox__in=user_mailboxes
        ).values('mailbox_id', 'folder').distinct()
        
        mailbox_folders = defaultdict(list)
        for item in folders_query:
            mailbox_folders[item['mailbox_id']].append(item['folder'])
        
        for mb_id in mailbox_folders:
            mailbox_folders[mb_id].sort()
        
        cache.set(cache_key, dict(mailbox_folders), timeout=60*15)  # 15 minutes

    # 4. Optimized email query with selective prefetching
    email_query = Email.objects.filter(
        mailbox=selected_mailbox,
        folder=folder,
    ).select_related(
        'mailbox', 
        'assigned_to'
    ).prefetch_related(
        Prefetch('attachment_set',
               queryset=Attachment.objects.only(
                   'file', 'filename', 'email_id'
               ),
               to_attr='prefetched_attachments')
    )

    # ==== INSERT SORTING LOGIC HERE ====
    sort = request.GET.get('sort', '-date_received')
    valid_sorts = {
        'sender', '-sender',
        'subject', '-subject',
        'date_received', '-date_received',
    }
    if sort not in valid_sorts:
        sort = '-date_received'
    email_query = email_query.order_by(sort)
    # ====================================

    # 5. Optimized search (only if needed)
    if search_query:
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

        vector = (
            SearchVector('subject', weight='A') + 
            SearchVector('sender', weight='B') + 
            SearchVector(Substr('body', 1, 1000000), weight='C')  # Avoids error
        )
        query = SearchQuery(search_query)
        
        email_query = email_query.annotate(
            rank=SearchRank(vector, query)
        ).filter(rank__gte=0.1).order_by('-rank', '-date_received')

    # 6. Efficient pagination (process before attachment check)
    page_number = request.GET.get('page')
    paginator = Paginator(email_query, per_page)
    page_obj = paginator.get_page(page_number)

    # 7. Optimized attachment processing (only for current page)
    cutoff_time = timezone.now() - timedelta(minutes=15)

    for email in page_obj.object_list:
        email.is_new = email.date_received >= cutoff_time
        email.has_real_attachments = any(
            not is_useless_attachment(
                a.file.path, 
                a.filename or os.path.basename(a.file.name)
            )
            for a in email.prefetched_attachments
        )

    # 8. Template context with optimized data
    context = {
        'page_obj': page_obj,
        'folder': folder,
        'selected_mailbox': selected_mailbox,
        'user_mailboxes': user_mailboxes,
        'mailbox_folders': mailbox_folders,
        'search_query': search_query,
        'per_page': per_page,
        'per_page_choices': [10, 25, 50, 100],
        'sort': sort,  # pass the current sort to template
        'nav_title': 'Inbox',
    }

    return render(request, 'custom_email/inbox.html', context)


@login_required
def send_email_view(request):
    if request.method == 'POST':
        form = SendEmailForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            mailbox = form.cleaned_data['mailbox']
            to_emails = form.cleaned_data['to_email']
            cc = form.cleaned_data.get('cc', '')
            bcc = form.cleaned_data.get('bcc', '')
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']
            attachments = form.cleaned_data.get('attachments')

            # Clean all email lists
            def clean_list(raw):
                return [e.strip() for e in re.split('[,;]', raw or '') if e.strip()]

            to_list = clean_list(to_emails)
            cc_list = clean_list(cc)
            bcc_list = clean_list(bcc)

            if not to_list:
                messages.error(request, "Please enter at least one recipient.")
                return render(request, 'custom_email/send-email.html', {'form': form})

            try:
                connection = get_connection(
                    host=mailbox.smtp_host,
                    port=mailbox.smtp_port,
                    username=mailbox.smtp_username,
                    password=mailbox.smtp_password,
                    use_tls=mailbox.smtp_use_tls
                )

                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=mailbox.smtp_username,
                    to=to_list,
                    cc=cc_list,
                    bcc=bcc_list,
                    connection=connection
                )

                for f in request.FILES.getlist('attachments'):
                    if f.size > 10 * 1024 * 1024:
                        raise ValidationError("Attachment exceeds 10MB limit")
                    email.attach(f.name, f.read(), f.content_type)

                email.send()

                messages.success(request, f"Email sent to {len(to_list)} recipient(s)")
                return redirect('email:inbox')

            except Exception as e:
                messages.error(request, f"Failed to send email: {e}")
        else:
            messages.error(request, "Please fix the form errors.")
    else:
        form = SendEmailForm(user=request.user)

    return render(request, 'custom_email/send-email.html', {'form': form, 'nav_title': 'Send Email',})