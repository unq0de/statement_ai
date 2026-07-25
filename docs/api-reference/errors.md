---
title: API Reference — Error Format
permalink: /api-reference/errors/
---

# Error Format
{: #error-format }

Errors are returned consistently as a JSON object with an `error` field (exception: registration validation errors, which are field-specific):

```json
{ "error": "Description of the error." }
```

| Status | Meaning |
|---|---|
| `400 Bad Request` | Invalid or missing input data |
| `401 Unauthorized` | Missing, invalid, or expired token |
| `404 Not Found` | Resource does not exist or belongs to another user |
| `500 Internal Server Error` | Unexpected server error (e.g. AI processing failed) |

> ℹ️ **Note:** A project-wide DRF exception handler guarantees this `{"error": "..."}` format even for cases DRF wouldn't normally catch cleanly — for example, a cryptographically valid refresh/access token whose underlying user no longer exists (deleted account, reset database, switched `DB_ENGINE`) is returned as a clean `401 Unauthorized` with `{"error": "Invalid or expired token."}` instead of an opaque `500`. All other unexpected exceptions are still logged server-side with a full traceback, but only ever exposed to the client as a generic `500` message.

---

Next: the [End-to-End Example]({{ '/api-reference/example-flow/' | relative_url }}) walks through a full request flow using `curl`.
