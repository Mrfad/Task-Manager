from django.urls import path, reverse_lazy
from .views import login_view, logout_view, profile_view, profile_edit

app_name = 'users'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile_view'),
     path('profile/<int:user_id>/', profile_view, name='profile_detail'),
    path('profile-edit/', profile_edit, name='profile_edit'),

]


