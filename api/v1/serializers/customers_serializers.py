from rest_framework import serializers
from customers.models import Customer, CountryCodes

# --- Nested Country Code Serializer ---
class CountryCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryCodes
        fields = ['id', 'country_name', 'country_code', 'country_phone_code']

# --- Customer Serializer (Full CRUD) ---
class CustomerSerializer(serializers.ModelSerializer):
    country_code = CountryCodeSerializer(read_only=True)
    country_code_id = serializers.PrimaryKeyRelatedField(
        source='country_code', queryset=CountryCodes.objects.all(), write_only=True
    )
    image = serializers.ImageField(required=False)

    class Meta:
        model = Customer
        fields = [
            'customer_id', 'account_number', 'customer_name', 'company',
            'customer_phone', 'customer_address', 'email', 'website',
            'tax_number', 'notes', 'image',
            'country_code', 'country_code_id',
            'creation_date', 'modified_date', 'created_by'
        ]
        read_only_fields = ['account_number', 'creation_date', 'modified_date', 'created_by']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)
