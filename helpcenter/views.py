# helpcenter/views.py
from django.shortcuts import render, get_object_or_404
from .models import HelpCategory, HelpArticle

def help_home(request):
    categories = HelpCategory.objects.all()
    return render(request, 'helpcenter/home.html', {'categories': categories})

def category_detail(request, slug):
    category = get_object_or_404(HelpCategory, slug=slug)
    articles = category.articles.all()
    return render(request, 'helpcenter/category_detail.html', {
        'category': category,
        'articles': articles
    })

def article_detail(request, slug):
    article = get_object_or_404(HelpArticle, slug=slug)
    return render(request, 'helpcenter/article_detail.html', {'article': article})