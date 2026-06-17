from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Account, Transaction
from django.db import transaction as trx
from utils.choices import TransactionType


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()          
        fields = ["id", "username", "email"]

class AccountNestedSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)    

    class Meta:
        model = Account
        fields = ["id", "account_number", "status", "balance", "user"]

class TransactionNestedSerializer(serializers.ModelSerializer):
    from_account = AccountNestedSerializer(read_only=True)
    to_account   = AccountNestedSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = [
                "id", 
                "reference_id", 
                "from_account", 
                "to_account", 
                "amount", 
                "transaction_type", 
                "status"
        ]

class TransactionWriteSerializer(serializers.ModelSerializer):
    """
        nested write- transaction serializer for writing in db, as drf will crash otherwise
        as it doesn't offer this by default. the purpose of using this is
        sort of like: creating profile while creating an account.
        similarly, here it creates account while transaction then 
        gets the account pk/uuid instead of re-hitting the GET accounts api.
    """
    from_account = AccountNestedSerializer()
    to_account = serializers.PrimaryKeyRelatedField(
            queryset = Account.objects.all(),
            required = False,
            allow_null = True,
        )
    class Meta:
        model = Transaction
        fields = ["id", "reference_id", "from_account", "to_account", "amount", "transaction_type", "status"]
        read_only_fields = ["id", "reference_id", "status"]

    def create(self, validated_data):
        #accounts pop is must as account table doesnt have such field
        account_data = validated_data.pop("from_account")
        user = validated_data.pop("user")
        
        with trx.atomic():
            from_account = Account.objects.create(
                **account_data,
                user=user,
                )    
            # to_account = Account.objects.create(**to_data)
            transaction = Transaction.objects.create(
                from_account = from_account,
                # to_account = to_account,
                **validated_data
            )
            
            return transaction      