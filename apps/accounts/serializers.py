from .models import Account, Transaction, LoginSession
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from utils.helpers import get_client_ip

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
    email = serializers.EmailField(required = True)
    class Meta:
        model = User
        fields = ["id", "username", "password", "email"]
        read_only_fields = ["id"]
    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email
    
    
    def create(self, validated_data):
        #pop password for security and leakage(such as logging.)
        password = validated_data.pop('password')
        
        #create_user is must for avoiding plaintext password saving.
        #it hashes the password and saves.
        user = User.objects.create_user(
            password=password, **validated_data 
        )
        return user

#custom jwt claims
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"   
    
    @classmethod
    def get_token(cls, user):
        #super() builds the base token (user_id, exp, iat, jti, token_type).
        #so We add our keys on top, then hand it back.
        token = super().get_token(user)

        # role: derived from flags you already have — no schema change.
        if user.is_superuser:
            token["role"] = "admin"
        elif user.is_staff:
            token["role"] = "staff"
        else:
            token["role"] = "user"

        #account_ids: reverse FK (user -> accounts).
        #values_list(flat=True) = ONE query returning just the ids.
        #str(...) because JSON can't serialize a UUID object — it'd crash otherwise.
        token["account_ids"] = [
            str(aid) for aid in user.accounts.values_list("id", flat=True)
        ]
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        request = self.context.get("request")
        refresh = self.get_token(self.user)
        LoginSession.objects.create(
            user=self.user,
            jti=refresh["jti"],
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )
        return data

class LoginSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginSession
        fields = ["id", "ip_address", "user_agent", "created_at", "revoked_at"]
