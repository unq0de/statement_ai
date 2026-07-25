---
title: API Reference — End-to-End Example
permalink: /api-reference/example-flow/
---

# Typical Flow (End-to-End Example)
{: #typical-flow }

**1. Register**

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "max", "email": "max@example.com", "password": "ASecurePassword123!"}'
```

**2. Log in and obtain tokens**

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "max", "password": "ASecurePassword123!"}'
# -> { "access": "...", "refresh": "..." }
```

**3. Upload a bank statement**

```bash
curl -X POST http://localhost:8000/api/statements/upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@statement_july.pdf"
```

**4. View all bank statements**

```bash
curl http://localhost:8000/api/statements/ \
  -H "Authorization: Bearer <access_token>"
```

**5. View all transactions**

```bash
curl http://localhost:8000/api/transactions/ \
  -H "Authorization: Bearer <access_token>"
```

**6. View AI evaluations**

```bash
curl http://localhost:8000/api/statements/analytics/ \
  -H "Authorization: Bearer <access_token>"
```

**7. Download the original PDF of a statement**

```bash
curl -OJ http://localhost:8000/api/statements/14/file/ \
  -H "Authorization: Bearer <access_token>"
```

**8. Export all of my personal data**

```bash
curl http://localhost:8000/api/auth/export/ \
  -H "Authorization: Bearer <access_token>"
```

**9. Refresh the token once the access token expires**

```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

**10. Delete a single bank statement**

```bash
curl -X DELETE http://localhost:8000/api/statements/14/ \
  -H "Authorization: Bearer <access_token>"
```

**11. Delete all bank statements** *(warning: irreversible!)*

```bash
curl -X DELETE http://localhost:8000/api/statements/delete-all/ \
  -H "Authorization: Bearer <access_token>"
```

**12. Delete my entire account** *(warning: irreversible!)*

```bash
curl -X DELETE http://localhost:8000/api/auth/account/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "ASecurePassword123!"}'
```

---

Next: [Project Structure]({{ '/project-structure/' | relative_url }}) gives an overview of how the codebase is laid out.
