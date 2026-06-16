from rest_framework import serializers
from .models import Account, Transaction
from utils.choices import TransactionType, AccountStatus
from decimal import Decimal
from django.db.models import Q


class AccountStatsSerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()
    balance_in_taka   = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ["id", "account_number", "balance", "balance_in_taka", "transaction_count"]

    def get_transaction_count(self, obj):
        #transaction count
        return Transaction.objects.filter(
            Q(from_account=obj) | Q(to_account=obj)
        ).count()

    def get_balance_in_taka(self, obj):
        # derives taka from stored USD balance in db.
        USD_TO_BDT = Decimal("123")
        taka = obj.balance * USD_TO_BDT
        
        return taka
    
    def get_last_active(self, obj):
        #account owner can see the last activity(transaction- received or sent).
        latest = (
            Transaction.objects.filter(
                Q(from_account=obj) | Q(to_account=obj).
                order_by("-created_at").
                first()
            )
        )
        return latest.created_at if latest else None
    
    def to_representation(self, instance):
        
        data = super().to_representation(instance)
        data["summary"] = f"{instance.account_number} is {instance.status}"
        return data