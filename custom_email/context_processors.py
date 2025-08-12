from collections import defaultdict
from .models import Mailbox, Email, UserEmailAccount

def user_mailboxes(request):
    if request.user.is_authenticated:
        mailboxes = UserEmailAccount.objects.filter(user=request.user).select_related('mailbox')
        return {'user_mailboxes': [link.mailbox for link in mailboxes]}
    return {'user_mailboxes': []}

def email_sidebar_context(request):
    if not request.user.is_authenticated:
        return {}

    user_mailboxes = Mailbox.objects.filter(useremailaccount__user=request.user)

    mailbox_id = request.GET.get('mailbox')
    folder = request.GET.get('folder', 'inbox')
    selected_mailbox = user_mailboxes.filter(id=mailbox_id).first() or user_mailboxes.first()

    # DEFAULT_FOLDERS = ['inbox', 'sent', 'outbox']
    DEFAULT_FOLDERS = [choice[0] for choice in Email._meta.get_field('folder').choices]

    mailbox_folders = defaultdict(list)

    for mailbox in user_mailboxes:
        folders = Email.objects.filter(mailbox=mailbox).values_list('folder', flat=True).distinct()
        folder_list = sorted(set(folders)) if folders else DEFAULT_FOLDERS
        if not folder_list:
            folder_list = DEFAULT_FOLDERS
        mailbox_folders[mailbox.id] = folder_list

    return {
        'user_mailboxes': user_mailboxes,
        'selected_mailbox': selected_mailbox,
        'mailbox_folders': dict(mailbox_folders),
        'folder': folder,
    }

