from datetime import datetime, timedelta, timezone
import io
import zipfile
import pytest
from fastapi import HTTPException
from PIL import Image


def test_health_static_and_no_ai(client):
    api, _ = client
    assert api.get("/health").json() == {"status": "ok"}
    assert api.get("/").status_code == 200
    assert api.get("/src/main.js").status_code == 200
    assert api.post("/chat", json={"message": "shirt"}).status_code == 503
    assert api.post("/chat", json={"message": 123}).status_code == 422
    assert api.post("/chat", json={"message": "x" * 2001}).status_code == 422


def test_email_cannot_impersonate_admin(client, account):
    api, db = client
    db.users.update_one({"email": "alice@example.com"}, {"$set": {"is_admin": True}})
    assert api.delete("/products", headers={"X-User-Email": "alice@example.com"}).status_code == 401
    assert api.get("/auth/is-admin?email=alice@example.com").status_code == 401
    assert api.get("/auth/is-admin", headers=account).json()["is_admin"] is True
    assert api.delete("/products", headers=account).status_code == 200


def test_non_admin_cannot_modify_catalog(client, account):
    api, _ = client
    assert api.delete("/products", headers=account).status_code == 403
    assert api.post("/products/bulk", json=[], headers=account).status_code == 403


def test_session_expiry_logout_and_hashed_storage(client, account):
    api, db = client
    session = db.sessions.find_one()
    assert "access_token" not in session
    assert account["Authorization"][7:] != session["token_hash"]
    assert api.get("/auth/profile?email=alice@example.com", headers=account).status_code == 200
    assert api.post("/auth/logout", headers=account).status_code == 200
    assert api.get("/auth/profile?email=alice@example.com", headers=account).status_code == 401
    response = api.post("/auth/login", json={"identifier": "alice", "password": "StrongPass123!"})
    token = response.json()["access_token"]
    db.sessions.update_many({}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}})
    assert api.get("/auth/is-admin", headers={"Authorization": "Bearer " + token}).status_code == 401


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/cart/bob@example.com", None),
    ("delete", "/cart/bob@example.com", None),
    ("get", "/orders/bob@example.com", None),
    ("get", "/auth/profile?email=bob@example.com", None),
    ("post", "/cart/add", {"user_email": "bob@example.com", "product_name": "Shirt", "quantity": 1}),
    ("post", "/orders", {"user_email": "bob@example.com", "product_name": "Shirt", "quantity": 1, "price": 0}),
    ("put", "/auth/profile", {"current_email": "bob@example.com", "current_password": "StrongPass123!", "new_username": "stolen"}),
    ("delete", "/auth/account", {"email": "bob@example.com", "password": "StrongPass123!"}),
])
def test_cross_account_access_denied(client, account, method, path, payload):
    api, _ = client
    kwargs = {"headers": account}
    if payload is not None: kwargs["json"] = payload
    assert api.request(method, path, **kwargs).status_code == 403


def test_server_prices_and_cart_increment(client, account):
    api, db = client
    db.products.insert_one({"name": "Shirt", "price": 499})
    data = {"user_email": "alice@example.com", "product_name": "Shirt", "quantity": 2}
    for _ in range(2): assert api.post("/cart/add", json=data, headers=account).status_code == 200
    assert db.cart.count_documents({}) == 1
    assert db.cart.find_one()["quantity"] == 4
    assert api.post("/orders", json={**data, "price": 1}, headers=account).status_code == 200
    assert db.orders.find_one()["price"] == 499
    assert "product_id" in db.orders.find_one()
    assert api.post("/orders", json={**data, "product_name": "Missing", "price": 1}, headers=account).status_code == 409
    db.products.insert_one({"name": "Shirt", "price": 999})
    assert api.post("/orders", json={**data, "price": 1}, headers=account).status_code == 409


def test_avatar_validated_and_owner_only(client, account):
    api, _ = client
    files = {"avatar": ("bad.svg", b"<svg></svg>", "image/png")}
    assert api.post("/auth/avatar", data={"email": "alice@example.com"}, files=files, headers=account).status_code == 415
    assert api.post("/auth/avatar", data={"email": "bob@example.com"}, files=files, headers=account).status_code == 403
    image = io.BytesIO(); Image.new("RGB", (2, 2)).save(image, format="PNG")
    response = api.post("/auth/avatar", data={"email": "alice@example.com"}, files={"avatar": ("image.png", image.getvalue(), "image/png")}, headers=account)
    assert response.status_code == 200
    assert response.json()["avatar"].startswith("data:image/png;base64,")


def test_rate_limit_shared_counter(client):
    api, db = client
    for _ in range(10):
        assert api.post("/auth/login", json={"identifier": "missing", "password": "bad"}).status_code == 401
    response = api.post("/auth/login", json={"identifier": "missing", "password": "bad"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert db.rate_limits.find_one()["count"] == 11


def test_oversized_body_rejected_before_route(client):
    api, _ = client
    response = api.post("/chat", content=b"x" * (24 * 1024 * 1024 + 1))
    assert response.status_code == 413


def test_password_validation_and_no_hash_leak(client, account):
    api, _ = client
    response = api.post("/auth/register", json={"username": "bob", "email": "bad", "password": "short"})
    assert response.status_code == 422
    assert api.post("/auth/login", json={"identifier": "alice", "password": "x" * 100}).status_code == 401
    response = api.get("/auth/profile?email=alice@example.com", headers=account)
    assert "password_hash" not in response.json()
    assert response.headers["cache-control"] == "no-store"


def test_zip_bomb_and_duplicates_rejected():
    from backend.utils.uploads import validate_zip
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb", b"x" * 100000)
    with pytest.raises(HTTPException) as error: validate_zip(output.getvalue(), 200000)
    assert error.value.status_code == 413
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("a/one.png", b"1"); archive.writestr("b/ONE.png", b"2")
    with pytest.raises(HTTPException) as error: validate_zip(output.getvalue(), 200000)
    assert error.value.status_code == 400


def test_profile_change_rotates_sessions(client, account):
    api, db = client
    response = api.put("/auth/profile", json={"current_email": "alice@example.com", "current_password": "StrongPass123!", "new_username": "alice2"}, headers=account)
    assert response.status_code == 200
    assert response.json()["access_token"] != account["Authorization"][7:]
    assert api.get("/auth/is-admin", headers=account).status_code == 401
    assert db.sessions.count_documents({}) == 1


def test_bulk_workbook_partial_errors(client, account):
    import openpyxl
    api, db = client
    db.users.update_one({"email": "alice@example.com"}, {"$set": {"is_admin": True}})
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(['name', 'description', 'price', 'category', 'image'])
    sheet.append(['Shirt', 'Cotton shirt', 499, 'men', 'shirt.png'])
    sheet.append(['Bad price', 'Cotton shirt', -1, 'men', 'shirt.png'])
    sheet.append(['Fraction', 'Cotton shirt', 1.5, 'men', 'shirt.png'])
    sheet.append(['Invalid category', 'Cotton shirt', 499, 'unknown', 'shirt.png'])
    excel = io.BytesIO(); workbook.save(excel)
    image = io.BytesIO(); Image.new('RGB', (2, 2)).save(image, format='PNG')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as images: images.writestr('shirt.png', image.getvalue())
    response = api.post('/products/bulk-upload', files={
        'excel_file': ('products.xlsx', excel.getvalue()),
        'images_zip': ('images.zip', archive.getvalue()),
    }, headers=account)
    assert response.status_code == 200, response.text
    assert response.json()['inserted'] == 1
    assert response.json()['failed'] == 3
    assert db.products.count_documents({}) == 1


def test_admin_product_round_trip_and_negative_price(client, account):
    api, db = client
    db.users.update_one({'email': 'alice@example.com'}, {'$set': {'is_admin': True}})
    image = io.BytesIO(); Image.new('RGB', (2, 2)).save(image, format='PNG')
    data = {'name': 'Shirt', 'description': 'Cotton', 'price': '123', 'category': 'men'}
    files = {'image': ('shirt.png', image.getvalue(), 'image/png')}
    assert api.post('/products', data={**data, 'price': '-1'}, files=files, headers=account).status_code == 422
    assert api.post('/products', data=data, files=files, headers=account).status_code == 200
    product = api.get('/products').json()[0]
    assert 'image_data' not in product
    assert api.get(product['image']).headers['content-type'] == 'image/png'
    assert api.put('/products/' + product['id'], data={'price': '456'}, headers=account).status_code == 200
    assert api.get('/products/' + product['id']).json()['price'] == 456
    assert api.delete('/products/' + product['id'], headers=account).status_code == 200
    assert api.get('/products/' + product['id']).status_code == 404


def test_google_verified_login_creates_real_session(client, monkeypatch):
    from backend.routes import google_auth
    api, db = client
    monkeypatch.setattr(google_auth, 'GOOGLE_CLIENT_ID', 'test-client-id')
    monkeypatch.setattr(google_auth.google_id_token, 'verify_oauth2_token', lambda credential, request, audience: {'email_verified': True, 'email': 'google@example.com', 'name': 'Google User'})
    response = api.post('/auth/google', json={'credential': 'signed-token-placeholder'})
    assert response.status_code == 200
    token = response.json()['access_token']
    assert api.get('/auth/profile?email=google@example.com', headers={'Authorization': 'Bearer ' + token}).status_code == 200
    assert db.users.find_one()['auth_provider'] == 'google'
    monkeypatch.setattr(google_auth.google_id_token, 'verify_oauth2_token', lambda *args: {'email_verified': False, 'email': 'other@example.com'})
    assert api.post('/auth/google', json={'credential': 'unverified-token'}).status_code == 401


def test_deleted_account_cannot_reuse_session(client, account):
    api, db = client
    response = api.request('DELETE', '/auth/account', json={'email': 'alice@example.com', 'password': 'StrongPass123!'}, headers=account)
    assert response.status_code == 200
    assert db.users.count_documents({}) == 0
    assert db.sessions.count_documents({}) == 0
    assert api.get('/auth/is-admin', headers=account).status_code == 401
