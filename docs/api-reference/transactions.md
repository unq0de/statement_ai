---
title: API Reference — Transactions
permalink: /api-reference/transactions/
---

# Transactions
{: #transactions }

## List Transactions
{: #list-transactions }

Lists all transactions from all bank statements of the logged-in user, sorted by date (newest first).

**Endpoint:** `GET /api/transactions/` · **Auth:** required

**Response `200 OK`**

```json
[
  {
    "id": 101,
    "date": "2026-07-01",
    "payee_payer": "ACME Corp",
    "description": "Monthly salary payment",
    "amount": "3200.00",
    "transaction_type": "INCOME",
    "category": "Salary & Main Income"
  },
  {
    "id": 100,
    "date": "2026-06-28",
    "payee_payer": "Netflix",
    "description": "Monthly subscription",
    "amount": "-15.99",
    "transaction_type": "CARD_PAYMENT",
    "category": "Subscriptions & Media"
  }
]
```

> There are currently no filter or pagination parameters — the endpoint always returns the complete list of all the user's transactions.

See [Data Models]({{ '/data-models/' | relative_url }}#transaction) for the full list of possible `transaction_type` and `category` values.

---

Next: [Account & Personal Data]({{ '/api-reference/account/' | relative_url }}) covers exporting and deleting your account.
