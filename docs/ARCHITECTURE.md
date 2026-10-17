# Architecture

One FastAPI process serves a browser ES-module storefront and all HTTP routes. MongoDB stores users, session digests, products, carts, demo orders and shared rate counters. Static paths are resolved relative to `main.py`, independent of the process working directory.

Registration/password login/verified Google login issue a random token with eight-hour expiry. The browser keeps it in per-tab `sessionStorage` and sends `Authorization: Bearer ...`. MongoDB stores a digest and user ID, never the raw token. Each protected request checks expiry and fetches the current user. Roles are read from the database each time. Email inputs must match the authenticated user. Tokens are revoked on logout, profile modification and account deletion.

Catalog reads are public; modifications require admin authorization. Orders copy the catalog price and product ID, ignoring any submitted price. Legacy cart operations still identify products by name: ambiguous or missing names return 409. This is a demo record flow, not payment or fulfillment.

Chat imports its providers only when configured. Typed input → parallel input guards → read-only agent/product search (eight results) → output guard → escaped browser rendering. Malformed guard results and guard outages fail closed. The complete pipeline has a 30-second deadline; provider guard calls have ten-second deadlines without retries, and agent runs have at most five requests/tool calls. Regex product filters are escaped, and the agent has no generic MongoDB execution tool.

External Logfire export is disabled without a configured token. Enabling tracing, Portkey or online evaluation changes where conversation data may be processed; review privacy terms before enabling any of them.
