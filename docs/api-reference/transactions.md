---
layout: page
title: Transaction Endpoints
permalink: /api-reference/transactions/
---

# Transaction endpoints

The transaction routes expose the extracted entries tied to a user's bank statements.

## List transactions

```http
GET /api/transactions/
Authorization: Bearer <access_token>
```

Common filters:

- `statement_id=<statement_id>`
- `category=Groceries%20%26%20Food`
- `q=coffee`
- `ordering=-date` or `ordering=amount`

Example:

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8001/api/transactions/?statement_id=1&ordering=-date"
```

Example response:

```json
[
  {
    "id": 12,
    "date": "2026-10-05",
    "payee_payer": "Supermarket",
    "description": "Weekly groceries",
    "amount": -65.4,
    "transaction_type": "CARD_PAYMENT",
    "category": "Groceries & Food"
  }
]
```

## Retrieve one transaction

```http
GET /api/transactions/<id>/
Authorization: Bearer <access_token>
```

Example response:

```json
{
  "id": 12,
  "date": "2026-10-05",
  "payee_payer": "Supermarket",
  "description": "Weekly groceries",
  "amount": -65.4,
  "transaction_type": "CARD_PAYMENT",
  "category": "Groceries & Food"
}
```

## Transaction data schema

| Field | Type | Description |
| --- | --- | --- |
| `id` | integer | Primary key |
| `date` | string | Transaction date in `YYYY-MM-DD` format |
| `payee_payer` | string | Sender or recipient name |
| `description` | string | Booking details or notes |
| `amount` | number | Positive for income, negative for outgoing funds |
| `transaction_type` | string | One of the allowed transaction type values |
| `category` | string | One of the configured AI categories |

## Related pages

- [API overview]({{ '/api-reference/' | relative_url }})
- [Statement endpoints](./statements.html)
- [Account and privacy endpoints](./account.html)
