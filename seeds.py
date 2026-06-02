"""
seeds.py — Populate the database with realistic fintech seed data.

Run with:
    python manage.py shell < seeds.py

Or import and call seed_all() from the Django shell:
    from seeds import seed_all
    seed_all()

Wipes existing data first so it's safe to run multiple times.
"""

import os
import django
import random
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fintech_project.settings")
django.setup()

from apps.users.models import User, UserProfile
from apps.accounts.models import Account, Card
from apps.merchants.models import Merchant
from apps.transactions.models import Transaction
from utils.choices import (
    AccountStatus, AccountType,
    CardStatus, CardType,
    Currency,
    MerchantCategory,
    TransactionStatus, TransactionType,
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def wipe():
    print("Wiping existing data...")
    Transaction.objects.all().delete()
    Card.objects.all().delete()
    Account.objects.all().delete()
    Merchant.objects.all().delete()
    UserProfile.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    print("Done.\n")


def make_account_number(n):
    return f"BD{n:018d}"


# ─────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────

def seed_users():
    print("Seeding users...")

    users_data = [
        {
            "username": "arif_hossain",
            "email": "arif@example.com",
            "phone": "+8801711000001",
            "first_name": "Arif",
            "last_name": "Hossain",
            "is_varified": True,
        },
        {
            "username": "nadia_islam",
            "email": "nadia@example.com",
            "phone": "+8801711000002",
            "first_name": "Nadia",
            "last_name": "Islam",
            "is_varified": True,
        },
        {
            "username": "karim_uddin",
            "email": "karim@example.com",
            "phone": "+8801711000003",
            "first_name": "Karim",
            "last_name": "Uddin",
            "is_varified": False,
        },
        {
            "username": "sadia_rahman",
            "email": "sadia@example.com",
            "phone": "+8801711000004",
            "first_name": "Sadia",
            "last_name": "Rahman",
            "is_varified": True,
        },
        {
            "username": "tariq_hassan",
            "email": "tariq@example.com",
            "phone": "+8801711000005",
            "first_name": "Tariq",
            "last_name": "Hassan",
            "is_varified": False,
        },
    ]

    users = []
    for data in users_data:
        user = User.objects.create_user(
            password="testpass123",
            **data,
        )
        UserProfile.objects.create(
            user=user,
            city="Dhaka",
            country="Bangladesh",
            postal_code="1200",
            address=f"{random.randint(1, 99)} Gulshan Avenue, Dhaka",
        )
        users.append(user)
        print(f"  Created user: {user.username}")

    return users


# ─────────────────────────────────────────────
# MERCHANTS
# ─────────────────────────────────────────────

def seed_merchants():
    print("\nSeeding merchants...")

    merchants_data = [
        {
            "name": "Pathao",
            "merchant_code": "MCH001",
            "category": MerchantCategory.TRANSPORT,
            "country": "Bangladesh",
            "website": "https://pathao.com",
        },
        {
            "name": "Chaldal",
            "merchant_code": "MCH002",
            "category": MerchantCategory.RETAIL,
            "country": "Bangladesh",
            "website": "https://chaldal.com",
        },
        {
            "name": "Grameenphone",
            "merchant_code": "MCH003",
            "category": MerchantCategory.UTILITIES,
            "country": "Bangladesh",
            "website": "https://grameenphone.com",
        },
        {
            "name": "Shajgoj",
            "merchant_code": "MCH004",
            "category": MerchantCategory.RETAIL,
            "country": "Bangladesh",
            "website": "https://shajgoj.com",
        },
        {
            "name": "Khaas Food",
            "merchant_code": "MCH005",
            "category": MerchantCategory.FOOD,
            "country": "Bangladesh",
            "website": "https://khaasfood.com",
        },
        {
            "name": "Shohoj",
            "merchant_code": "MCH006",
            "category": MerchantCategory.TRANSPORT,
            "country": "Bangladesh",
            "website": "https://shohoj.com",
        },
        {
            "name": "10 Minute School",
            "merchant_code": "MCH007",
            "category": MerchantCategory.EDUCATION,
            "country": "Bangladesh",
            "website": "https://10minuteschool.com",
        },
        {
            "name": "Square Hospital",
            "merchant_code": "MCH008",
            "category": MerchantCategory.HEALTH,
            "country": "Bangladesh",
            "website": "https://squarehospital.com",
        },
    ]

    merchants = []
    for data in merchants_data:
        merchant = Merchant.objects.create(**data)
        merchants.append(merchant)
        print(f"  Created merchant: {merchant.name}")

    return merchants


# ─────────────────────────────────────────────
# ACCOUNTS
# ─────────────────────────────────────────────

def seed_accounts(users):
    print("\nSeeding accounts...")

    accounts = []
    counter = 1

    accounts_data = [
        # arif — 2 accounts
        (users[0], AccountType.SAVINGS, Decimal("85000.00"),  Currency.BDT, AccountStatus.ACTIVE),
        (users[0], AccountType.CURRENT, Decimal("320000.00"), Currency.BDT, AccountStatus.ACTIVE),
        # nadia — 2 accounts
        (users[1], AccountType.SAVINGS, Decimal("15000.00"),  Currency.BDT, AccountStatus.ACTIVE),
        (users[1], AccountType.WALLET,  Decimal("4500.00"),   Currency.BDT, AccountStatus.FROZEN),
        # karim — 1 account
        (users[2], AccountType.SAVINGS, Decimal("2000.00"),   Currency.BDT, AccountStatus.ACTIVE),
        # sadia — 2 accounts
        (users[3], AccountType.CURRENT, Decimal("500000.00"), Currency.BDT, AccountStatus.ACTIVE),
        (users[3], AccountType.SAVINGS, Decimal("12000.00"),  Currency.USD, AccountStatus.ACTIVE),
        # tariq — 1 account
        (users[4], AccountType.WALLET,  Decimal("750.00"),    Currency.BDT, AccountStatus.ACTIVE),
    ]

    for user, acc_type, balance, currency, status in accounts_data:
        account = Account.objects.create(
            user=user,
            account_number=make_account_number(counter),
            account_type=acc_type,
            balance=balance,
            currency=currency,
            status=status,
        )
        accounts.append(account)
        counter += 1
        print(f"  Created account: {account.account_number} ({user.username})")

    return accounts


# ─────────────────────────────────────────────
# CARDS
# ─────────────────────────────────────────────

def seed_cards(users, accounts):
    print("\nSeeding cards...")

    cards = []

    cards_data = [
        (users[0], accounts[0], "4111111111111111", CardType.VISA,       CardStatus.ACTIVE,  12, 2027),
        (users[0], accounts[1], "5500005555555559", CardType.MASTERCARD,  CardStatus.ACTIVE,  6,  2026),
        (users[1], accounts[2], "4111111111112222", CardType.VISA,       CardStatus.ACTIVE,  3,  2028),
        (users[1], accounts[3], "4111111111113333", CardType.VISA,       CardStatus.BLOCKED, 9,  2025),
        (users[3], accounts[5], "5500005555556666", CardType.MASTERCARD,  CardStatus.ACTIVE,  1,  2029),
        (users[4], accounts[7], "4111111111117777", CardType.VISA,       CardStatus.ACTIVE,  8,  2026),
    ]

    for user, account, raw_number, card_type, status, month, year in cards_data:
        card = Card(
            user=user,
            account=account,
            card_type=card_type,
            status=status,
            expiry_month=month,
            expiry_year=year,
            is_contactless=True,
        )
        card.set_card_number(raw_number)
        card.save()
        cards.append(card)
        print(f"  Created card: **** {card.last_four} ({user.username})")

    return cards


# ─────────────────────────────────────────────
# TRANSACTIONS
# ─────────────────────────────────────────────

def seed_transactions(accounts, merchants, cards):
    print("\nSeeding transactions...")

    now = timezone.now()

    def days_ago(n):
        return now - timedelta(days=n)

    arif_savings  = accounts[0]
    arif_current  = accounts[1]
    nadia_savings = accounts[2]
    nadia_wallet  = accounts[3]
    karim_savings = accounts[4]
    sadia_current = accounts[5]
    sadia_usd     = accounts[6]
    tariq_wallet  = accounts[7]

    pathao       = merchants[0]
    chaldal      = merchants[1]
    grameenphone = merchants[2]
    shajgoj      = merchants[3]
    khaas        = merchants[4]
    shohoj       = merchants[5]
    school       = merchants[6]
    hospital     = merchants[7]

    arif_visa       = cards[0]
    arif_mastercard = cards[1]
    nadia_visa      = cards[2]
    sadia_mc        = cards[4]

    txns_data = [
        # ── Completed payments (arif spending) ──
        {
            "from_account": arif_savings,
            "to_account": None,
            "merchant": pathao,
            "card": arif_visa,
            "amount": Decimal("350.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Ride to Gulshan",
            "days_ago": 2,
        },
        {
            "from_account": arif_savings,
            "to_account": None,
            "merchant": chaldal,
            "card": arif_visa,
            "amount": Decimal("2800.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Monthly groceries",
            "days_ago": 5,
        },
        {
            "from_account": arif_savings,
            "to_account": None,
            "merchant": grameenphone,
            "card": arif_visa,
            "amount": Decimal("500.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Monthly bill",
            "days_ago": 10,
        },
        {
            "from_account": arif_current,
            "to_account": None,
            "merchant": hospital,
            "card": arif_mastercard,
            "amount": Decimal("12000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Consultation fee",
            "days_ago": 15,
        },
        {
            "from_account": arif_current,
            "to_account": None,
            "merchant": school,
            "card": arif_mastercard,
            "amount": Decimal("3000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Course subscription",
            "days_ago": 20,
        },
        # ── Transfer: arif → nadia ──
        {
            "from_account": arif_savings,
            "to_account": nadia_savings,
            "merchant": None,
            "card": None,
            "amount": Decimal("5000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.TRANSFER,
            "status": TransactionStatus.COMPLETED,
            "description": "Rent contribution",
            "days_ago": 7,
        },
        # ── Transfer: arif → karim ──
        {
            "from_account": arif_current,
            "to_account": karim_savings,
            "merchant": None,
            "card": None,
            "amount": Decimal("10000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.TRANSFER,
            "status": TransactionStatus.COMPLETED,
            "description": "Loan repayment",
            "days_ago": 12,
        },
        # ── Nadia spending ──
        {
            "from_account": nadia_savings,
            "to_account": None,
            "merchant": khaas,
            "card": nadia_visa,
            "amount": Decimal("1200.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Organic groceries",
            "days_ago": 3,
        },
        {
            "from_account": nadia_savings,
            "to_account": None,
            "merchant": shajgoj,
            "card": nadia_visa,
            "amount": Decimal("3500.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Skincare products",
            "days_ago": 8,
        },
        {
            "from_account": nadia_savings,
            "to_account": None,
            "merchant": pathao,
            "card": nadia_visa,
            "amount": Decimal("180.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Ride to Dhanmondi",
            "days_ago": 1,
        },
        # ── Sadia spending (high value) ──
        {
            "from_account": sadia_current,
            "to_account": None,
            "merchant": hospital,
            "card": sadia_mc,
            "amount": Decimal("45000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Surgery deposit",
            "days_ago": 4,
        },
        {
            "from_account": sadia_current,
            "to_account": None,
            "merchant": school,
            "card": sadia_mc,
            "amount": Decimal("8000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Annual plan",
            "days_ago": 25,
        },
        {
            "from_account": sadia_current,
            "to_account": None,
            "merchant": chaldal,
            "card": sadia_mc,
            "amount": Decimal("6500.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Bulk grocery order",
            "days_ago": 18,
        },
        # ── Top-ups (external money in) ──
        {
            "from_account": None,
            "to_account": arif_savings,
            "merchant": None,
            "card": None,
            "amount": Decimal("50000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.TOP_UP,
            "status": TransactionStatus.COMPLETED,
            "description": "Salary credit",
            "days_ago": 30,
        },
        {
            "from_account": None,
            "to_account": sadia_current,
            "merchant": None,
            "card": None,
            "amount": Decimal("200000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.TOP_UP,
            "status": TransactionStatus.COMPLETED,
            "description": "Business revenue",
            "days_ago": 30,
        },
        {
            "from_account": None,
            "to_account": nadia_savings,
            "merchant": None,
            "card": None,
            "amount": Decimal("25000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.TOP_UP,
            "status": TransactionStatus.COMPLETED,
            "description": "Salary credit",
            "days_ago": 30,
        },
        # ── Pending transactions ──
        {
            "from_account": arif_savings,
            "to_account": None,
            "merchant": shohoj,
            "card": arif_visa,
            "amount": Decimal("1500.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.PENDING,
            "description": "Bus ticket booking",
            "days_ago": 0,
        },
        {
            "from_account": tariq_wallet,
            "to_account": None,
            "merchant": pathao,
            "card": None,
            "amount": Decimal("220.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.PENDING,
            "description": "Ride in progress",
            "days_ago": 0,
        },
        # ── Failed transactions ──
        {
            "from_account": nadia_savings,
            "to_account": None,
            "merchant": chaldal,
            "card": nadia_visa,
            "amount": Decimal("9500.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.FAILED,
            "description": "Insufficient balance",
            "days_ago": 6,
        },
        {
            "from_account": karim_savings,
            "to_account": None,
            "merchant": grameenphone,
            "card": None,
            "amount": Decimal("500.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.FAILED,
            "description": "Account frozen",
            "days_ago": 9,
        },
        # ── Withdrawal ──
        {
            "from_account": arif_current,
            "to_account": None,
            "merchant": None,
            "card": None,
            "amount": Decimal("20000.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.WITHDRAWAL,
            "status": TransactionStatus.COMPLETED,
            "description": "ATM withdrawal",
            "days_ago": 14,
        },
        # ── Refund ──
        {
            "from_account": None,
            "to_account": arif_savings,
            "merchant": chaldal,
            "card": None,
            "amount": Decimal("800.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.REFUND,
            "status": TransactionStatus.COMPLETED,
            "description": "Returned items refund",
            "days_ago": 4,
        },
        # ── More transport payments for aggregation variety ──
        {
            "from_account": sadia_current,
            "to_account": None,
            "merchant": pathao,
            "card": sadia_mc,
            "amount": Decimal("450.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Airport ride",
            "days_ago": 11,
        },
        {
            "from_account": arif_savings,
            "to_account": None,
            "merchant": shohoj,
            "card": arif_visa,
            "amount": Decimal("880.00"),
            "currency": Currency.BDT,
            "transaction_type": TransactionType.PAYMENT,
            "status": TransactionStatus.COMPLETED,
            "description": "Train ticket",
            "days_ago": 22,
        },
    ]

    txns = []
    for data in txns_data:
        days = data.pop("days_ago")
        created = now - timedelta(days=days)

        txn = Transaction.objects.create(**data)

        # Manually set created_at since auto_now_add ignores assignment
        Transaction.objects.filter(pk=txn.pk).update(created_at=created)
        txn.refresh_from_db()

        if txn.status == TransactionStatus.COMPLETED:
            Transaction.objects.filter(pk=txn.pk).update(completed_at=created + timedelta(minutes=2))

        txns.append(txn)
        print(f"  Created txn: {txn.get_transaction_type_display()} | {txn.amount} BDT | {txn.status}")

    return txns


# ─────────────────────────────────────────────
# REVERSAL EXAMPLE
# ─────────────────────────────────────────────

def seed_reversal(accounts, merchants):
    """
    Create one reversal transaction so we can query the
    self-referencing OneToOneField in orm_queries.py
    """
    print("\nSeeding reversal...")

    original = Transaction.objects.filter(
        transaction_type=TransactionType.PAYMENT,
        status=TransactionStatus.COMPLETED,
        from_account=accounts[0],
    ).first()

    if not original:
        print("  No original transaction found to reverse.")
        return

    reversal = Transaction.objects.create(
        from_account=None,
        to_account=original.from_account,
        merchant=original.merchant,
        amount=original.amount,
        currency=original.currency,
        transaction_type=TransactionType.REFUND,
        status=TransactionStatus.COMPLETED,
        description=f"Reversal of {original.reference_id}",
        reversal_of=original,
        completed_at=timezone.now(),
    )
    print(f"  Created reversal: {reversal} → reverses {original.reference_id}")


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────

def seed_all():
    wipe()
    users     = seed_users()
    merchants = seed_merchants()
    accounts  = seed_accounts(users)
    cards     = seed_cards(users, accounts)
    seed_transactions(accounts, merchants, cards)
    seed_reversal(accounts, merchants)
    print("\n✓ Seed complete.")
    print(f"  Users:        {User.objects.count()}")
    print(f"  Accounts:     {Account.objects.count()}")
    print(f"  Cards:        {Card.objects.count()}")
    print(f"  Merchants:    {Merchant.objects.count()}")
    print(f"  Transactions: {Transaction.objects.count()}")


if __name__ == "__main__":
    seed_all()