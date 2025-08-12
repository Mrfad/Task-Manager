# helpcenter/urls.py
from django.urls import path
from .views import *


app_name = 'helpcenter'

urlpatterns = [
    path('home/', help_home, name='home'),
    path('<slug:slug>/', category_detail, name='category_detail'),
    path('article/<slug:slug>/', article_detail, name='article_detail'),
]