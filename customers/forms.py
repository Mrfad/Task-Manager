from django import forms
from .models import Customer, CountryCodes, Phone

class CustomerForm(forms.ModelForm):
    country_code = forms.ModelChoiceField(
        queryset=CountryCodes.objects.all(),
        required=False
    )

    class Meta:
        model = Customer
        fields = [
            'customer_name',
            'country_code',
            'customer_phone',
            'company',
            'customer_address',
            'email',
            'website',
            'tax_number',
            'image',
            'notes'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields['country_code'].initial = CountryCodes.objects.get(id=102)
        except CountryCodes.DoesNotExist:
            self.fields['country_code'].initial = None  # Or a fallback object if needed

    def clean_customer_phone(self):
        phone = self.cleaned_data.get('customer_phone')
        if phone:
            phone = phone.replace(' ', '').strip()
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip()

            # Check uniqueness
            qs = Customer.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This email address is already in use.")
        return email
    


class Phoneform(forms.ModelForm):
    country_code = forms.ModelChoiceField(
        queryset=CountryCodes.objects.all(),
        required=False
    )

    class Meta:
        model = Phone
        fields = ['name', 'country_code', 'customer_phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields['country_code'].initial = CountryCodes.objects.get(id=102)
        except CountryCodes.DoesNotExist:
            self.fields['country_code'].initial = None  # Or a fallback object if needed