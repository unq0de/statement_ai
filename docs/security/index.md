---
layout: page
title: Security and Privacy
permalink: /security/
---

# Security and privacy

This project handles financial data, so access control and retention are important parts of the design.

## Data isolation

Every `BankStatement` is linked to a single Django user. The API views filter by `user=self.request.user` or by the statement owner before returning data. This prevents one user from reading or deleting another user's statements or transactions.

## Authentication and authorization

The project uses JWT authentication for protected endpoints. Requests without a valid token are rejected with `401 Unauthorized`.

The system also uses access checks on file downloads and statement detail operations. For example, the original PDF file is only served if the current user owns the statement.

## File handling

Uploaded PDFs are stored in the local media directory and tied to the owning user. They are not exposed through a public static route in production. Instead, the application serves the file through the authenticated API route.

## Personal data export

The export endpoint returns the user's own data as JSON. This is intended to support access and portability workflows for personal financial information.

## Account deletion

Deleting an account is not a soft delete. The API confirms the password and then removes the user record. Related statements, transactions, and uploaded files are deleted as part of the cascade.

## Data retention

The project includes automatic data retention through the `delete_expired_data` management command. The `DATA_RETENTION_DAYS` environment variable controls how long statement records remain eligible for cleanup.

This is a practical safeguard that helps reduce long-term storage of old banking data.

## Security recommendations

For production usage, you should:

- keep `SECRET_KEY` in a secure environment variable
- rotate the Gemini API key if it is exposed
- use `DEBUG=0` in production
- set explicit `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`
- protect the database and media directory with the same access controls as the rest of the app

## Related pages

- [Features]({{ '/features/' | relative_url }})
- [Troubleshooting]({{ '/troubleshooting/' | relative_url }})
- [API reference]({{ '/api-reference/' | relative_url }})
