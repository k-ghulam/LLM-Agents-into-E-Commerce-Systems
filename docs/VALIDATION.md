# Validation record — 17 October 2026

Validated locally on Linux with Python 3.12. No original provider credentials were used.

| Check | Result |
| --- | --- |
| Offline regression suite (`python -m pytest -q`) | 35 tests pass |
| Browser ES-module parsing (`node scripts/check-frontend.mjs`) | All 33 modules pass |
| Python compilation (`python -m compileall -q backend main.py`) | Pass |
| Dependency metadata (`python -m pip check`) | Pass |
| Fresh virtual environment installed only from `requirements.lock` | Installation and dependency check pass |
| Known source-config credential comparison | No exact source credential values found in deliverables |
| Git whitespace check | Pass |
| GitHub upload | Blocked: integration returned HTTP 403; no successful upload |

The test suite uses mongomock and mocked provider calls. It covers registration, password login, forged admin headers, authenticated admin product CRUD, token digest storage, session expiry/logout, cross-account access denial, server catalog prices, atomic cart increments, missing/ambiguous products, avatar content and ownership, body limits, shared rate counters, ZIP expansion/duplicate rejection, partial bulk row errors, profile session rotation, mocked verified Google sign-in, deletion revocation and AI fail-closed behavior.

Not run: real MongoDB collation/TTL/concurrency integration tests, live Google OAuth, live AI evaluations, real-browser interactions, Docker build/run, dependency vulnerability audit, payment/fulfillment or any cloud deployment. Passing offline tests does not establish production readiness.

See [PUBLISH.md](PUBLISH.md) for publishing the prepared files using an account with repository write access.
