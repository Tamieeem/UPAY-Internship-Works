import uuid

from django.db import models

from utils.choices import MerchantCategory
from utils.timestamped import TimeStampedModel
# from .managers import MerchantManager


class Merchant(TimeStampedModel):
    """
    An entity that receives payments — e.g. Pathao, Chaldal, Grameenphone.

    Merchants are independent of users and accounts. They are referenced
    by transactions to record where money was sent during a payment.

    merchant_code acts like a real-world MCC (Merchant Category Code) —
    a unique identifier assigned to each merchant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)
    merchant_code = models.CharField(max_length=50, unique=True)
    category = models.CharField(
        max_length=20,
        choices=MerchantCategory.choices,
        default=MerchantCategory.OTHER,
    )
    country   = models.CharField(max_length=100, default="Bangladesh")
    is_active = models.BooleanField(default=True, db_index=True)
    website   = models.URLField(blank=True)

    # objects = MerchantManager()

    class Meta:
        db_table = "merchants"
        indexes = [
            models.Index(fields=["category"],      name="idx_merchant_category"),
            models.Index(fields=["merchant_code"], name="idx_merchant_code"),
            models.Index(fields=["country"],       name="idx_merchant_country"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"