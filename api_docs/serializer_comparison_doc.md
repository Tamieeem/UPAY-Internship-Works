# Serializers — when to use what

Notes from building the serializer module. Quick reference for which serializer/field type to reach for.

## Serializer vs ModelSerializer

We use **ModelSerializer** for anything that maps to a model. It reads the model and builds the fields and does the create/update for us automatically.

We use plain **Serializer** when the data is not related to a model. Like when a user creates account we don't save form, or when we send OTP, it isn't saved, instead it is one time thing. So we use serializer for these cases. Here in the project, the TransactionRequestSerializer() is just validating the payload data, not saving/directing to db model.

## ListSerializer

This is the one that handles MANY objects, not a list of fields. DRF automatically does this under the hood when we write many = True. This is used multiple request body validation at once, like a list of requests.
Like the BulkTransactionSerializer() in this project. 

## Nested vs flat

The deciding question: is the related object being CREATED right now, or just REFERENCED?

- Already exists, just point at it -> flat (PrimaryKeyRelatedField / UUID). This is the normal case. A transfer references two existing accounts, so transfers should be flat.
- Created together as one unit -> nested write (serializer as a field + override create). Like when a user creates an account in, his profile is automatically created.

For output it's a similar call:
- Client needs the related details to render (detail view) -> nested read (read_only=True).
- Client just needs the link, or it's a list endpoint -> flat (UUID). Nesting everything into a list of 100 rows is heavy.

Why nested writes are extra work: reading nests automatically (object -> relations -> JSON), but writing doesn't — one nested blob has to become multiple rows with FKs wired between them, and DRF can't guess the order. So nested fields are read_only by default so we need to override the create()/update().

## Custom fields

A field is a two-way translator for one value: to_representation (outbound, stored -> shown) and to_internal_value (inbound, sent -> stored).

- MoneyField: symmetric. Stores USD, shows taka.
- MaskedCardField: asymmetric. Outbound masks (show last 4), inbound stores the full number. Masking is one-way on purpose — we can't go from "****" to actual numbers. 

So custom fields are reversible two-way transform (money) vs one-way display transform (card).

## Validators — field-level vs object-level

Decided by how many fields the rule needs to look at.

- Needs ONE field -> validate_<fieldname>(). Example: amount must be positive.
- Needs MULTIPLE fields -> regular validate() in drf, which gets the whole dict. Example: from_account != to_account (can't check that with only one field in hand).

Field-level runs first, object-level runs after all fields individually pass. Both must return (the value, or data) or the field silently goes empty.

## Computed fields — SerializerMethodField

For values that aren't stored as a column but are computed at serialize time. Read-only, outbound only. Declare the field as SerializerMethodField() and write get_<fieldname>(self, obj); obj is the model instance.

Examples here:
- balance_in_taka -> derived from balance.
- transaction_count -> counted from the account's transactions, using Q(from_account=obj) | Q(to_account=obj) so either side counts (one query, and it won't double-count).
- last_active -> timestamp of the most recent transaction on either side.


## to_representation / to_internal_value at serializer level

Same idea as the custom-field versions, but for the WHOLE dict instead of one value. Runs once per object.

Reach for serializer-level to_representation only when the change spans more than one field — renaming/regrouping keys, building a field from multiple others, or dropping a field based on the object's state. Always call super() first to get the normal dict, then tweak it, then return it.

Most output changes are single-field, and a SerializerMethodField or a custom field does those more cleanly — so this hook is rarely needed. Used it here to add a summary (built from two fields) and to hide balance when an account is frozen, which a single-field tool can't do because it can't see across fields.

## Quick map

| When to- | Use |
| --- | --- |
| Standard model CRUD | ModelSerializer |
| Validate a non-model payload | Serializer (+ own create) |
| Bulk create / validate a batch | ListSerializer |
| Reference an existing related object | flat (UUID) |
| Create parent + child in one call | nested write (override create) |
| Transform one field's value | custom field |
| Validate one field | validate_<field> |
| Validate across fields | validate() |
| Show a value with no DB column | SerializerMethodField |
| Reshape the whole output dict | serializer to_representation |