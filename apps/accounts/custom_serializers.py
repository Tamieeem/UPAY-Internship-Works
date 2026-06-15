from rest_framework import serializers
from .models import Account, Transaction
from utils.choices import TransactionType
from django.db import transaction
from decimal import Decimal, InvalidOperation

class TransactionRequestSerializers(serializers.ListSerializer):
    """
        this is like--- everything manual like the APIView class,
        unlike the modelserializer, the serializer class doesn't refer
        to any model, and this is used when we usually don't need a to store
        data to a db model. such as, otp verification, third party api keys.
    """
    
    from_account = serializers.PrimaryKeyRelatedField(queryset = Account.objects.all())
    to_account = serializers.PrimaryKeyRelatedField(queryset = Account.objects.all())
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    #validations
    #validate + the field name: amount
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive, more than zero")
        return value
    
    def validate(self, data):
        if data["from_account"] == data["to_account"]:
            raise serializers.ValidationError("Can't Transfer to your OWN account")
        return data
    
    def create(self, validated_data):
        
        transaction_type = TransactionType.TRANSFER
        from_account = validated_data['from_account']
        to_account = validated_data['to_account']
        amount = validated_data['amount']
        
        return Transaction.objects.create(
            transaction_type,
            from_account,
            to_account,
            amount,
            transaction_type,
        )


class TransactionListSerializer(serializers.Serializer):
    """
        this is what the many=True does under the hood, 
        for handling list of transactions. now it is full manual,
        explicit.
    """
    def create(self, validated_data):
        with transaction.atomic():
            list_of_transactions = []
            for items in validated_data:
                list_of_transactions.append(
                    Transaction.objects.create(
                        from_account = validated_data['from_account'],
                        to_account = validated_data['to_account'],
                        amount = validated_data['amount'],
                        transaction_type = TransactionType.TRANSFER,
                    )
                    
                )
            return list_of_transactions
        


#same as the regular serializer, only for one transaction,
#that we will use for the ListSerializer class above.
class BulkTransactionSerializer(serializers.Serializer):
    """describes one transaction."""
    from_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    to_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        list_serializer_class = TransactionListSerializer
        
        


class MoneyField(serializers.Field):
    """
    Stores USD in the DB, presents/accepts BDT to the client.
    Fixed rate for this exercise (production would inject a live rate).
    """
    USD_TO_BDT = Decimal("123")     # fixed rate, as Decimal (never float for money)

    def to_representation(self, value):
        # outbound: value is the stored USD (a Decimal). Return what the client sees (BDT).
        return value * self.USD_TO_BDT
            
        
    def to_internal_value(self, data):
        # inbound: data is what the client sent (BDT). Return what we store (USD).
        try:
            bdt = Decimal(str(data))
            
        except (InvalidOperation, TypeError):
            raise serializers.ValidationError("Amount must be a valid number.")
        
        return bdt / self.USD_TO_BDT


class MaskedCardField(serializers.Field):
    """
        Outbound: show only last 4 digits. masking it for the user/client,
        ensures security just like we do for api keys.        
    """
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value
    
    def to_representation(self, value):
        # value = stored card number (string). Return masked.
        if not value:
            return ""

        return f"{'*' * (len(value) -4)}{value[-4:]}" 
        
            
    def to_internal_value(self, data):
        # data = client-sent card number. Validate, store actual card number. (to_representation will mask).
        card = str(data)
        if not card.isdigit() or not (13 <= len(card) <= 19):
            raise serializers.ValidationError("Enter a valid card number.")
        return card

    