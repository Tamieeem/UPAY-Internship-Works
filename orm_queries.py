"""
orm_queries.py — 15 ORM queries of increasing complexity.
each query here solves a realistic fintech problem and is followed
by an explanation of what ORM concept it demonstrates.
"""

from decimal import Decimal

from django.db import models
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import TruncMonth, TruncDate, Coalesce
from django.utils import timezone

from apps.accounts.models import Account, Card
from apps.merchants.models import Merchant
from apps.transactions.models import Transaction
from apps.users.models import User
from utils.choices import (
    AccountStatus,
    MerchantCategory,
    TransactionStatus,
    TransactionType,
)


# Q01 — Basic filter + exclude + ordering
# Concept: filter(), exclude(), order_by(), values()
#
# Problem: Get all completed transactions above 1000 BDT,
# excluding refunds, ordered by amount descending.
# Return only the fields we need — not the whole object.

def q01_basic_filter():
    results = (
        Transaction.objects
        .filter(
            status=TransactionStatus.COMPLETED,
            amount__gt=Decimal("1000.00"),
            currency="BDT",
        )
        .exclude(transaction_type=TransactionType.REFUND)
        .order_by("-amount")
        .values(
            "reference_id",
            "amount",
            "transaction_type",
            "created_at",
        )
    )

    print("Q01 — Completed BDT transactions > 1000, excluding refunds:")
    for r in results:
        print(f"  {r['transaction_type']:<12} {r['amount']} BDT  {r['created_at'].date()}")

    return results


# Q02 — F() expressions: comparing two fields
# Concept: F() lets you reference a model field in a query
# without pulling the value into Python. The comparison
# happens entirely in SQL.
#
# Problem: Find accounts where the balance is above
# a threshold, and use F() to apply a percentage increase
# in an annotation — without fetching balance into Python.
#
# Real use: applying interest rates, fee calculations,
# threshold checks — all in one DB round trip.

def q02_f_expressions():
    # F() reference: annotate each account with what its
    # balance would be after a 2% monthly interest credit.
    results = (
        Account.objects
        .filter(status=AccountStatus.ACTIVE)
        .annotate(
            balance_after_interest=F("balance") * Decimal("1.02"),
            interest_earned=F("balance") * Decimal("0.02"),
        )
        .filter(balance__gt=Decimal("10000.00"))  # only meaningful balances
        .order_by("-balance")
        .values("account_number", "balance", "balance_after_interest", "interest_earned")
    )

    print("Q02 — Active accounts > 10k with 2% interest projection:")
    for r in results:
        print(
            f"  {r['account_number']}  "
            f"Current: {r['balance']}  "
            f"After interest: {r['balance_after_interest']:.2f}  "
            f"Earned: {r['interest_earned']:.2f}"
        )

    return results


# Q03 — Q() objects: complex lookups with OR / AND / NOT
# Concept: Q() lets you combine filter conditions with
# OR (|), AND (&), and NOT (~) operators.
# Regular .filter() chaining only does AND.
#
# Problem: Find transactions that are either:
#   - Pending (regardless of amount), OR
#   - Failed with amount > 500 BDT
# These are the transactions that need attention.

def q03_q_objects():
    results = (
        Transaction.objects
        .filter(
            Q(status=TransactionStatus.PENDING)
            | (
                Q(status=TransactionStatus.FAILED)
                & Q(amount__gt=Decimal("500.00"))
            )
        )
        .select_related("from_account__user", "merchant")
        .order_by("status", "-amount")
    )

    print("Q03 — Transactions needing attention (pending OR high-value failed):")
    for t in results:
        user = t.from_account.user.username if t.from_account else "external"
        merchant = t.merchant.name if t.merchant else "—"
        print(f"  [{t.status}] {user:<15} {t.amount} BDT  merchant: {merchant}")

    return results


# Q04 — Aggregations: Sum, Count, Avg, Min, Max
# Concept: aggregate() returns a single dict of computed
# values across the entire queryset — one SQL query.
#
# Problem: Produce a summary report of all completed
# transactions — total volume, count, average, min, max.
# This is the kind of query that powers a finance dashboard.

def q04_aggregate():
    summary = Transaction.objects.filter(
        status=TransactionStatus.COMPLETED
    ).aggregate(
        total_volume=Sum("amount"),
        total_count=Count("id"),
        average_amount=Avg("amount"),
        smallest=Min("amount"),
        largest=Max("amount"),
    )

    print("Q04 — Completed transaction summary:")
    print(f"  Total volume:  {summary['total_volume']} BDT")
    print(f"  Total count:   {summary['total_count']}")
    print(f"  Average:       {summary['average_amount']:.2f} BDT")
    print(f"  Smallest:      {summary['smallest']} BDT")
    print(f"  Largest:       {summary['largest']} BDT")

    return summary


# Q05 — annotate() + values(): GROUP BY
# Concept: annotate() adds a computed column per row.
# When combined with values(), Django groups by those
# fields and aggregates — equivalent to SQL GROUP BY.
#
# Problem: For each merchant category, find the total
# spend and number of transactions. Powers a "spending
# by category" breakdown on a user dashboard.

def q05_annotate_group_by():
    results = (
        Transaction.objects
        .filter(
            status=TransactionStatus.COMPLETED,
            merchant__isnull=False,
        )
        .values("merchant__category")           # GROUP BY category
        .annotate(
            total_spent=Sum("amount"),
            txn_count=Count("id"),
            avg_txn=Avg("amount"),
        )
        .order_by("-total_spent")
    )

    print("Q05 — Spending breakdown by merchant category:")
    for r in results:
        print(
            f"  {r['merchant__category']:<15} "
            f"Total: {r['total_spent']:>10.2f} BDT  "
            f"Count: {r['txn_count']}  "
            f"Avg: {r['avg_txn']:.2f}"
        )

    return results


# Q06 — select_related(): eliminate N+1 on FK lookups
# Concept: select_related() performs a SQL JOIN and caches
# the related object. Without it, accessing t.from_account.user
# inside a loop fires one extra query per transaction — N+1.
#
# Problem: List recent transactions with their sender's
# username and account number. Without select_related,
# a loop over 20 transactions = 40+ queries.
# With select_related, it's 1 query.

def q06_select_related():
    # One SQL query with JOINs across transaction → account → user
    results = (
        Transaction.objects
        .filter(status=TransactionStatus.COMPLETED)
        .select_related(
            "from_account",           # JOIN accounts
            "from_account__user",     # JOIN users (through accounts)
            "to_account",
            "merchant",
        )
        .order_by("-created_at")[:10]
    )

    print("Q06 — Recent completed transactions (select_related, 1 query):")
    for t in results:
        sender   = t.from_account.user.username if t.from_account else "external"
        acc_no   = t.from_account.account_number if t.from_account else "—"
        merchant = t.merchant.name if t.merchant else "—"
        print(f"  {sender:<15} {acc_no}  {t.amount:>10.2f} BDT  → {merchant}")

    return results


# Q07 — prefetch_related(): reverse FK and M2M
# Concept: prefetch_related() handles reverse FK and M2M
# relations. Unlike select_related (JOIN), it runs a
# separate query per relation and joins in Python.
# Use it when you'd get duplicate rows with a JOIN
# (one-to-many from the "one" side).
#
# Problem: For each user, list all their accounts and
# the number of transactions on each account.
# select_related can't do reverse FKs — prefetch can.

def q07_prefetch_related():
    users = (
        User.objects
        .filter(is_verified=True)
        .prefetch_related(
            models.Prefetch(
                "accounts",
                queryset=Account.objects.filter(
                    status=AccountStatus.ACTIVE
                ).annotate(
                    txn_count=Count("outgoing_transactions"),
                ),
            )
        )
    )

    print("Q07 — Verified users with their active accounts (prefetch_related):")
    for user in users:
        print(f"  {user.username}:")
        for account in user.accounts.all():
            print(
                f"    {account.account_number}  "
                f"{account.balance:>10.2f} {account.currency}  "
                f"outgoing txns: {account.txn_count}"
            )

    return users


# Q08 — Subquery(): correlated subquery
# Concept: Subquery() lets you embed one queryset inside
# another — the inner query references the outer via
# OuterRef(). Runs as a correlated subquery in SQL.
#
# Problem: For each account, show the amount of its
# most recent completed transaction. You can't do this
# with a simple JOIN — you need a subquery per account.

def q08_subquery():
    # Inner query: for a given account (OuterRef("pk")),
    # get the amount of the latest completed outgoing transaction.
    latest_txn_amount = (
        Transaction.objects
        .filter(
            from_account=OuterRef("pk"),       # references outer Account.pk
            status=TransactionStatus.COMPLETED,
        )
        .order_by("-created_at")
        .values("amount")[:1]                  # LIMIT 1
    )

    results = (
        Account.objects
        .filter(status=AccountStatus.ACTIVE)
        .annotate(
            last_txn_amount=Subquery(
                latest_txn_amount,
                output_field=DecimalField(),
            )
        )
        .filter(last_txn_amount__isnull=False)  # only accounts with transactions
        .select_related("user")
        .order_by("-last_txn_amount")
    )

    print("Q08 — Accounts with their latest completed transaction amount (Subquery):")
    for acc in results:
        print(
            f"  {acc.user.username:<15} "
            f"{acc.account_number}  "
            f"Last txn: {acc.last_txn_amount} BDT"
        )

    return results


# Q09 — Exists(): boolean subquery check
# Concept: Exists() is more efficient than Count() > 0
# because the DB stops scanning as soon as it finds
# one matching row. Use it for "has at least one" checks.
#
# Problem: Find all users who have at least one failed
# transaction. Flag them for a fraud review workflow.
def q09_exists():
    has_failed_txn = Transaction.objects.filter(
        from_account__user=OuterRef("pk"),
        status=TransactionStatus.FAILED,
    )

    results = (
        User.objects
        .annotate(has_failure=Exists(has_failed_txn))
        .filter(has_failure=True)
        .values("username", "email", "phone_number", "has_failure")
    )

    print("Q09 — Users with at least one failed transaction (Exists):")
    for r in results:
        print(f"  {r['username']:<15} {r['email']}")

    return results


# Q10 — Case / When: conditional expressions
# Concept: Case/When is SQL's CASE WHEN ... THEN ... END.
# Use it to compute derived values or labels per row
# based on conditions — without fetching data into Python.
#
# Problem: Classify each account by balance tier.
# This powers a UI badge or risk scoring system.

def q10_case_when():
    results = (
        Account.objects
        .filter(status=AccountStatus.ACTIVE)
        .annotate(
            balance_tier=Case(
                When(balance__gte=Decimal("100000.00"), then=Value("PREMIUM")),
                When(balance__gte=Decimal("20000.00"),  then=Value("STANDARD")),
                When(balance__gte=Decimal("5000.00"),   then=Value("BASIC")),
                default=Value("LOW"),
                output_field=models.CharField(),
            )
        )
        .select_related("user")
        .order_by("-balance")
        .values("account_number", "balance", "balance_tier", "user__username")
    )

    print("Q10 — Accounts with balance tier classification (Case/When):")
    for r in results:
        print(
            f"  {r['user__username']:<15} "
            f"{r['account_number']}  "
            f"{r['balance']:>10.2f} BDT  "
            f"[{r['balance_tier']}]"
        )

    return results


# Q11 — TruncMonth + annotate(): time series aggregation
# Concept: TruncDate / TruncMonth truncates a datetime
# to the month boundary, allowing you to group by month.
# This is how every "monthly spending" chart is built.
#
# Problem: Show total transaction volume per month
# for the last 60 days — the data behind a trend chart.


def q11_time_series():
    since = timezone.now() - __import__("datetime").timedelta(days=60)

    results = (
        Transaction.objects
        .filter(
            status=TransactionStatus.COMPLETED,
            created_at__gte=since,
        )
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total_volume=Sum("amount"),
            txn_count=Count("id"),
        )
        .order_by("month")
    )

    print("Q11 — Monthly transaction volume (time series):")
    for r in results:
        print(
            f"  {r['month'].strftime('%Y-%m')}  "
            f"Volume: {r['total_volume']:>12.2f} BDT  "
            f"Count: {r['txn_count']}"
        )

    return results


# Q12 — Coalesce(): handle NULL in aggregations
# Concept: Coalesce() returns the first non-NULL value
# from a list. Critical in aggregations — Sum() of an
# empty queryset returns None, not 0. Coalesce fixes that.
#
# Problem: For each user, show total money sent and
# total money received. Users with no transactions should
# show 0, not None — safe for arithmetic downstream.

def q12_coalesce():
    results = (
        User.objects
        .annotate(
            total_sent=Coalesce(
                Sum(
                    "accounts__outgoing_transactions__amount",
                    filter=Q(
                        accounts__outgoing_transactions__status=TransactionStatus.COMPLETED
                    ),
                ),
                Decimal("0"),
                output_field=DecimalField(),
            ),
            total_received=Coalesce(
                Sum(
                    "accounts__incoming_transactions__amount",
                    filter=Q(
                        accounts__incoming_transactions__status=TransactionStatus.COMPLETED
                    ),
                ),
                Decimal("0"),
                output_field=DecimalField(),
            ),
        )
        .values("username", "total_sent", "total_received")
        .order_by("-total_sent")
    )

    print("Q12 — Per-user total sent and received (Coalesce for NULL safety):")
    for r in results:
        net = r["total_received"] - r["total_sent"]
        print(
            f"  {r['username']:<15} "
            f"Sent: {r['total_sent']:>10.2f}  "
            f"Received: {r['total_received']:>10.2f}  "
            f"Net: {net:>10.2f}"
        )

    return results


# Q13 — Subquery with annotate(): per-row derived data
# Concept: Combine Subquery + OuterRef with annotate()
# to attach a per-row derived value from another table.
# More flexible than joins when you need "latest" or
# "first" related records.
#
# Problem: For each merchant, show the date of their
# most recent transaction. Used to find inactive merchants
# (no transaction in the last 30 days).

def q13_subquery_annotate():
    from django.db.models import DateTimeField

    last_txn_date = (
        Transaction.objects
        .filter(
            merchant=OuterRef("pk"),
            status=TransactionStatus.COMPLETED,
        )
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    results = (
        Merchant.objects
        .filter(is_active=True)
        .annotate(
            last_transaction_at=Subquery(
                last_txn_date,
                output_field=DateTimeField(),
            ),
            total_revenue=Coalesce(
                Sum(
                    "transactions__amount",
                    filter=Q(transactions__status=TransactionStatus.COMPLETED),
                ),
                Decimal("0"),
                output_field=DecimalField(),
            ),
        )
        .order_by("-total_revenue")
        .values("name", "category", "last_transaction_at", "total_revenue")
    )

    print("Q13 — Merchants with last transaction date and total revenue:")
    for r in results:
        last = r["last_transaction_at"].date() if r["last_transaction_at"] else "never"
        print(
            f"  {r['name']:<20} "
            f"{r['category']:<15} "
            f"Revenue: {r['total_revenue']:>10.2f} BDT  "
            f"Last txn: {last}"
        )

    return results


# Q14 — Multi-level annotation + conditional aggregate
# Concept: You can pass a filter= argument to aggregation
# functions (Sum, Count, Avg) to aggregate conditionally
# within the same query. This avoids multiple queries
# or Python-side filtering.
#
# Problem: For each user, compute in one query:
#   - Total completed transaction amount
#   - Total failed transaction amount
#   - Number of pending transactions
#   - Their largest single transaction
# A full risk/activity profile in one DB round trip.

def q14_conditional_aggregate():
    results = (
        User.objects
        .annotate(
            completed_volume=Coalesce(
                Sum(
                    "accounts__outgoing_transactions__amount",
                    filter=Q(
                        accounts__outgoing_transactions__status=TransactionStatus.COMPLETED
                    ),
                ),
                Decimal("0"),
                output_field=DecimalField(),
            ),
            failed_volume=Coalesce(
                Sum(
                    "accounts__outgoing_transactions__amount",
                    filter=Q(
                        accounts__outgoing_transactions__status=TransactionStatus.FAILED
                    ),
                ),
                Decimal("0"),
                output_field=DecimalField(),
            ),
            pending_count=Count(
                "accounts__outgoing_transactions",
                filter=Q(
                    accounts__outgoing_transactions__status=TransactionStatus.PENDING
                ),
            ),
            largest_txn=Max("accounts__outgoing_transactions__amount"),
        )
        .values(
            "username",
            "completed_volume",
            "failed_volume",
            "pending_count",
            "largest_txn",
        )
        .order_by("-completed_volume")
    )

    print("Q14 — Full user transaction profile (conditional aggregates):")
    for r in results:
        print(
            f"  {r['username']:<15} "
            f"Completed: {str(r['completed_volume'] or 0):>10}  "
            f"Failed: {str(r['failed_volume'] or 0):>8}  "
            f"Pending: {r['pending_count']}  "
            f"Largest: {r['largest_txn'] or 0}"
        )

    return results


# Q15 — Combined: Subquery + Case/When + prefetch
# Concept: Real production queries combine multiple
# ORM features. This query builds an account statement
# summary — the kind of data that powers a mobile
# banking home screen.
#
# Problem: For each active account of verified users:
#   - Attach owner's full name
#   - Classify the account by balance tier (Case/When)
#   - Attach the amount of the last transaction (Subquery)
#   - Classify activity level based on transaction count
#   - Prefetch last 5 transactions for display

def q15_combined():
    from django.db.models.functions import Concat
    from django.db.models import CharField

    last_txn = (
        Transaction.objects
        .filter(
            Q(from_account=OuterRef("pk")) | Q(to_account=OuterRef("pk"))
        )
        .order_by("-created_at")
        .values("amount")[:1]
    )

    recent_txns_prefetch = models.Prefetch(
        "outgoing_transactions",
        queryset=Transaction.objects
            .filter(status=TransactionStatus.COMPLETED)
            .select_related("merchant")
            .order_by("-created_at")[:5],
        to_attr="recent_txns",
    )

    accounts = (
        Account.objects
        .filter(
            status=AccountStatus.ACTIVE,
            user__is_varified=True,
        )
        .select_related("user")
        .prefetch_related(recent_txns_prefetch)
        .annotate(
            owner_name=Concat(
                "user__first_name",
                Value(" "),
                "user__last_name",
                output_field=CharField(),
            ),
            balance_tier=Case(
                When(balance__gte=Decimal("100000.00"), then=Value("PREMIUM")),
                When(balance__gte=Decimal("20000.00"),  then=Value("STANDARD")),
                When(balance__gte=Decimal("5000.00"),   then=Value("BASIC")),
                default=Value("LOW"),
                output_field=models.CharField(),
            ),
            last_txn_amount=Subquery(
                last_txn,
                output_field=DecimalField(),
            ),
            outgoing_count=Count(
                "outgoing_transactions",
                filter=Q(outgoing_transactions__status=TransactionStatus.COMPLETED),
            ),
            activity_level=Case(
                When(outgoing_count__gte=10, then=Value("HIGH")),
                When(outgoing_count__gte=5,  then=Value("MEDIUM")),
                When(outgoing_count__gte=1,  then=Value("LOW")),
                default=Value("INACTIVE"),
                output_field=models.CharField(),
            ),
        )
        .order_by("-balance")
    )

    print("Q15 — Full account dashboard summary (combined ORM features):")
    for acc in accounts:
        print(
            f"\n  {acc.owner_name} | {acc.account_number}"
            f"\n    Balance:   {acc.balance:>10.2f} {acc.currency}  [{acc.balance_tier}]"
            f"\n    Activity:  {acc.activity_level} ({acc.outgoing_count} completed txns)"
            f"\n    Last txn:  {acc.last_txn_amount or 'none'}"
        )
        if hasattr(acc, "recent_txns") and acc.recent_txns:
            print("    Recent:")
            for t in acc.recent_txns:
                merchant = t.merchant.name if t.merchant else "transfer"
                print(f"      {t.created_at.date()}  {t.amount:>8.2f} BDT  → {merchant}")

    return accounts


# script for run all together
def run_all():
    queries = [
        ("Q01 — Basic filter + exclude + ordering",     q01_basic_filter),
        ("Q02 — F() field expressions",                 q02_f_expressions),
        ("Q03 — Q() objects: OR / AND / NOT",           q03_q_objects),
        ("Q04 — Aggregate: Sum, Count, Avg, Min, Max",  q04_aggregate),
        ("Q05 — annotate() + values(): GROUP BY",       q05_annotate_group_by),
        ("Q06 — select_related(): eliminate N+1",       q06_select_related),
        ("Q07 — prefetch_related(): reverse FK",        q07_prefetch_related),
        ("Q08 — Subquery() + OuterRef()",               q08_subquery),
        ("Q09 — Exists(): boolean subquery",            q09_exists),
        ("Q10 — Case / When: conditional expressions",  q10_case_when),
        ("Q11 — TruncMonth: time series aggregation",   q11_time_series),
        ("Q12 — Coalesce(): NULL safety",               q12_coalesce),
        ("Q13 — Subquery + annotate(): per-row data",   q13_subquery_annotate),
        ("Q14 — Conditional aggregates (filter=)",      q14_conditional_aggregate),
        ("Q15 — Combined: full account dashboard",      q15_combined),
    ]

    for label, fn in queries:
        print(f"\n{'─' * 60}")
        print(f"{label}")
        print('─' * 60)
        try:
            fn()
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n{'─' * 60}")
    print("All queries complete.")


if __name__ == "__main__":
    import os
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    run_all()