import io
import pytest
from PIL import Image
from backend.utils.money import cents

@pytest.mark.parametrize("value", [True, False, "NaN", "Infinity", "-0.01", "1.001", "1000000.01", ""])
def test_invalid_money(value):
    with pytest.raises(ValueError):
        cents(value)


def test_mixed_catalog_filters(client):
    api, db = client
    db.products.insert_many([
        {"name": "Old", "price": 35, "category": "women"},
        {"name": "Decimal", "price_cents": 1999, "currency": "EUR", "category": "women"},
        {"name": "Boundary", "price": 20, "category": "women"}])
    results = api.get("/products?min_price=19.99&max_price=20&category=women").json()
    assert {r["name"] for r in results} == {"Decimal", "Boundary"}
    assert api.get("/products?max_price=19.98").json() == []
    assert api.get("/products?min_price=20.01&max_price=35").json()[0]["price"] == "35.00"
    assert api.get("/products?max_price=NaN").status_code == 422
    assert db.products.find_one({"name": "Old"})["price"] == 35


def test_exact_order_and_history(client, account):
    api, db = client
    db.products.insert_one({"name": "Shirt", "price_cents": 1999, "currency": "EUR"})
    response = api.post("/orders", headers=account, json={"user_email": "alice@example.com", "product_name": "Shirt", "quantity": 3, "price": "0.01"})
    assert response.status_code == 200
    order = db.orders.find_one()
    assert order["price_cents"] == 1999 and order["total_cents"] == 5997
    assert "price" not in order
    history = api.get("/orders/alice@example.com", headers=account).json()
    assert history[0]["price"] == "19.99" and history[0]["total_cents"] == 5997


def test_decimal_admin_paths(client, account):
    api, db = client
    db.users.update_one({"email": "alice@example.com"}, {"$set": {"is_admin": True}})
    product = {"name": "Shirt", "description": "Cotton", "price": "19.99", "category": "men", "size": ["M"], "color": ["Red"], "image": "https://example.com/shirt.png"}
    assert api.post("/products/bulk", json=[product], headers=account).status_code == 200
    assert db.products.find_one()["price_cents"] == 1999
    for invalid in ["1.001", True, "NaN"]:
        assert api.post("/products/bulk", json=[{**product, "price": invalid}], headers=account).status_code == 422
    image = io.BytesIO(); Image.new("RGB", (2, 2)).save(image, format="PNG")
    data = {"name": "New", "description": "Cotton", "price": "0.10", "category": "women"}
    result = api.post("/products", data=data, files={"image": ("shirt.png", image.getvalue(), "image/png")}, headers=account)
    assert result.status_code == 200, result.text
    stored = db.products.find_one({"name": "New"})
    assert stored["price_cents"] == 10
    assert api.put("/products/" + str(stored["_id"]), data={"price": "19.99"}, headers=account).status_code == 200
    assert db.products.find_one({"name": "New"})["price_cents"] == 1999
