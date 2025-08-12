from tasks.models import Notification

def notification_context(request):
    if not request.user.is_authenticated:
        return {}

    unread = Notification.objects.filter(user=request.user, is_read=False) \
        .select_related('task', 'type') \
        .order_by('-created_at')
    
    general_notifications = []
    payment_notifications = []

    for n in unread:
        if n.type and n.type.name.lower() == 'payment':
            payment_notifications.append(n)
        else:
            general_notifications.append(n)

    return {
        'notification_unread_count': len(general_notifications),
        'notifications': general_notifications[:5],
        'payment_notifications': payment_notifications[:5],
        'payment_unread_count': len(payment_notifications),
    }