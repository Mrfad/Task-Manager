# admin.py
# customers/admin.py
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget
from .models import CountryCodes, Customer, Phone
from django.contrib.auth import get_user_model

User = get_user_model()

admin.site.register(Phone)


class CustomerResource(ModelResource):
    country_code = Field(
        column_name='country_code',
        attribute='country_code',
        widget=ForeignKeyWidget(CountryCodes, 'id')  # This fixes the FK import!
    )
    created_by = Field(
        column_name='created_by',
        attribute='created_by',
        widget=ForeignKeyWidget(User, 'id')  # This fixes the user FK!
    )

    class Meta:
        model = Customer
        import_id_fields = ()
        skip_unchanged = True
        report_skipped = True
        fields = (
            'account_number', 'customer_name', 'company', 'image',
            'country_code', 'customer_phone', 'customer_address', 'email',
            'website', 'tax_number', 'created_by',
            'creation_date', 'modified_date', 'notes'
        )

class CustomerAdmin(ImportExportModelAdmin):
    resource_class = CustomerResource
    list_display = ('account_number', 'customer_name', 'company', 'customer_phone', 'email', 'creation_date')
    list_filter = ('creation_date', 'country_code')
    search_fields = ('account_number', 'customer_name', 'company', 'customer_phone', 'email')
    raw_id_fields = ('created_by', 'country_code')
    readonly_fields = ('account_number', 'creation_date','modified_date')
    fieldsets = (
        ('Basic Info', {
            'fields': ('account_number', 'image', 'customer_name', 'company')
        }),
        ('Contact Info', {
            'fields': ('country_code', 'customer_phone', 'customer_address', 'email', 'website')
        }),
        ('Financial Info', {
            'fields': ('tax_number',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'creation_date','modified_date', 'notes')
        }),
    )
    list_per_page = 25

class CountryCodesAdmin(ImportExportModelAdmin):
    list_display = ('country_name', 'country_code', 'country_phone_code')
    search_fields = ('country_name', 'country_code')
    list_per_page = 25

admin.site.register(CountryCodes, CountryCodesAdmin)
admin.site.register(Customer, CustomerAdmin)