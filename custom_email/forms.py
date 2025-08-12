from django import forms
from django.core.exceptions import ValidationError
from .models import Mailbox


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return single_file_clean(data, initial)

class SendEmailForm(forms.Form):
    mailbox = forms.ModelChoiceField(queryset=Mailbox.objects.all())
    to_email = forms.CharField(
        label="Recipients",
        widget=forms.Textarea(attrs={'rows': 2}),
        help_text="Separate multiple emails with commas or semicolons"
    )
    cc = forms.CharField(label="CC", required=False)
    bcc = forms.CharField(label="BCC", required=False)
    subject = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea)
    attachments = MultipleFileField(
        required=False,
        help_text="Max 10MB total (multiple files allowed)"
    )

    EMAIL_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

    def clean_attachments(self):
        attachments = self.files.getlist('attachments')
        if not attachments:
            return []
            
        # Check individual file sizes
        for attachment in attachments:
            if attachment.size > self.EMAIL_MAX_UPLOAD_SIZE:
                raise ValidationError(
                    f"File '{attachment.name}' exceeds 10MB limit. "
                    f"Max size is {self.EMAIL_MAX_UPLOAD_SIZE/1024/1024}MB"
                )
        
        # Check total size
        total_size = sum(f.size for f in attachments)
        if total_size > self.EMAIL_MAX_UPLOAD_SIZE:
            raise ValidationError(
                f"Total attachments size {total_size/1024/1024:.2f}MB "
                f"exceeds limit of {self.EMAIL_MAX_UPLOAD_SIZE/1024/1024}MB"
            )
        
        return attachments

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['mailbox'].queryset = Mailbox.objects.filter(useremailaccount__user=user)

        # 🏷️ Add the Tagify-compatible class to email fields
        tag_fields = ['to_email', 'cc', 'bcc']
        for field in tag_fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control tag-email',
                'placeholder': f"Add {field.replace('_', ' ')}"
            })


class ReplyEmailForm(forms.Form):
    subject = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea)
