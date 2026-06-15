from rest_framework import serializers
from .models import Account, Transaction
from utils.choices import TransactionType
from django.db import transaction


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