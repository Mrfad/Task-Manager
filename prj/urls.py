from django.contrib import admin
from django.conf import settings
from django.views.static import serve
from django.conf.urls.static import static
from django.urls import path, include, re_path

from users.views import role_redirect_view
handler403 = 'tasks.views.custom_permission_denied_view'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('redirect-me/', role_redirect_view, name='role_redirect'),
    path('', include('tasks.urls'), name='tasks'),
    path('', include('customers.urls'), name='customers'),
    path('', include('users.urls'), name='users'),
    path('payments/', include('payments.urls'), name='payments'),
    path('', include('helpcenter.urls'), name='helpcenter'),
    path('mail/', include('custom_email.urls'), name='mail'),
    path('api/', include('api.urls'), name='api'),
    re_path(r'^download/(?P<path>.*)$',serve,{'document_root':settings.MEDIA_ROOT}),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)