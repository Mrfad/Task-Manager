from django import forms
from tasks.models import Task, Subtask, CurrencyRate, DeliveredTask, Project
from customers.models import Customer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class RateForm(forms.ModelForm):
    class Meta:
        model = CurrencyRate
        fields = '__all__'


class TaskForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.none())  # placeholder, set in __init__

    class Meta:
        model = Task
        fields = [
            'task_name',
            'customer_name',
            'branch',
            'project',
            'task_priority',
            'frontdesk_price',
            'currency',
            'user',
            'payment_method',
            'job_due_date',
            'file_name',
            'notes',
        ]
        widgets = {
            'job_due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)

        # ✅ Step 1: Define allowed group names (case-insensitive matching via DB)
        allowed_groups = ["Graphic", "Typing", "Autocad", "Laser", "Outdoor", "FrontDesk"]

        # ✅ Step 2: Filter active users from any of the allowed groups
        self.fields['user'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=allowed_groups
        ).distinct()

        # ✅ Step 3: Apply Bootstrap styling to all fields
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control form-control-sm'})

class SubtaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        task = kwargs.pop('task', None)
        super(SubtaskForm, self).__init__(*args, **kwargs)

        if task:
            allowed_groups = ["Graphic", "Typing", "Autocad", "Laser", "Outdoor", "FrontDesk"]

            # Gather all users from allowed groups
            users_qs = User.objects.none()  # Start with empty QS
            for group_name in allowed_groups:
                try:
                    group = Group.objects.get(name__iexact=group_name)
                    users_qs = users_qs | group.user_set.all()
                except Group.DoesNotExist:
                    continue

            # Remove already assigned users
            assigned_user_ids = task.assigned_employees.values_list('id', flat=True)
            self.fields['user'].queryset = users_qs.exclude(id__in=assigned_user_ids).distinct()

    class Meta:
        model = Subtask
        fields = ['user', 'notes_from_top']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'notes_from_top': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class UpdateSubtaskForm(forms.ModelForm):
    final_location = forms.ChoiceField(
        choices=[('', '— Select Final Location —')] + Task.FINAL_LOCATION,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    other_location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Custom location'})
    )

    def __init__(self, *args, **kwargs):
        super(UpdateSubtaskForm, self).__init__(*args, **kwargs)
        if 'user' in self.fields:
            del self.fields['user']

    def clean(self):
        cleaned_data = super().clean()
        is_done = cleaned_data.get('is_done')
        final_location = self.data.get('final_location', '').strip()
        other_location = self.data.get('other_location', '').strip()

        if is_done:
            if not final_location and not other_location:
                self.add_error("","Please provide a final or custom location.")
            if final_location and other_location:
                self.add_error("Choose either a final location or a custom location, not both.")

        return cleaned_data

    class Meta:
        model = Subtask
        fields = ['is_done', 'name', 'notes_from_operator', 'subtask_amount']
        widgets = {
            'notes_from_operator': forms.Textarea({
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any updates or notes about this subtask'
            }),
            'is_done': forms.CheckboxInput({'class': 'form-check-input'}),
            'subtask_amount': forms.NumberInput({'class': 'form-control', 'step': '0.01'}),
        }

class RequestCancelSubtaskForm(forms.ModelForm):
    class Meta:
        model = Subtask
        fields = ['cancel_subtask_reason']  # This must include the field you want to show

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make the reason required only when submitting the cancel form
        self.fields['cancel_subtask_reason'].required = True
        self.fields['cancel_subtask_reason'].widget.attrs.update({
            'placeholder': 'Please provide a reason for cancellation...',
            'class': 'form-control'
        })
        self.fields['cancel_subtask_reason'].label = "Cancellation Reason"

class DeliveredTaskForm(forms.ModelForm):
    class Meta:
        model = DeliveredTask
        fields = ['delivered_by', 'received_person', 'notes']



class CloseTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['final_location', 'other_location']  # include only relevant fields for closing

    def clean(self):
        cleaned_data = super().clean()
        final_location = cleaned_data.get("final_location")
        other_location = cleaned_data.get("other_location")

        # If task is being closed, at least one location is required
        if not final_location and not other_location:
            raise forms.ValidationError("You must select a final location or enter a custom one.")

        return cleaned_data
    
class projectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'balance', 'currency', 'customer', 'notes']