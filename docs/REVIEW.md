# Review and remaining risks

## Scope and method

The three nested archives were safely extracted without restoring symlinks or traversal paths. All Python/JavaScript modules and runtime/deployment configuration were inventoried; the final integration was compared with the legacy and POC stages and inspected by responsibility. PDF, PPTX, notebook and demo data files were inventoried, not independently audited for authorship or content accuracy. The final integration is the only maintained runnable tree. Historical copies are intentionally not duplicated into the public source tree.

Credential-bearing `.env` and `.logfire` files were present. They are excluded, alongside notebook outputs, caches and historical CLI commands. Treat source-archive credentials as exposed and rotate/revoke them at their providers. No provider credentials were used for validation.

## Residual release blockers

- **Commerce consistency:** cart lookup is still by product name. Duplicate names are rejected, but concurrent renames, price changes and catalog deletion need a product-ID migration. Demo multi-item ordering can partially succeed and retries can duplicate orders; do not add a payment gateway to this flow without transactional, idempotent checkout.
- **Sessions:** per-tab bearer tokens reduce accidental persistence but remain readable by JavaScript. An XSS can steal a token. An audited HttpOnly/Secure/SameSite cookie design with CSRF controls is preferred for production. Logout is sent best effort by the browser; a failed request leaves the server token valid until expiry. No refresh-token system, device management or MFA exists.
- **Accounts:** no email verification, reset or recovery flow. Email changes are rejected until verified identity migration is implemented, preventing orphaned carts/history. Google-only deletion still needs an identity reauthentication flow. Order retention after deletion needs a documented lawful policy. Username uniqueness with MongoDB collation requires real-server validation.
- **Existing databases:** new unique username/cart indexes may fail if duplicate documents already exist. Back up, inspect and reconcile duplicates before deploying. Startup intentionally fails rather than silently accepting missing indexes. mongomock cannot prove collation, TTL cleanup scheduling, transaction or cross-worker concurrency behavior.
- **Abuse:** fixed one-minute per-IP counters are shared through MongoDB and fail closed on database errors. They can allow bursts at a minute boundary. Reverse proxies may group users behind one IP; forwarding headers must be accepted only from explicitly trusted proxies. These counters are not DDoS protection. Apply edge limits, payload limits and provider spending limits in production.
- **Uploads:** bounded compressed/expanded sizes and Pillow checks protect this demo, not every file-format attack. Parse trusted administrator uploads only; add isolated scanning and object storage before broad use. Upload metadata does not prove image licensing. Workbooks/ZIPs may still consume CPU within limits.
- **Queries:** public product and account history reads have no pagination. Add pagination and safe projections before a large catalog. Image base64 storage increases MongoDB document/network costs; use object storage at scale.
- **AI:** no live provider/model availability, attack-resistance, latency, budget or factuality validation was performed. The assistant cannot purchase items, but probabilistic guards can still miss attacks. Fail-closed handling reduces availability when a guard is unavailable. Agent loop limits do not replace account-level billing quotas. Sample support contact details were removed.
- **Observability/privacy:** tracing and live evaluations are opt-in. Review captured inputs, profile data, credentials, processors, retention, international transfers and deletion obligations before enabling export. Application logs still contain account/order identifiers. This is not a GDPR certification.
- **Deployment:** no cloud deployment or settings changes were made. Docker and GCP templates need execution and environment-specific IAM/secrets verification. No full browser, keyboard, screen-reader or mobile QA was performed.
- **Ownership:** confirm the uploaded source and demo assets may be published and select a valid license. A README claiming MIT is not a substitute for a license grant.

## Priorities

First validate the current session and isolation tests against a disposable real MongoDB instance and run browser login/admin/cart checks. Next migrate commerce identity to product IDs and implement transactional checkout. Complete account verification/MFA and privacy controls before accepting real users or money.
