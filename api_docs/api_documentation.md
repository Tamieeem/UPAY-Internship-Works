# Fintech API — Design Document

## Overview

A minimal two-model fintech API (`Account`, `Transaction`, plus a `TransactionLog` audit table) built with Django + DRF. The accounts resource is implemented in **three DRF view styles** for comparison; the canonical CRUD surface is the `ModelViewSet` + `DefaultRouter`, extended with custom state-transition actions.

- **APIView** — manual CRUD, full control over every request/response.
- **GenericAPIView + Mixins** — configured CRUD; the mixins supply the logic, we map the HTTP methods.
- **ModelViewSet** — full CRUD auto-generated from one class, wired by the router.

- **Auth:** Basic Auth (development) for testing;
- **IDs:** all primary keys are UUIDs.
- **Money:** `DecimalField(max_digits=12, decimal_places=2)`.

---

## Benefits of APIView

- Full control over every request and response; no reliance on DRF shortcuts.
- Easiest place to write unusual, endpoint-specific business logic.
- Most verbose — you hand-write the fetch / serialize / validate / save flow for each method.
- Best for endpoints that don't map cleanly to a model's CRUD (reports, webhooks, calls to external services), and for learning how DRF works internally.

## Benefits of GenericAPIView + Mixins

- Less code than APIView: list/create/retrieve/update/destroy come from built-in mixins.
- Built-in `queryset` / `serializer_class` plumbing keeps the code clean and consistent.
- You still choose which operations exist and map `get`/`post`/etc. to the mixin methods, so the wiring stays explicit.
- Heavily used at scale precisely because it's customizable (`get_queryset`, `get_serializer_class`, `perform_create`).
- Good when APIView feels too manual but you want some control over which actions are exposed.

## Benefits of ModelViewSet

- Least code: one class provides all six CRUD operations.
- Works with `DefaultRouter` to generate URLs automatically.
- The common, default choice for standard CRUD resources — the workhorse, not a rare case.
- Custom behaviour is added cleanly via `@action` methods (e.g. `freeze`, `refund`).
- Trade-off: the wiring is implicit, so you must know the router conventions.

> **Choosing between them:** pick by *how much the endpoint deviates from standard CRUD*, not by project size. Standard CRUD → ModelViewSet/Generic; bespoke logic → APIView.

---

## All Endpoints


### ACCOUNTS

#### 1. APIView (manual)

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/v1/raw/accounts/` | List all accounts |
| POST | `/api/v1/raw/accounts/` | Create new account |
| GET | `/api/v1/raw/accounts/{id}/` | Get account by id |
| PATCH | `/api/v1/raw/accounts/{id}/` | Partial update account by id |
| DELETE | `/api/v1/raw/accounts/{id}/` | Delete account by id |

#### 2. GenericAPIView + Mixins

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/v1/generic/accounts/` | List all accounts |
| POST | `/api/v1/generic/accounts/` | Create new account |
| GET | `/api/v1/generic/accounts/{id}/` | Get account by id |
| PATCH | `/api/v1/generic/accounts/{id}/` | Partial update account by id |
| DELETE | `/api/v1/generic/accounts/{id}/` | Delete account by id |

#### 3. ModelViewSet (canonical)

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/v1/accounts/` | List all accounts |
| POST | `/api/v1/accounts/` | Create new account |
| GET | `/api/v1/accounts/{id}/` | Get account by id |
| PUT | `/api/v1/accounts/{id}/` | Update account by id |
| PATCH | `/api/v1/accounts/{id}/` | Partial update account by id |
| DELETE | `/api/v1/accounts/{id}/` | Delete account by id |
| POST | `/api/v1/accounts/{id}/freeze/` | Freeze account by id |
| GET | `/api/v1/accounts/{id}/statement/` | Account statement *(planned)* |

### TRANSACTIONS

#### ModelViewSet (canonical)

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/v1/transactions/` | List all transactions |
| POST | `/api/v1/transactions/` | Create new transaction |
| GET | `/api/v1/transactions/{id}/` | Get transaction by id |
| PUT | `/api/v1/transactions/{id}/` | Update transaction by id |
| PATCH | `/api/v1/transactions/{id}/` | Partial update transaction by id |
| DELETE | `/api/v1/transactions/{id}/` | Delete transaction by id |
| POST | `/api/v1/transactions/{id}/refund/` | Refund transaction by id |

---

## Database Models

### Account Model

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Primary key, auto-generated |
| `user` | FK → auth.User | Account owner |
| `account_number` | String(20) | Unique account number |
| `balance` | Decimal(12,2) | Current balance (default `0`); read-only via API |
| `status` | String (choices) | `ACTIVE` / `FROZEN` / `CLOSED` (default `ACTIVE`); read-only via API |

### Transaction Model

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Primary key, auto-generated |
| `reference_id` | UUID | Unique idempotency key, auto-generated |
| `from_account` | FK → Account (nullable) | Source account |
| `to_account` | FK → Account (nullable) | Destination account |
| `reversal_of` | OneToOne → Transaction (nullable) | Links a refund to the original; unique → refund-once |
| `amount` | Decimal(12,2) | Transaction amount |
| `transaction_type` | String (choices) | `TRANSFER` / `PAYMENT` / `TOP_UP` / `WITHDRAWAL` / `REFUND` |
| `status` | String (choices) | `PENDING` (default) / `COMPLETED` / `FAILED` / `REFUNDED` |

### TransactionLog Model (audit)

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Primary key, auto-generated |
| `original_transaction` | FK → Transaction | The transaction this log entry concerns |
| `action` | String(20) | Event name (e.g. `REFUND`) |
| `actor` | FK → auth.User | Who triggered the event |
| `created_at` | DateTime | Timestamp (auto-generated) |

---

## Custom Actions

### Freeze Account

| Property | Value |
| --- | --- |
| Decorator | `@action(detail=True, methods=["post"])` |
| Endpoint | `POST /api/v1/accounts/{id}/freeze/` |
| Auth | Required |

**Purpose:** Transition an account to `FROZEN`. Enforces its own rule — a `CLOSED` account cannot be frozen (returns `400`). Unlike a blind `PATCH`, it only ever sets one status.

### Refund Transaction

| Property | Value |
| --- | --- |
| Decorator | `@action(detail=True, methods=["post"])` |
| Endpoint | `POST /api/v1/transactions/{id}/refund/` |
| Auth | Required |

**Purpose:** Create a compensating transaction that reverses the original (accounts swapped, `transaction_type = REFUND`, `status = COMPLETED`, linked via `reversal_of`), mark the original `REFUNDED`, and write a `TransactionLog` row — all inside one atomic DB transaction. Guards: rejects an already-`REFUNDED` transaction and any transaction that is not `COMPLETED` (both `400`).

### Account Statement *(planned)*

| Property | Value |
| --- | --- |
| Decorator | `@action(detail=True, methods=["get"])` |
| Endpoint | `GET /api/v1/accounts/{id}/statement/` |
| Auth | Required |

**Purpose:** Return every transaction touching this account, on either side (`from_account` **or** `to_account`).

---

## Status Codes

| Code | Meaning |
| --- | --- |
| `200` | Successful GET / PUT / PATCH / freeze |
| `201` | Resource created (POST create, refund) |
| `204` | Successful DELETE (no body) |
| `400` | Validation error or rejected state transition |
| `401` | Missing / invalid authentication |
| `404` | Not found, or object outside the user's scope |

---

## Notes (pending work)

- `statement` action not yet implemented.
- `get_queryset` (per-user scoping) and `get_serializer_class` (list vs detail serializers) not yet added.