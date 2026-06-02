import hashlib
import uuid

from django.db import models
from django.db.models import Q
from utils.choices import (
    AccountStatus,
    AccountType,
    CardStatus,
    CardType,
    Currency,
)
from utils.timestamped import TimeStampedModel
# from .managers import AccountManager, CardManager


class Account(TimeStampedModel):
    """
    A financial account owned by a User.
    One user can hold multiple accounts across different types and currencies.

    balance uses DecimalField — never FloatField for money.
    FloatField uses IEEE 754 binary floating point which introduces
    rounding errors. DecimalField stores exact decimal values.

    on_delete=PROTECT on the user FK means Django will raise a ProtectedError
    if you try to delete a user who still has accounts. Prevents accidental
    data loss — you must close accounts before deleting a user.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    account_number = models.CharField(max_length=20, unique=True)
    account_type   = models.CharField(
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.SAVINGS,
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.BDT,
    )
    status = models.CharField(
        max_length=10,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )

    # objects = AccountManager()

    class Meta:
        db_table = "accounts"
        indexes = [
            # Composite: most common query is "active accounts for this user"
            models.Index(fields=["user", "status"],   name="idx_account_user_status"),
            models.Index(fields=["currency"],          name="idx_account_currency"),
            models.Index(fields=["account_number"],    name="idx_account_number"),
        ]
        constraints = [
            # Enforced at the DB level — application bugs cannot cause
            # negative balances to persist, even if service logic fails.
            models.CheckConstraint(condition=Q(balance__gte=0),
                name="chk_account_balance_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.account_number} ({self.get_account_type_display()}) — {self.user}"

    @property
    def is_active(self):
        return self.status == AccountStatus.ACTIVE

    def can_debit(self, amount):
        """
        Read-only check — does this account have enough balance
        and is it in an operable state?

        This is a model-level helper (pure read, no DB write).
        The actual debit logic lives in AccountService.
        """
        return self.is_active and self.balance >= amount


class Card(TimeStampedModel):
    """
    A payment card linked to a specific Account.
    One user can hold multiple cards across different accounts.

    Raw card numbers are never stored — only a SHA-256 hash
    and the last four digits for display. This follows PCI-DSS guidelines.

    Both user and account use PROTECT to prevent orphaned cards
    from dangling after a delete.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user    = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="cards",
    )
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="cards",
    )

    card_number_hash = models.CharField(max_length=64)  # SHA-256 hex digest
    last_four        = models.CharField(max_length=4)
    card_type        = models.CharField(
        max_length=10,
        choices=CardType.choices,
        default=CardType.VISA,
    )
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year  = models.PositiveSmallIntegerField()
    status       = models.CharField(
        max_length=10,
        choices=CardStatus.choices,
        default=CardStatus.ACTIVE,
    )
    is_contactless = models.BooleanField(default=True)

    # objects = CardManager()

    class Meta:
        db_table = "cards"
        indexes = [
            models.Index(fields=["user", "status"],    name="idx_card_user_status"),
            models.Index(fields=["account"],           name="idx_card_account"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expiry_month__gte=1) & Q(expiry_month__lte=12),
                name="chk_card_expiry_month_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(expiry_year__gte=2024),
                name="chk_card_expiry_year_valid",
            ),
        ]

    def __str__(self):
        return f"**** **** **** {self.last_four} ({self.get_card_type_display()})"

    @property
    def is_active(self):
        return self.status == CardStatus.ACTIVE

    def set_card_number(self, raw_number: str):
        """
        Hashes and stores the card number.
        will be called during card creation.
        no raw card number storing.
        Example:
            card = Card(user=user, account=account, ...)
            card.set_card_number("4111111111111111")
            card.save()
        """
        if not raw_number.isdigit() or len(raw_number) not in (15, 16):
            raise ValueError("Card number must be 15 or 16 digits.")
        self.card_number_hash = hashlib.sha256(raw_number.encode()).hexdigest()
        self.last_four = raw_number[-4:]