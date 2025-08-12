from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import FormView
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Profile
from .forms import ProfileForm, UserForm

User = get_user_model()

@login_required
def role_redirect_view(request):
    user = request.user
    print('hello')
    if user.groups.filter(name='Managers').exists():
        return redirect('tasks:stats')
    elif user.groups.filter(name='Cashier').exists():
        return redirect('payments:unpaid_jobs')
    elif user.groups.filter(name='Graphic').exists():
        return redirect('tasks:my_tasks')
    else:
        return redirect('tasks:home')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('role_redirect')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('users:login')


@login_required
def profile_view(request, user_id=None):
    if user_id:
        # Viewing another user's profile
        user = get_object_or_404(User, pk=user_id)
    else:
        # Viewing your own profile
        user = request.user

    profile, _ = Profile.objects.get_or_create(user=user)

    from tasks.models import Task

    # Count completed and in-progress jobs for this user
    completed_jobs = Task.objects.filter(assigned_employees=user, status='closed').count()
    in_progress_jobs = Task.objects.filter(assigned_employees=user, status='in_progress').count()

    context = {
        'profile_user': user,  # use this instead of `user` in template
        'profile': profile,
        'is_own_profile': (request.user == user),
        'completed_jobs': completed_jobs,
        'in_progress_jobs': in_progress_jobs,
    }

    return render(request, 'users/profile.html', context)


def profile_edit(request):
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        user_form = UserForm(request.POST, instance=request.user)
        
        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()
            user_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('users:profile_view')
    else:
        profile_form = ProfileForm(instance=request.user.profile)
        user_form = UserForm(instance=request.user)
    
    return render(request, 'users/profile-edit.html', {
        'profile_form': profile_form,
        'user_form': user_form
    })
