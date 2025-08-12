# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.conf import settings
from .models import Profile, CustomUser
from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'is_active', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('username', 'first_name', 'last_name', 'email',)

admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_jobs', 'finished_jobs')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'profile_picture', 'mobile', 'address', 'bio')
        }),
        ('Stats', {
            'fields': ('total_jobs', 'finished_jobs', 'unfinished_jobs')
        }),
    )


class GroupAdminForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=FilteredSelectMultiple('Users', is_stacked=False)
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']  # include permissions as well

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Initial selected users in this group
            self.fields['users'].initial = self.instance.user_set.all()

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
        # Save users many-to-many after group is saved
        if group.pk:
            group.user_set.set(self.cleaned_data['users'])
        return group


class CustomGroupAdmin(GroupAdmin):
    form = GroupAdminForm
    list_display = ['name']
    search_fields = ['name']

    def save_model(self, request, obj, form, change):
        # Save the group itself
        super().save_model(request, obj, form, change)
        # Save the many-to-many users explicitly
        if 'users' in form.cleaned_data:
            obj.user_set.set(form.cleaned_data['users'])

# Re-register with the updated admin
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
