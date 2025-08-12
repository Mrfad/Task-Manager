from django.urls import path, include


urlpatterns = [
    path('v1/', include('api.v1.urls')),
    # path('v2/', include('v2.urls')),

]