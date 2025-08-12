from django.db import models
from django.conf import settings
from django.db.models import Q, Sum
from django.core.validators import RegexValidator
from .utils import create_shortcode

class CountryCodes(models.Model):
    country_name = models.CharField(max_length=255)
    country_code = models.CharField(max_length=15)
    country_phone_code = models.CharField(max_length=5)

    def __str__(self):
        return f"{self.country_name} ({self.country_code})"

    class Meta: 
        verbose_name = "Country Code"
        verbose_name_plural = "Country Codes"
        ordering = ['country_name']


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    account_number = models.CharField(max_length=15, unique=True, blank=True)
    image = models.ImageField(default='customers/avatar.png', upload_to='customers', null=True, blank=True)
    customer_name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, null=True, blank=True)
    
    country_code = models.ForeignKey(CountryCodes, on_delete=models.SET_NULL, null=True, blank=True)
    customer_phone = models.CharField(
        max_length=20, 
        null=True, 
        blank=True, 
        unique=True,
        validators=[RegexValidator(regex=r'^\+?[\d\-]+$', message="Enter a valid phone number.")]
    )
    customer_address = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    
    creation_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    tax_number = models.CharField(max_length=20, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['customer_name']
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                name='unique_non_null_email',
                condition=~models.Q(email=None)
            )
        ]
        

    def __str__(self):
        return f"{self.customer_name}"
    

    def save(self, *args, **kwargs):
        if not self.account_number:
            unique = False
            attempt = 0
            while not unique and attempt < 5:
                attempt += 1
                shortcode = create_shortcode(self)
                if not Customer.objects.filter(account_number=shortcode).exists():
                    self.account_number = shortcode
                    unique = True

        if self.email == '':
            self.email = None
        super().save(*args, **kwargs)


    @property
    def total_usd_amount(self):
        return (
            self.task_set.filter(currency='USD')
            .aggregate(total=Sum('final_price'))['total'] or 0
        )

    @property
    def total_lbp_amount(self):
        return (
            self.task_set.filter(currency='LBP')
            .aggregate(total=Sum('final_price'))['total'] or 0
    )



class Phone(models.Model):
    country_code = models.ForeignKey(CountryCodes, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255, default='Additional Phone')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    customer_phone = models.CharField(
        max_length=20, 
        unique=True,
        validators=[RegexValidator(regex=r'^\+?[\d\-]+$', message="Enter a valid phone number.")]
    )

    def __str__(self):
        return f"({self.country_code} {self.customer_phone} {self.customer.customer_name})"
    