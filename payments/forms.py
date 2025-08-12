# payments/forms.py
from django import forms
from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_type', 'payment_method', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Enforce select styling
        self.fields['payment_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['payment_method'].widget.attrs.update({'class': 'form-select'})

        # Set default value
        self.fields['payment_type'].initial = 'full'

        # Force the field to be required, disabling the blank choice
        self.fields['payment_type'].required = True

        # Optional: you can explicitly reset choices to enforce no empty
        self.fields['payment_type'].choices = [
            ('down', 'Down Payment'),
            ('full', 'Full Payment'),
        ]