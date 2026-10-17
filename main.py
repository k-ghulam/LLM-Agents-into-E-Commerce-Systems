from contextlib import asynccontextmanager
from pathlib import Path

import logfire
import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from backend.auth import current_user
from fastapi.staticfiles import StaticFiles

from backend.routes import products, products_bulk, orders, cart, chatbot, auth, google_auth, profile, wishlist
from backend.config import settings
from backend.database import ensure_indexes, client
from backend.middleware import SecurityMiddleware


# Configure Logfire for Observability. The SDK looks for LOGFIRE_TOKEN; this
# project historically stores it as LOGFIRE_API_KEY, so settings accepts either.
# Configured before the lifespan below runs, so a startup failure is traced too.
logfire.configure(
    send_to_logfire=bool(settings.logfire_write_token),
    token=settings.logfire_write_token,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run once on startup: create the unique-account indexes in MongoDB."""
    try:
        ensure_indexes()
    except Exception:
        logfire.exception("Startup failed: could not reach MongoDB to create indexes")
        raise
    try:
        yield
    finally:
        client.close()


# Initialize FastAPI app
app = FastAPI(title="KooshkWear Commerce API", lifespan=lifespan)
app.add_middleware(SecurityMiddleware)

logfire.instrument_fastapi(app)
logfire.instrument_pydantic()
logfire.instrument_pydantic_ai()  # agent run traces + online-evaluation events

# The monolith serves every endpoint — both halves of each route module.
ROUTE_MODULES = (products, products_bulk, orders, cart, chatbot, auth, google_auth, profile, wishlist)
for module in ROUTE_MODULES:
    app.include_router(module.read_router)
    app.include_router(module.write_router)


@app.get("/config")
def frontend_config():
    """
    Tells the frontend where the ingestion service lives. The monolith serves
    both reads and writes itself, so ingestion is just this same origin —
    without this, the frontend falls back to guessing port 8001 (the split
    services' ingestion port), which isn't running here and breaks any write
    call (e.g. Google sign-in) with a fetch failure.
    """
    return {"ingestion_base_url": "", "commerce_mode": "preview", "payments_enabled": False,
            "currency": "EUR", "inventory_reservations_enabled": False}


@app.post("/checkout", tags=["Commerce"])
def checkout(user: dict = Depends(current_user)):
    raise HTTPException(503, "Online payment is not enabled. Only demo orders are available.")


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the vanilla-JS frontend at the root.
app.mount("/", StaticFiles(directory=str(Path(__file__).resolve().parent / "Frontend"), html=True), name="frontend")

if __name__ == "__main__":
    print("Starting backend server (FastAPI)...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
