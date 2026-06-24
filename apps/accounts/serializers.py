from .models import Account, Transaction
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class AccountSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Account
        fields = [
            'id',
            'user',
            'account_number',
            'balance',
            'status',
        ]
        
        read_only_fields = [
            'id',
            'user',
            'balance',
            'status'
        ]

class TransactionSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Transaction
        fields = [
            "id",
            "reference_id",
            "from_account",
            "to_account",
            "amount",
            "transaction_type",
            "status",
            "reversal_of",
        ]
        read_only_fields = [
        'id',
        'reference_id',
        # 'status',
        'reversal_of'
        ]
        
class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only = True,
        required = True,
        validators = [validate_password],
        style = {'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ["id", "username", "password"]
        read_only_fields = ["id"]
        
    def create(self, validated_data):
        #pop password for security and leakage(such as logging.)
        password = validated_data.pop('password')
        
        #create_user is must for avoiding plaintext password saving.
        #it hashes the password and saves.
        user = User.objects.create_user(
            password=password, **validated_data 
        )
        return user