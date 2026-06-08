from .models import Account, Transaction
from rest_framework import serializers

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
            # 'user',
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