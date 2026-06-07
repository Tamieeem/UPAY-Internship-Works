from django.conf import settings
from django.db import models
from utils.choices import AccountStatus, TransactionStatus, TransactionType
import uuid


class Account(models.Model):
    '''using django's built in User model to keep it simple
    for the given task as using only two models for this task.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    status = models.CharField(max_length=10, 
        choices=AccountStatus.choices, 
        default=AccountStatus.ACTIVE
    )
    
    def __str__(self):
        return f"{self.account_number} — {self.user}"


class Transaction(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    reference_id = models.UUIDField(
        unique=True,default=uuid.uuid4, db_index=True)
    
    from_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="outgoing_transactions",
        null=True,
        blank=True,
    )
    to_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="incoming_transactions",
        null=True,
        blank=True,
    )
    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_by",
    )

    amount   = models.DecimalField(
        max_digits=12, decimal_places=2)
    transaction_type = models.CharField(
        max_length=15,
        choices=TransactionType.choices,
    )
    status = models.CharField(  
        max_length=10,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )

    def __str__(self):
        return (
            f"[{self.status}] {self.get_transaction_type_display()} | "
            f"{self.amount} | ref: {self.reference_id}"
        )
