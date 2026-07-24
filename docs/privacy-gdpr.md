---
title: Privacy & GDPR
layout: default
---

# Privacy & GDPR

Statement AI processes financial data extracted from bank statements, which is personal data under the GDPR. The following measures are implemented:

| Measure | Implementation |
|---|---|
| 🧹 **Data minimization & retention** | Statements are automatically eligible for deletion after `DATA_RETENTION_DAYS` |
| 🗑️ **Right to erasure** | [`DELETE /api/auth/account/`]({{ site.baseurl }}/api-reference/#14-delete-my-account) permanently removes the account, statements, transactions & PDFs |
| 📤 **Right of access / portability** | [`GET /api/auth/export/`]({{ site.baseurl }}/api-reference/#13-export-my-data) returns all personal data as JSON |
| 🔒 **Access control** | PDFs are never publicly reachable, only via the [authenticated download endpoint]({{ site.baseurl }}/api-reference/#12-download-the-original-pdf) |
| 🌍 **Third-country data transfer** | Statement content is sent to **Google Gemini** (Google LLC, USA) for AI processing |

> 🤖 **Note on Gemini data usage:** This project uses a `GEMINI_API_KEY` from the Gemini API's **paid quota** (i.e. a Cloud project with an active billing account). According to Google's own terms, on Paid Services Google does **not** use your prompts or the PDF/statement content you submit, nor the generated responses, to improve its products or train models; prompts and responses are only logged for a limited time solely to detect and prevent violations of Google's Prohibited Use Policy and for required legal/regulatory disclosures. This is a different (and stricter) data handling regime than the **free/unpaid** Gemini tier, where submitted content and responses *may* be used by Google to improve its products and may be reviewed by humans. If you run this project on the free tier, treat it as unsuitable for real users' financial data. See Google's official **[Gemini API Additional Terms of Service](https://ai.google.dev/gemini-api/terms)**, sections "Paid Services → How Google Uses Your Data" and "Unpaid Services → How Google Uses Your Data", for the authoritative wording.

> ⚖️ **Disclaimer:** This section describes the technical measures available in the API — **not legal advice**. Consult a data protection professional before processing real users' financial data in production. If you operate this API for real users in the EU/EEA, you are responsible for having a valid legal basis and a Data Processing Agreement (DPA) with Google covering this transfer.
