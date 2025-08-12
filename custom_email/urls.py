from django.urls import path
from .views import inbox, send_email_view, mail_detail, reply_email, customer_email_suggestions


app_name = 'mail'

urlpatterns = [
    path('inbox/', inbox, name='inbox'),
    path('send/', send_email_view, name='send_email'),
    path('mail-detail/<int:pk>/', mail_detail, name='mail_detail'),
    path('reply_email/<int:email_id>/', reply_email, name='reply_email'),

    path('customer-emails/', customer_email_suggestions, name='customer_email_suggestions'),
]
