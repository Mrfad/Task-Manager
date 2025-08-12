# helpcenter/admin.py

from django.contrib import admin
from .models import HelpCategory, HelpArticle

@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'category', 'is_active', 'created_at']
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'content']
