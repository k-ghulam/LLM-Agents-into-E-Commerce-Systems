import importlib
import sys
from pathlib import Path
import mongomock
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "portkey_api_key", "")
    monkeypatch.setattr(settings, "logfire_token", None)
    monkeypatch.setattr(settings, "logfire_api_key", None)
    monkeypatch.setenv("LOGFIRE_IGNORE_NO_CONFIG", "1")

@pytest.fixture
def client(monkeypatch):
    import backend.database as database
    db = mongomock.MongoClient(tz_aware=True).ecommerce_db
    collections = {name + "_collection": db[name] for name in ("users", "products", "orders", "cart", "sessions", "rate_limits", "wishlist")}
    for attr, value in collections.items():
        monkeypatch.setattr(database, attr, value)
    import main
    for name, module in list(sys.modules.items()):
        if name.startswith("backend."):
            for attr, value in collections.items():
                if hasattr(module, attr):
                    monkeypatch.setattr(module, attr, value)
    with TestClient(main.app) as api:
        yield api, db

@pytest.fixture
def account(client):
    api, db = client
    response = api.post("/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "StrongPass123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}
