from django.db.models import Q, Avg, Sum
from .models import *
from payments.models import Payment
from decimal import Decimal
from datetime import datetime, date
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from tasks.models import Notification, NotificationType
import json
import os
import zipfile
from io import BytesIO
from django.core.files import File
from django.conf import settings

User = get_user_model()

##########################################################################################
################################ Creates zip file ########################################

IGNORED_FILENAMES = [
    'logo.png', 'logo.jpg', 'logo.jpeg',
    'image001.png', 'image002.png',
    'signature.png', 'spacer.gif',
]

def is_useless_attachment(file_path, filename):
    filename_lower = filename.lower()

    # Ignore known filenames
    if filename_lower in IGNORED_FILENAMES:
        return True

    # Ignore by prefix
    if filename_lower.startswith('image') and filename_lower.endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return True

    # Ignore tiny files (e.g. under 5KB)
    try:
        if os.path.getsize(file_path) < 5 * 1024:
            return True
    except FileNotFoundError:
        return True

    return False


def zip_email_attachments(email, target_filename=None):
    """
    Zips all attachments of an email and returns a Django File object.
    The zip is saved under MEDIA_ROOT/zipped_attachments/

    :param email: Email instance
    :param target_filename: Optional custom zip filename
    :return: File object ready to assign to FileField (e.g. task.file_name)
    """
    attachments = email.attachment_set.all()
    if attachments.count() < 1:
        return None

    zip_buffer = BytesIO()
    has_valid_files = False

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for attachment in attachments:
            file_path = attachment.file.path
            filename = attachment.filename or os.path.basename(file_path)

            if is_useless_attachment(file_path, filename):
                continue  # ✅ Skip it

            zip_file.write(file_path, arcname=filename)
            has_valid_files = True

    if not has_valid_files:
        return None  # ⛔ Don't create zip if nothing valid

    zip_buffer.seek(0)
    zip_name = target_filename or f"email_{email.id}_attachments.zip"
    zip_path = os.path.join(settings.MEDIA_ROOT, 'zipped_attachments', zip_name)

    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    with open(zip_path, 'wb') as f:
        f.write(zip_buffer.read())

    return File(open(zip_path, 'rb')), zip_name


##########################################################################################
################ Creates Notification object and Channels notification ###################

def notify_user_about_task(user, task, message=None, type_name=None):
    """
    Creates a Notification and sends it via WebSocket.
    """
    from tasks.models import NotificationType

    created_by = task.created_by.get_full_name() if task.created_by else "System"
    due_date = getattr(task, 'due_date', None)
    due_date = str(due_date) if due_date else ""

    default_msg = message or f"New Task assigned: {task.task_name}"

    # Determine notification type
    if type_name:
        notif_type, _ = NotificationType.objects.get_or_create(name=type_name.lower())
    elif "paid" in default_msg.lower():
        notif_type, _ = NotificationType.objects.get_or_create(name="payment")
    else:
        notif_type, _ = NotificationType.objects.get_or_create(name="task")

    # Build extra_data dict
    extra_data = {
        "created_by": created_by
    }
    if due_date:
        extra_data["due_date"] = due_date

    # Create the notification
    Notification.objects.create(
        user=user,
        task=task,
        message=default_msg,
        type=notif_type,
        extra_data=extra_data
    )

    # Prepare WebSocket payload
    payload = {
        "type": "notify",
        "message": default_msg,
        "task_id": task.id,
        "task_title": task.task_name.name,
        "created_by": created_by,
        "category": notif_type.name.lower(),
    }
    if due_date:
        payload["due_date"] = due_date

    # Send via WebSocket
    async_to_sync(get_channel_layer().group_send)(
        f"user_{user.id}",
        {
            "type": "send_notification",
            "message": json.dumps(payload)
        }
    )

########################################################################
############################### Charts #################################
def get_quarter_usd(quarter_number):
    users = User.objects.filter(groups__name='Graphics').filter(is_active=True)
    user_statsusd = []
    for user in users:
        tasksusd = Task.objects.filter(user = user).filter(currency='USD').filter(created_at__quarter=quarter_number)
        
        total_final_priceusd = 0
        for task in tasksusd:
            total_final_priceusd += task.final_price

        user_statsusd.append({
            'user': user,
            'total_final_price': total_final_priceusd,
        })
    return user_statsusd

def get_quarter_lbp(quarter_number):
    users = User.objects.filter(groups__name='Graphics').filter(is_active=True)
    user_statsusd = []
    for user in users:
        tasksusd = Task.objects.filter(user = user).filter(currency='LBP').filter(created_at__quarter=quarter_number)
        
        total_final_priceusd = 0
        for task in tasksusd:
            total_final_priceusd += task.final_price

        user_statsusd.append({
            'user': user,
            'total_final_price': total_final_priceusd,
        })
    return user_statsusd

def get_year_usd(year_number):
    users = User.objects.filter(groups__name='Graphics').filter(is_active=True)
    user_statsusd = []
    for user in users:
        tasksusd = Task.objects.filter(user = user).filter(currency='USD').filter(created_at__year=year_number)
        
        total_final_priceusd = 0
        for task in tasksusd:
            total_final_priceusd += task.final_price

        user_statsusd.append({
            'user': user,
            'total_final_price': total_final_priceusd,
        })
    return user_statsusd

def get_year_lbp(year_number):
    users = User.objects.filter(groups__name='Graphics').filter(is_active=True)
    user_statslbp = []
    for user in users:
        taskslbp = Task.objects.filter(user = user).filter(currency='LBP').filter(created_at__year=year_number)

        total_final_pricelbp = 0
        for task in taskslbp:
            total_final_pricelbp  += task.final_price

        user_statslbp.append({
            'user': user,
            'total_final_price': total_final_pricelbp,
        })
    return user_statslbp

    # get all monthes in the selected year
def get_all_monthes_in_year_usd(year_number):
    month_statsusd = []
    for month in range(1, 13):
        datetime_object = datetime.strptime(str(month), "%m")
        month_usd = Task.objects.filter(currency='USD', created_at__month=month, created_at__year=year_number).aggregate(Sum('final_price'))
        amount = month_usd['final_price__sum'] or 0
        month_statsusd.append({
            'month': datetime_object.strftime("%B"),
            'Amount': amount,
        })
    return month_statsusd

def get_all_monthes_in_year_lbp(year_number):
    month_statslbp = []
    for month in range(1, 13):
        datetime_object = datetime.strptime(str(month), "%m")
        month_lbp = Task.objects.filter(currency='LBP', created_at__month=month, created_at__year=year_number).aggregate(Sum('final_price'))
        amount = month_lbp['final_price__sum'] or 0
        month_statslbp.append({
            'month': datetime_object.strftime("%B"),
            'Amount': amount,
        })
    return month_statslbp


def get_all_monthes_in_quarter_usd(year_number, quarter_number):
    month_statsusd = []
    
    first = 0
    last = 0
    if quarter_number == '1':
        first = 1 
        last = 4
    elif quarter_number == '2':
        first = 4 
        last = 7
    elif quarter_number == '3':
        first = 7 
        last = 10
    elif quarter_number == '4':
        first = 10 
        last = 13

    for month in range(first, last):
        datetime_object = datetime.strptime(str(month), "%m")
        month_usd = Task.objects.filter(currency='USD').filter(created_at__month=month).filter(created_at__year=year_number).aggregate(Sum('final_price'))
        amount = month_usd['final_price__sum']
        if amount is None:
             month_statsusd.append({
            'month': datetime_object.strftime("%B"),
            'Amount': 0,
        })
        else:
            month_statsusd.append({
                'month': datetime_object.strftime("%B"),
                'Amount': amount,
            })

    return month_statsusd

def get_all_monthes_in_quarter_lbp(year_number, quarter_number):
    month_statslbp = []

    first = 0
    last = 0
    if quarter_number == '1':
        first = 1 
        last = 4
    elif quarter_number == '2':
        first = 4 
        last = 7
    elif quarter_number == '3':
        first = 7 
        last = 10
    elif quarter_number == '4':
        first = 10 
        last = 13
    print(first, last)
    for month in range(first, last):
        datetime_object = datetime.strptime(str(month), "%m")
        month_lbp = Task.objects.filter(currency='LBP').filter(created_at__month=month).filter(created_at__year=year_number).aggregate(Sum('final_price'))
        amount = month_lbp['final_price__sum']
        if amount is None:
             month_statslbp.append({
            'month': datetime_object.strftime("%B"),
            'Amount': 0,
        })
        else:
            month_statslbp.append({
                'month': datetime_object.strftime("%B"),
                'Amount': amount,
            })

    return month_statslbp


def notify_user_assigned(user, message):
    # Save in DB
    Notification.objects.create(user=user, message=message)

    # Send to WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            "type": "send_notification",
            "message": message,
        }
    )