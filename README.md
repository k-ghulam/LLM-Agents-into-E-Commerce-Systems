# LLM Agents into E-Commerce Systems — LUXE

A clothing-store integration project: FastAPI, MongoDB, a vanilla JavaScript storefront, and a read-only AI shopping assistant built with Pydantic AI and Groq. Maintained repository: [k-ghulam/LLM-Agents-into-E-Commerce-Systems](https://github.com/k-ghulam/LLM-Agents-into-E-Commerce-Systems).

**Status: a hardened demonstration, not a production commerce service.** Orders are records only: no money is charged, no inventory is reserved, and there is no payment processor or fulfillment integration. Prices retain the source project's integer rupee convention. Do not use customer data until the remaining release work below is complete.

## What was reviewed and how it was improved

The uploaded `CLOTHING STORE FDE RESOURCES.rar` contains three nested stages:

| Source stage | Review and integration decision |
| --- | --- |
| Legacy System Resources | Store, accounts, catalog, cart, orders and admin. Compared with the integrated store; duplicated insecure implementations are not shipped as runnable alternatives. |
| POC Development CODE | Standalone agent, MongoDB search, input/output guards and experiment notebooks. Compared with integrated AI modules; notebook outputs and historical credentials are not published. |
| FINAL INTEGRATION | Chosen as the maintained application because it combines the store, agent, evaluations and frontend. Hardened in this repository. |

The review process was: inventory the archives → compare the Python/JavaScript modules across all three stages → trace identity, account ownership, prices, uploads and AI calls → fix the integrated implementation → add offline regression tests → run validation → prepare a sanitized Git upload. Supporting PDFs, slides and demo assets were inventoried; no presentation-content or image-rights audit is claimed. They remain in the supplied source archive.

### Findings and implemented changes

| Original finding | Change |
| --- | --- |
| `X-User-Email` could impersonate an administrator | Random 256-bit bearer sessions, stored as SHA-256 digests in MongoDB. Every admin request resolves a real, unexpired session and checks the database role. |
| Other users' carts, order histories, profiles and avatars could be accessed by email | Account routes require a session and enforce ownership. Client email remains a compatibility field, never proof of identity. |
| Login did not create a server-verified session | Registration, password login and verified Google login now create an eight-hour session. Logout revokes it; profile changes revoke prior sessions and issue a replacement. |
| Browser could submit a forged unit price | Order price and product ID are copied from the database. Missing or ambiguously named products are rejected. |
| Cart updates used a read-then-write race | Atomic MongoDB upsert/increment with a unique account/product index. |
| Uploads were unbounded and trusted MIME labels | 24 MiB streamed request cap, per-file limits, Pillow raster verification, pixel limits and ZIP expansion/duplicate checks. SVG uploads are rejected. |
| Malformed guards or provider outages allowed unscreened AI responses | Guard failures now refuse the request/response. Chat has a typed 2,000-character limit, a 30-second pipeline budget and a five-request/tool-call budget. |
| Store startup depended on AI credentials | Provider initialization is deferred until configured chat is requested. Store and accounts work without AI. |
| No shared abuse throttling | MongoDB-backed counters: 10 authentication attempts/minute, 20 chats/minute, 120 other writes/minute per client IP. |
| Credentials and local tracing state were bundled | `.env`, `.logfire`, bytecode, notebooks and historical command files are excluded. Only blank configuration examples ship. Rotate all credentials from the original archive before reuse. |
| Unpinned dependencies and no regression suite | Exact direct dependencies, a full runtime lock snapshot, regression tests and GitHub CI are included. |
| UI described recording an order as purchasing | Order controls now explicitly say demo order. Unauthenticated users must sign in. |

GitHub upload status and terminal commands are in [PUBLISH.md](docs/PUBLISH.md).

See [review and remaining risks](docs/REVIEW.md) for the practical limits of these changes.

## Run locally — Linux Mint / macOS

Use Python 3.12 and MongoDB 7 or 8. Run commands from the project directory.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
cp .env.example .env
# Edit .env: set your MongoDB connection string.
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

If Docker is installed, a local development database can be started with:

```bash
docker run --name luxe-mongo -d -p 127.0.0.1:27017:27017 mongo:8
```

This database example has no authentication and is bound to loopback for local use only. Do not expose it publicly. For hosted MongoDB, use a dedicated least-privilege database user, TLS and restricted network access.

On Windows PowerShell, create the environment with `py -3.12 -m venv .venv`, activate with `.\.venv\Scripts\Activate.ps1`, and copy configuration with `Copy-Item .env.example .env`. The pip and uvicorn commands are the same.

Open [the store](http://127.0.0.1:8000), [API reference](http://127.0.0.1:8000/docs) or [health endpoint](http://127.0.0.1:8000/health). No Node build is required. The frontend is served by FastAPI and uses hash routes.

### Configure optional services

| Setting | Purpose |
| --- | --- |
| `MONGO_URI` | MongoDB URI; defaults to local MongoDB. Database name is `ecommerce_db`. |
| `GROQ_API_KEY` | Enables direct Groq chat; blank leaves the store usable with chat returning HTTP 503. |
| `PORTKEY_API_KEY`, `PORTKEY_GROQ_PROVIDER` | Optional alternative gateway for the configured Groq provider. |
| `AGENT_MODEL_NAME`, `GUARD_MODEL_NAME`, `PROMPT_GUARD_MODEL_NAME` | Provider model IDs. Source defaults are retained; check availability in your provider account before live testing. |
| `GOOGLE_CLIENT_ID` | Optional Google Identity Services client ID; configure the site's exact allowed origin in Google. |
| `LOGFIRE_TOKEN` | Optional external tracing. Without a configured token, export is disabled. Review privacy and retention before enabling. |
| `ONLINE_EVALS_ENABLED` | Default `false`; opt-in sampled live judge calls may send conversations to another model and incur charges. |

Never put secret values into source, a public README or a screenshot. The assistant only searches public product data; it has no checkout, account or admin tools.

### Create an administrator

1. Register a normal account in the Profile screen.
2. With your own database administrator connection, set `is_admin: true` on that exact existing account in MongoDB, for example in `mongosh`:

```javascript
use ecommerce_db
db.users.updateOne({ email: "owner@example.com" }, { $set: { is_admin: true } })
```

3. Sign in again and open Admin. There is no default admin password or public role-elevation endpoint. Do not enter the example email unless it is the account you actually registered.

## Validation

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q backend main.py
python -m pip check
node scripts/check-frontend.mjs
```

The frontend check needs Node 20+ and parses browser modules without executing them.

Tests use a fresh in-memory MongoDB fake per test and mocked AI calls. They cover authorization, session expiry/revocation, account isolation, pricing, image validation, ZIP limits, rate limits, bulk row validation and guard failure handling. They do not validate a hosted MongoDB connection, real Google OAuth, provider responses, a payment flow, Docker execution or browser interaction. See [VALIDATION.md](docs/VALIDATION.md) for the recorded result.

Live AI evaluation is a separate, paid-network operation and is **not** part of normal CI:

```bash
python -m backend.evals.chatbot_evals
```

## Project map

| Path | Responsibility |
| --- | --- |
| `main.py` | FastAPI startup, routers, static assets and health endpoint |
| `backend/auth.py` | Revocable session and ownership dependencies |
| `backend/middleware.py` | Request limits, shared abuse counters, response security headers |
| `backend/routes/` | Accounts, catalog, bulk uploads, cart, demo orders and chat |
| `backend/chatbot/` | Read-only search agent, guardrails and pipeline |
| `backend/evals/` | Optional live-model evaluation dataset |
| `Frontend/` | Storefront, profile, admin and chat UI; browser ES modules |
| `tests/` | Offline regression tests |
| `docs/` | Architecture, review findings, validation and deployment limits |
| `cloudbuild.yaml` | Optional inherited GCP deployment template; review before use |

## Before any production release

Use durable product IDs for cart operations; add idempotent transactional checkout, inventory handling and verified payment webhooks. Replace browser-readable bearer storage with an audited secure cookie/CSRF design, add email verification/recovery and MFA for administrators, and validate real MongoDB indexes and concurrent behavior. Finish accessibility and mobile browser testing, privacy notices, retention/deletion/export rules, dependency/security review and live AI evaluation. Configure trusted proxies and rate-limit policy for the actual hosting topology. Do not call this project “anti-hack” or production-ready.

## License and provenance

The uploaded README claimed MIT, but the archive did not include a license file or ownership evidence. No new license grant is invented here. Confirm source and demo-image rights, then add the appropriate `LICENSE` before redistribution beyond your authorized repository work.
