from django.urls import path
from .views import (add_customer_modal, customers_list, 
                    customer_detail, customer_edit, 
                    customers_data, add_customer, merge_customers_view,
                    add_phone, edit_phone, delete_phone)


app_name = 'customers'

urlpatterns = [
    path('customers/', customers_list, name='customers_list'),
    path('customer-detail/<int:pk>/', customer_detail, name='customer_detail'),
    path('customer/<int:pk>/edit/', customer_edit, name='customer_edit'),
    path('add-customer-modal/', add_customer_modal, name='add_customer_modal'),
    path('add-customer/', add_customer, name='add_customer'),
    path('merge-customers/', merge_customers_view, name='merge_customers'),
    path('add-phone/', add_phone, name='add_phone'),
    path('edit-phone/<pk>/', edit_phone, name='edit_phone'),
    path('delete-phone/', delete_phone, name='delete_phone'),
    path('api/data/', customers_data, name='customers_data'),
]
