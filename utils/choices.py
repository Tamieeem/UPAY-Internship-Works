from django.db import models


class Currency(models.TextChoices):
    BDT = "BDT", "Bangladeshi Taka"
    USD = "USD", "US Dollar"


class AccountType(models.TextChoices):
    SAVINGS = "SAVINGS", "Savings"
    CURRENT = "CURRENT", "Current"
    WALLET  = "WALLET",  "Wallet"


class AccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    FROZEN = "FROZEN", "Frozen"
    CLOSED = "CLOSED", "Closed"


class CardType(models.TextChoices):
    VISA       = "VISA",       "Visa"
    MASTERCARD = "MASTERCARD", "Mastercard"
    AMEX       = "AMEX",       "American Express"


class CardStatus(models.TextChoices):
    ACTIVE  = "ACTIVE",  "Active"
    BLOCKED = "BLOCKED", "Blocked"
    EXPIRED = "EXPIRED", "Expired"


class TransactionType(models.TextChoices):
    TRANSFER   = "TRANSFER",   "Transfer"
    PAYMENT    = "PAYMENT",    "Payment"
    TOP_UP     = "TOP_UP",     "Top Up"
    WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
    REFUND     = "REFUND",     "Refund"


class TransactionStatus(models.TextChoices):
    PENDING   = "PENDING",   "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED    = "FAILED",    "Failed"
    REVERSED  = "REVERSED",  "Reversed"


class MerchantCategory(models.TextChoices):
    FOOD          = "FOOD",          "Food & Dining"
    TRANSPORT     = "TRANSPORT",     "Transport"
    RETAIL        = "RETAIL",        "Retail"
    UTILITIES     = "UTILITIES",     "Utilities"
    ENTERTAINMENT = "ENTERTAINMENT", "Entertainment"
    HEALTH        = "HEALTH",        "Health & Medical"
    EDUCATION     = "EDUCATION",     "Education"
    OTHER         = "OTHER",         "Other"