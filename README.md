# KooshkWear — LLM Agents into E-Commerce Systems

**Storefront:** KooshkWear  
**Development and customization:** KooshkTech

A clothing-store integration project: FastAPI, MongoDB, a vanilla JavaScript storefront, and a read-only AI shopping assistant built with Pydantic AI and Groq. Maintained repository: [k-ghulam/LLM-Agents-into-E-Commerce-Systems](https://github.com/k-ghulam/LLM-Agents-into-E-Commerce-Systems).

**Status: a hardened demonstration, not a production commerce service.** Orders are records only: no money is charged, no inventory is reserved, and there is no payment processor or fulfillment integration. Prices support exact **EUR (€)** amounts such as `19.99`. New writes store integer `price_cents` and currency `EUR`; API responses include a two-decimal `price` string. Existing whole-euro `price` records remain readable without a bulk database rewrite. This does not convert exchange rates; review original catalog amounts. Do not use customer data until the remaining release work below is complete.

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
| Cart updates used a read-then-write race | A unique account/product index and conditional quantity updates prevent lost increments. The preview update retries competing updates and checks the recorded stock count. This does not reserve inventory. |
| Uploads were unbounded and trusted MIME labels | 24 MiB streamed request cap, per-file limits, Pillow raster verification, pixel limits and ZIP expansion/duplicate checks. SVG uploads are rejected. |
| Malformed guards or provider outages allowed unscreened AI responses | Guard failures now refuse the request/response. Chat has a typed 2,000-character limit, a 30-second pipeline budget and a five-request/tool-call budget. |
| Store startup depended on AI credentials | Provider initialization is deferred until configured chat is requested. Store and accounts work without AI. |
| No shared abuse throttling | MongoDB-backed counters: 10 authentication attempts/minute, 20 chats/minute, 120 other writes/minute per client IP. |
| Credentials and local tracing state were bundled | `.env`, `.logfire`, bytecode, notebooks and historical command files are excluded. Only blank configuration examples ship. Rotate all credentials from the original archive before reuse. |
| Unpinned dependencies and no regression suite | Exact direct dependencies, a full runtime lock snapshot, regression tests and GitHub CI are included. |
| UI described recording an order as purchasing | Order controls now explicitly say demo order. Unauthenticated users must sign in. |

The user has confirmed their local `main` branch is synchronized with `origin/main`. Publishing instructions are in [PUBLISH.md](docs/PUBLISH.md); its earlier HTTP 403 note is a historical record of the connected integration, not a statement that the user cannot push from their authenticated terminal.

See [review and remaining risks](docs/REVIEW.md) for the practical limits of these changes.

## Run locally — Linux Mint / macOS

Use Python 3.12. Run commands from the project directory. The application connects to MongoDB Atlas or another compatible MongoDB 7/8 server; the database does not have to run on the same computer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
cp -n .env.example .env
geany .env
```

`geany .env` is for users of Geany; use your preferred editor otherwise. If your configured `python3` is not Python 3.12, select the Python 3.12 interpreter when creating the environment.

### Connect to MongoDB Atlas

1. Create or resume the intended Atlas cluster.
2. Add your current public IP to the project's IP access list.
3. Create a dedicated database user with `readWrite` access to `ecommerce_db`. This is a database credential, separate from your Atlas website login.
4. Choose the Python / PyMongo connection method and copy the cluster URI.
5. Store it in your local `.env` as `MONGO_URI`. URL-encode the username and password when they contain reserved URI characters. Network compression can remain disabled.

Example only — replace all placeholders privately:

```dotenv
MONGO_URI='mongodb+srv://YOUR_DATABASE_USER:YOUR_URL_ENCODED_PASSWORD@YOUR_CLUSTER.mongodb.net/'
```

The application selects `ecommerce_db` in code. Do not publish your real URI, password or `.env`. Do not disable TLS verification to work around a connection failure.

Start the storefront and API in the same process:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Open [the store](http://127.0.0.1:8000), [API reference](http://127.0.0.1:8000/docs) or [health endpoint](http://127.0.0.1:8000/health). Keep the terminal running. No Node build is required; the frontend uses browser ES modules and hash routes.

### Optional local MongoDB with Docker

Docker Engine is enough; Docker Desktop is not required. **Check CPU compatibility first:** MongoDB 5+ on x86-64 requires AVX support. The user's older Linux Mint computer reported no AVX support and could not run `mongo:8`; that setup uses Atlas instead. Installing Docker Desktop does not supply missing CPU instructions.

On a compatible development computer:

```bash
docker run -d --name kooshkwear-mongo \
  --restart unless-stopped \
  -p 127.0.0.1:27017:27017 \
  -v kooshkwear-mongo-data:/data/db \
  mongo:8
```

Use `MONGO_URI=mongodb://127.0.0.1:27017` for that local database. The example has no database authentication and is restricted to the local computer. Do not expose it publicly. Hosted deployments need TLS, a least-privilege database user and restricted network access.

On Windows PowerShell, create the environment with `py -3.12 -m venv .venv`, activate with `.\.venv\Scripts\Activate.ps1`, and copy `.env.example` to `.env` only if `.env` does not already exist. The pip and uvicorn commands are the same.

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
2. Stop the local server with Ctrl+C. In the active project virtual environment, run the following administrative script and enter the exact registered email privately:

```bash
python - <<'PYADMIN'
from getpass import getpass
from backend.database import users_collection, client

try:
    email = getpass("Registered account email: ").strip().lower()
    result = users_collection.update_one(
        {"email": email}, {"$set": {"is_admin": True}}
    )
    print("Admin access enabled." if result.matched_count else "Account not found.")
finally:
    client.close()
PYADMIN
```

3. Restart the server, sign out and sign in again, then open [Admin](http://127.0.0.1:8000/#/admin).

Run this script only with your authorized database connection, for the account you intend to administer the store. There is no default admin password or public role-elevation endpoint.

### First product and demo order

Add a test product in Admin with a JPEG/PNG/WebP image and an intended EUR price, for example `19.99` for €19.99. Browse the product, add it to your cart, and check its quantity and price. Demo orders do not charge money.

An unauthenticated cart request may return HTTP 401; sign in before using account/cart features. The application startup message confirms startup indexes were created, not that every feature has been validated.

## Validation

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q backend main.py
python -m pip check
node scripts/check-frontend.mjs
node scripts/check-money.mjs
```

The frontend check needs Node 20+ and parses browser modules without executing them.

Tests use a fresh in-memory MongoDB fake per test and mocked AI calls. They cover authorization, session expiry/revocation, account isolation, pricing, image validation, ZIP limits, rate limits, bulk row validation and guard failure handling. They do not validate a hosted MongoDB connection, real Google OAuth, provider responses, a payment flow, Docker execution or browser interaction. The luxury-preview update passes **61 offline tests**, parses **39 browser JavaScript modules**, and passes integer-cent arithmetic and storefront module checks. Browser and responsive visual verification of the new design is pending. See [VALIDATION.md](docs/VALIDATION.md) for the earlier recorded baseline. The user separately reported successful application startup with Atlas; this is not an end-to-end production validation.

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

## Store identity and developer credit

- **Store name:** KooshkWear.
- **Developer/customizer credit:** Developed and customized by KooshkTech.
- **Currency display:** EUR (€); no automatic exchange-rate conversion.
- **Footer:** the developer credit is separate from the store name.

No verified business address, support email, phone number, VAT ID, domain registration or trademark availability is asserted. Add confirmed business details before public release. Developer credit does not replace original source attribution or third-party licenses.

## License and provenance

The uploaded README claimed MIT, but the archive did not include a license file or ownership evidence. No new license grant is invented here. Confirm source and demo-image rights, then add the appropriate `LICENSE` before redistribution beyond your authorized repository work.

## Development and customization

Developed and customized by **KooshkTech**.

The storefront name is KooshkWear. KooshkTech is the developer/customizer credit, not the storefront name. This credit does not claim exclusive authorship of the uploaded source; original provenance, third-party acknowledgements and applicable license obligations remain in force.

Display prices and AI currency examples use euros. New prices use integer cents; legacy integer prices are read as whole euros. No exchange-rate conversion or automatic bulk database rewrite is performed. Review existing catalog amounts manually. This update does not read or change `.env`, credentials, stored database data, session namespaces or cloud configuration.

## Decimal EUR and public demo hosting

The change was traced through JSON and form ingestion, Excel import, mixed old/new catalog filters, the shopping agent, cart totals and demo order snapshots. Decimal parsing rejects negative, non-finite and sub-cent amounts rather than rounding them silently. Inputs are limited to EUR 1,000,000 per unit. Order prices come from the catalog, regardless of browser submissions. New orders store `price_cents`, `total_cents` and `currency`; legacy history remains readable. Updating a product price replaces that product's legacy price field only.

See [Render setup](docs/RENDER.md) for the prepared hosting configuration, private secret entry and live verification steps. The Docker command supports Render's `PORT` variable. This is a FastAPI application; it can run directly as a Render web service without rewriting it in Streamlit. No public URL has been validated yet.

## Luxury storefront preparation — free tools, payment disabled

This release prepares an original KooshkWear shopping experience: editorial hero and typography, visible catalog search, a paginated filter sidebar, price/name sorting, product favourites, product availability, an editable shopping bag and a store guide. It takes general usability ideas from established stores without reproducing their branding, code, reviews or claims. It retains KooshkTech's developer/customizer credit and the original provenance section.

The frontend uses the existing vanilla JavaScript/FastAPI stack. No paid UI kit, font subscription, payment SDK, new hosting resource or additional runtime dependency is introduced. Existing external provider and hosting usage remains subject to those accounts' limits. The existing editorial hero image is retained; image rights and actual product photography still need review before commercial release.

The process was: verify the exact GitHub baseline `363582e` → trace current catalog/cart/account APIs → add compatible search and wishlist endpoints → add explicit preview capabilities and recorded stock checks → redesign the connected pages → exercise backend regressions and frontend module logic → package a reversible update. The project now has 61 offline tests. These include wishlist isolation/caps/account cleanup, literal search, mixed legacy and cents prices, pagination, inventory checks, cart edits and an interleaved cart update. See [PREVIEW-READINESS.md](docs/PREVIEW-READINESS.md) for changes, limitations and the route to real commerce.

### Added storefront APIs

| Endpoint | Purpose |
| --- | --- |
| `GET /products/search` | Paginated search, category, EUR min/max, size, colour, stock and sorting |
| `GET /wishlist` | Current account's saved products; authentication required |
| `PUT /wishlist/{product_id}` | Idempotently save an existing product, max 200 per account |
| `DELETE /wishlist/{product_id}` | Remove from the current account's wishlist |
| `PUT /cart/item` | Set the current account's product quantity |
| `DELETE /cart/item?product_name=...` | Remove one current-account cart item |
| `POST /checkout` | Always returns HTTP 503 for authenticated users: real payment is disabled |

`GET /config` advertises `commerce_mode: preview`, `payments_enabled: false` and `inventory_reservations_enabled: false`. This is a deliberate closed boundary, not a simulated successful payment. Adding an environment variable cannot enable real commerce by itself.

### Stock and favourites

Admin supports an optional **Recorded stock** count. Blank means availability is unconfirmed; zero means out of stock. JSON bulk import accepts `stock_quantity` as a nonnegative integer or null; Excel accepts an optional numeric whole-number column of the same name. The multipart admin API uses `-1` to clear that optional count. Existing products without the field remain readable and unchanged. Product-level stock is not size/colour inventory, and demo orders neither reserve nor decrement it.

Signed-in favourites live in MongoDB, keyed by immutable user ID, and are removed on account deletion. Guest favourites are saved on that browser only. Guest and account lists are intentionally separate. Product reads retain their original API compatibility; the new storefront uses `/products/search`.

### Validate this update

```bash
python -m pytest -q
python -m compileall -q backend main.py
python -m pip check
node scripts/check-frontend.mjs
node scripts/check-money.mjs
node --experimental-vm-modules scripts/check-storefront.mjs
```

The last command uses Node's built-in VM module test support and does not need npm packages. It validates wishlist identity isolation, guest persistence, stale catalog-response protection and escaped search text. It does not render a browser or prove accessibility/layout correctness.
