# EUR update validation — 17 October 2026

52 offline pytest tests passed, including the prior authentication, ownership, uploads and fail-closed AI coverage. Added exact-cent ingestion and mixed legacy/new filters, a server-priced EUR 19.99 × 3 order snapshot, decimal history, JSON and multipart validation, Excel decimal ingestion, and real search-tool filtering with mocked database access. Invalid boolean, negative, non-finite, over-limit and sub-cent amounts are rejected.

All 34 browser modules parsed. Node assertions confirmed EUR 0.10 + 0.20 = 30 cents, 19.99 × 3 = 5997 cents and EUR formatting. Python compilation and installed dependency consistency passed.

These results use mongomock and mocked AI providers. Real MongoDB integration, Docker build/run, browser interaction and Render deployment remain unverified. This record supplements, rather than replaces, the historical baseline in VALIDATION.md.
