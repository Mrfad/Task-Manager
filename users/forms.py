from django import forms
from django.utils.timezone import datetime
from .models import CustomUser, Profile

class ProfileForm(forms.ModelForm):
    """
    A form for updating user profile information.
    """
    class Meta:
        model = Profile
        fields = ('bio', 'profile_picture', 'mobile', 'address')
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter your bio'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your mobile number'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your address'}),
        }
        help_texts = {
            'bio': 'Enter a brief bio about yourself',
            'profile_picture': 'Upload a profile picture',
            'mobile': 'Enter your mobile number',
            'address': 'Enter your address',
        }


class UserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'}),
        }
        help_texts = {
            'first_name': 'Enter your first name',
            'last_name': 'Enter your last name',
            'email': 'Enter your email address',
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        if email!= self.instance.email:  # Check if email is being changed
            if CustomUser.objects.filter(email=email).exists():
                raise forms.ValidationError('Email address is already in use')
        return email
    