---
layout: page
title: Transaction Endpoints
permalink: /api-reference/transactions/
---

# Transaction endpoints

The transaction routes expose the entries Gemini extracted from the user's statements. Both routes require authentication and are read-only: transactions cannot be created, edited or deleted through the API. They disappear when their statement is deleted.

## List transactions

```http
GET /api/transactions/
Authorization: Bearer <access_token>
```

Returns transactions across all of the user's statements as a JSON array, without pagination.

| Query parameter | Description |
| --- | --- |
| `statement_id` | Only transactions of this statement. Pass an integer. |
| `category` | Case-insensitive exact match, for example `Groceries & Food` (URL-encode it). |
| `q` | Case-insensitive substring search over `description`, `payee_payer` and `category`. |
| `ordering` | `date`, `-date`, `amount` or `-amount`. Default `-date`. Other values fall back to the default. |

Filters combine with AND.

```bash
curl -G http://localhost:8001/api/transactions/ \
  -H "Authorization: Bearer <access_token>" \
  --data-urlencode "category=Groceries & Food" \
  --data-urlencode "ordering=amount"
```

`200 OK`:

```json
[
  {
    "id": 12,
    "date": "2026-10-05",
    "payee_payer": "Supermarket",
    "description": "Weekly groceries",
    "amount": "-65.40",
    "transaction_type": "CARD_PAYMENT",
    "category": "Groceries & Food"
  }
]
```

The `statement_id` filter is not validated. A non-numeric value will most likely cause a `500` (inferred from the code, not tested), so pass an integer.

## Retrieve one transaction

```http
GET /api/transactions/<id>/
Authorization: Bearer <access_token>
```

Returns one transaction in the shape above. `404` if it does not exist or belongs to another user.

## Transaction fields

| Field | Type | Description |
| --- | --- | --- |
| `id` | integer | Primary key. |
| `date` | string | Booking date, `YYYY-MM-DD`. |
| `payee_payer` | string | Counterparty name. May be empty. |
| `description` | string | Short English description of the booking. |
| `amount` | string | Decimal with two places. Negative for outgoing money, positive for incoming. |
| `transaction_type` | string | One of the values below. |
| `category` | string | One of the categories below. |

**Transaction types:** `INCOME`, `TRANSFER_OUT`, `TRANSFER_IN`, `DIRECT_DEBIT`, `STANDING_ORDER`, `CARD_PAYMENT`, `ATM_WITHDRAWAL`, `FEE_CHARGE`.

**Categories:** `Housing & Utilities`, `Groceries & Food`, `Dining Out & Cafes`, `Transportation`, `Shopping & Retail`, `Subscriptions & Media`, `Health & Medical`, `Financial & Insurance`, `Salary & Main Income`, `Secondary Income`, `Transfers & P2P`, `Education & Childcare`, `Travel & Vacations`, `Cash & ATM`, `Miscellaneous & Other`.

Both lists are defined in the Gemini prompt. The database does not enforce them, and the code does not re-check Gemini's answer against them, so treat them as strongly expected rather than guaranteed.

## Related pages

- [API overview]({{ '/api-reference/' | relative_url }})
- [Statement endpoints]({{ '/api-reference/statements/' | relative_url }})
- [Account and privacy endpoints]({{ '/api-reference/account/' | relative_url }})
