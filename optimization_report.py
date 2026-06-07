"""
What this script does:
    Runs the same data fetch two ways — naive and optimized.
    Measures how many SQL queries fired and how long they took.
    Prints a clear before/after report for each pattern.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fintech_project.settings")
django.setup()

from django.db import connection, reset_queries
from django.db.models import Count, Prefetch, Q, Sum
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import Account
from apps.transactions.models import Transaction
from apps.users.models import User
from utils.choices import AccountStatus, TransactionStatus


# ─────────────────────────────────────────────
# HELPER: measure a block of code
# ─────────────────────────────────────────────

class measure:
    """
    Context manager that captures every SQL query fired
    inside the `with` block.

    Usage:
        with measure() as m:
            list(Transaction.objects.filter(...))
        m.report()
        
        CaptureQueriesContext wraps Django's database connection.
        every SQL statement sent during the block is recorded
        in ctx.captured_queries — a list of {sql, time} dicts.
    """

    def __init__(self, label):
        self.label = label
        self._ctx = CaptureQueriesContext(connection)

    def __enter__(self):
        self._ctx.__enter__()
        return self

    def __exit__(self, *args):
        self._ctx.__exit__(*args)
        self.queries = self._ctx.captured_queries
        self.count = len(self.queries)
        self.total_time = sum(float(q["time"]) for q in self.queries)

    def report(self):
        print(f"    Queries fired : {self.count}")
        print(f"    Total time    : {self.total_time * 1000:.2f}ms")

    def sql(self, max_chars=120):
        """this will print each SQL query"""
        for i, q in enumerate(self.queries, 1):
            sql_preview = q["sql"].replace("\n", " ")[:max_chars]
            print(f"    [{i:02d}] {float(q['time'])*1000:.2f}ms  {sql_preview}...")


#divider
def section(title):
    print(f"\n{'═' * 65}")
    print(f"  {title}")
    print(f"{'═' * 65}")
    
def subsection(title):
    print(f"\n  ── {title}")

# fixing N+1 via select_related
# problem:
#   When you access a ForeignKey field on a model instance
#   like transaction.from_account, Django fires a new SQL
#   query to fetch that related object unless we explicitly call it
#   to fetch it upfront.
#
#   If we loop over 10 transactions and access from_account
#   on each, that's 10 extra queries. access from_account.user
#   on each and it's 20 extra queries. so total N+1 queries.
#
# to solve it we can use the approach: select_related()
#   this tells Django to JOIN the related tables in the original
#   query. All related objects arrive together in one round
#   trip. subsequent attribute access hits Python memory,
#   not the database.

def _print_comparison(before, after):
    query_reduction = before.count - after.count
    if after.total_time > 0:
        speedup_str = f"{before.total_time / after.total_time:>6.1f}x faster"
    else:
        speedup_str = "  ~cached"

    print(f"""
    ┌─────────────────────────────────────────┐
    │              RESULT                     │
    ├──────────────┬──────────────────────────┤
    │              │  Queries   │  Time       │
    ├──────────────┼────────────┼─────────────┤
    │  Before      │  {before.count:<10} │  {before.total_time*1000:>7.2f}ms   │
    │  After       │  {after.count:<10} │  {after.total_time*1000:>7.2f}ms   │
    │  Saved       │  {query_reduction:<10} │  {speedup_str:<19} │
    └──────────────┴────────────┴─────────────┘""")


def ONEtoONE_SELECT_RELATED():
    section("N+1 Problem: select_related")

    # ── BEFORE ──────────────────────────────
    subsection("BEFORE — naive fetch, no select_related")
    print("""
    Code:
        txns = list(Transaction.objects.filter(status="COMPLETED")[:10])
        for t in txns:
            _ = t.from_account          # query fires here
            if t.from_account:
                _ = t.from_account.user # query fires again here
            _ = t.merchant              # and again
    """)

    with measure("naive") as before:
        txns = list(
            Transaction.objects
            .filter(status=TransactionStatus.COMPLETED)
            [:10]
        )
        # Accessing FK attributes inside a loop — each fires a new query
        for t in txns:
            _ = t.from_account
            if t.from_account:
                _ = t.from_account.user
            _ = t.merchant

    before.report()
    print()
    before.sql()

    # ── AFTER ───────────────────────────────
    subsection("AFTER — select_related prefetches FK joins")
    print("""
    Code:
        txns = list(
            Transaction.objects
            .filter(status="COMPLETED")
            .select_related(
                "from_account",
                "from_account__user",
                "merchant",
            )[:10]
        )
        for t in txns:
            _ = t.from_account          # served from Python memory
            _ = t.from_account.user     # served from Python memory
            _ = t.merchant              # served from Python memory
    """)

    with measure("optimized") as after:
        txns = list(
            Transaction.objects
            .filter(status=TransactionStatus.COMPLETED)
            .select_related(
                "from_account",
                "from_account__user",
                "merchant",
            )
            [:10]
        )
        for t in txns:
            _ = t.from_account
            if t.from_account:
                _ = t.from_account.user
            _ = t.merchant

    after.report()
    print()
    after.sql()

    # ── SUMMARY ─────────────────────────────
    _print_comparison(before, after)
    print("""
    Why:
        Without select_related, Django fetches each FK lazily —
        one query per attribute access. With select_related, Django
        generates a single SQL query with LEFT OUTER JOINs, bringing
        all related rows back at once. Attribute access in Python
        then reads from the already-loaded cache, not the database.
    """)



#run report()
def run_report():
    print("\n" + "█" * 65)
    print("  DJANGO ORM QUERY OPTIMIZATION REPORT")
    print("█" * 65)
    print(f"\n  Database : {connection.vendor}")
    print(f"  Django   : {django.get_version()}")

    ONEtoONE_SELECT_RELATED()

    print(f"\n{'═' * 65}")
    print("  REPORT COMPLETE")
    print(f"{'═' * 65}\n")


run_report()

if __name__ == "__main__":
    run_report()