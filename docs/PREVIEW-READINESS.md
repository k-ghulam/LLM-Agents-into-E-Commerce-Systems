# KooshkWear luxury preview — readiness and next steps

## Delivered in this update

- Original warm-ivory, dark-green and muted-gold design, editorial typography, accessible icon labels, visible search, category navigation, loading/error/empty states and a responsive CSS layer. No added runtime UI or font dependency.
- Search by name/description with escaped literal matching; exact EUR boundaries across integer-cent and legacy whole-euro products; category, size, colour and confirmed-stock filters; deterministic sorting and bounded pagination.
- Account-owned MongoDB wishlists, idempotent save/remove, a 200-product atomic cap and account-deletion cleanup. Guest saves use a separate browser list. Removed products do not break saved-product reads.
- Admin product-level recorded stock, optional JSON/Excel import field and visible unknown/out-of-stock states. Add-to-cart and demo-order requests check the recorded count. Demo orders explicitly record `order_kind=demo`, `payment_status=not_charged`, `fulfillment_status=not_applicable`.
- Quantity editing/removal in the shopping bag. Competing add operations use conditional updates and retry, preventing a stale cart count from bypassing a recorded-stock limit.
- A store guide and explicit preview notices. No fake ratings, invented shipping promises, made-up sales or nonfunctional newsletter form.
- `/config` declares disabled payment and reservation capabilities. Authenticated `/checkout` always returns 503 and creates no order/payment. No payment provider or paid resource was configured.

## Verification actually completed

61 pytest tests passed with mongomock/mocked providers. Python compilation, installed dependency consistency, parsing of all 39 browser modules, EUR arithmetic checks and frontend VM module tests passed. The frontend tests check account/guest wishlist isolation, persistence, a delayed old catalog response and search-text escaping.

A real browser/layout check could not be completed in the editing environment: the cloud browser could not access the local preview, and local browser execution was restricted. These are environment limitations, not evidence that the design has passed a real browser check. Mobile layout, keyboard focus order, screen-reader output, contrast and all visible controls must be checked on the applied local build or a deployed preview. No preview fixture/catalog data is included in the update.

Hosted MongoDB, index concurrency and real provider calls for the new features were not exercised. The earlier deployed version had working Atlas/chat and user-confirmed login/demo-order/mobile flows; that evidence does not validate this changed UI.

## Apply and review

1. Use the provided updater from the folder containing `main.py` and `Frontend`. It checks all touched files against reviewed baseline 363582e or the already-applied update before writing. Unexpected edits stop the entire update. It backs up changed source outside the project, preserves `.env` and does not connect to the database.
2. Run the README checks. Restart Uvicorn. MongoDB will create the new `wishlist.user_id` unique index and a catalog category/price index when the application starts. Existing product/order/cart data is not migrated or deleted. Wishlist records are created by user actions only.
3. At 390px mobile and desktop sizes: check horizontal overflow, mobile menu expansion, search submit, filters/reset, sort/page controls, empty/error/retry states, product links, favourite save/remove, account isolation and shopping bag quantity controls. Check the product-detail guide and the preview notices. Test the admin stock field, including blank, zero and a positive count. Check that out-of-stock items cannot be added or ordered through the API.
4. Use only test accounts/products. Verify EUR 19.99 × 3 and the prior account-ownership checks. Verify real checkout remains unavailable.
5. Run the updater with `--stage` to stage only its reviewed files, then commit and push. The existing Render service is configured to auto-deploy main. Check the new commit's deployment and logs before describing the new UI as live.

The updater does not stage itself. To roll back code, restore the recorded source backup locally or revert the release commit and push. The new additive indexes/collection can remain; do not drop existing data/indexes as part of a source rollback. Account wishlist entries are private user data and require the same backup/retention controls as other account records.

## Required before real sales

1. Replace name-based carts with durable product/variant IDs and migrate existing carts deliberately. Add an SKU for each size/colour combination, per-SKU stock, reservation expiry and audited inventory adjustments. A product-level count is insufficient for selling variants.
2. Implement one transactional/idempotent checkout operation with server pricing, taxes, shipping, immutable order lines and reliable inventory reservation. The existing client-side demo-order loop may partially record a multi-item cart on failure; it must not become a real checkout.
3. Choose a payment provider and implement signed webhooks, event deduplication, reconciliation, refund handling and an explicit order state machine. Never trust a browser success redirect as proof of payment. Payment fees and hosting costs require the owner's later decision.
4. Complete email verification/recovery, administrator MFA and a reviewed secure-cookie/CSRF session design. Current bearer sessions remain browser-readable. Add dependency/security review, real MongoDB integration and concurrent checkout testing.
5. Configure trusted proxy/rate-limit handling for the actual host. The inherited `--no-proxy-headers` setting can make clients share a proxy IP; the current shared limits need production topology validation.
6. Establish seller identity, delivery regions/costs, returns/refunds, tax treatment, privacy information and support contact. Review image/source rights and licensing; this update does not invent a license or legal terms.
7. Implement verified backups/restores, monitoring, order email delivery, accessibility/mobile QA and load testing. The unpaginated compatibility `/products` endpoint remains in admin/cart and should be replaced with bounded ID reads before a large catalog.

## Free-first policy

No paid plan, premium theme, checkout subscription or paid add-on is needed to apply this source update. Existing Render, Atlas and Groq accounts continue to have their own free-tier limits; future scale is not guaranteed to remain free. This release does not enable spending, real payment, automatic inventory decrement or fulfilment. It is a preparation milestone, not a production-commerce sign-off.
