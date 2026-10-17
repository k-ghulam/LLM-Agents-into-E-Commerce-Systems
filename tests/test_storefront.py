from bson import ObjectId


def test_catalog_search_combines_filters_and_exact_prices(client):
    api, db = client
    db.products.insert_many([
        {'name': 'Linen Shirt', 'description': 'Soft natural fabric', 'price': 20, 'category': 'women', 'size': ['M'], 'color': ['Black'], 'stock_quantity': 3},
        {'name': 'Linen Dress', 'description': 'Natural fabric', 'price_cents': 1999, 'currency': 'EUR', 'category': 'women', 'size': ['S'], 'color': ['Black'], 'stock_quantity': 2},
        {'name': 'Linen Shirt', 'description': 'Cotton', 'price': 10, 'category': 'men', 'size': ['M'], 'color': ['White'], 'stock_quantity': 0},
        {'name': 'Unknown stock', 'description': 'Linen blend', 'price': 35, 'category': 'women'}])
    result = api.get('/products/search?q=linen&category=women&min_price=19.99&max_price=20&color=black&sort=price_asc').json()
    assert result['total'] == 2
    assert [p['price'] for p in result['items']] == ['19.99', '20.00']
    assert api.get('/products/search?size=m&category=women').json()['total'] == 1
    assert api.get('/products/search?in_stock=true').json()['total'] == 2
    assert api.get('/products/search?q=.*').json()['total'] == 0
    assert api.get('/products/search?q=natural').json()['total'] == 2


def test_search_pagination_validation_and_ties(client):
    api, db = client
    db.products.insert_many([{'name': 'Piece', 'price': 20, 'category': 'men'} for _ in range(3)])
    one = api.get('/products/search?limit=2&page=1&sort=price_desc').json()
    two = api.get('/products/search?limit=2&page=2&sort=price_desc').json()
    assert one['total'] == 3 and one['has_more'] and not two['has_more']
    assert len({p['id'] for p in one['items'] + two['items']}) == 3
    for query in ['page=0', 'limit=49', 'sort=untrusted', 'category=anything', 'min_price=5&max_price=4', 'min_price=NaN', 'q=' + 'a'*121]:
        assert api.get('/products/search?' + query).status_code == 422
    assert api.get('/products/search?q=missing').json()['items'] == []


def test_wishlist_private_idempotent_and_deleted_products(client, account):
    api, db = client
    product_id = str(db.products.insert_one({'name': 'Shirt', 'price': 25}).inserted_id)
    assert api.get('/wishlist').status_code == 401
    assert api.put('/wishlist/' + product_id).status_code == 401
    assert api.put('/wishlist/' + product_id, headers=account).status_code == 200
    assert api.put('/wishlist/' + product_id, headers=account).status_code == 200
    assert len(api.get('/wishlist', headers=account).json()) == 1
    response = api.post('/auth/register', json={'username':'bob','email':'bob@example.com','password':'StrongPass123!'})
    other = {'Authorization': 'Bearer ' + response.json()['access_token']}
    assert api.get('/wishlist', headers=other).json() == []
    assert api.delete('/wishlist/' + product_id, headers=other).status_code == 200
    assert len(api.get('/wishlist', headers=account).json()) == 1
    db.products.delete_one({'_id': ObjectId(product_id)})
    assert api.get('/wishlist', headers=account).json() == []
    assert api.delete('/wishlist/' + product_id, headers=account).status_code == 200
    assert api.put('/wishlist/' + 'f'*24, headers=account).status_code == 404
    assert api.put('/wishlist/not-an-id', headers=account).status_code == 400


def test_wishlist_cap_and_account_deletion(client, account):
    api, db = client
    user = db.users.find_one({'email':'alice@example.com'})
    ids = [str(ObjectId()) for _ in range(200)]
    db.wishlist.insert_one({'user_id':user['_id'], 'product_ids':ids})
    new = str(db.products.insert_one({'name':'New','price':10}).inserted_id)
    assert api.put('/wishlist/' + new, headers=account).status_code == 409
    assert len(db.wishlist.find_one()['product_ids']) == 200
    assert api.delete('/wishlist/' + ids[0], headers=account).status_code == 200
    assert api.put('/wishlist/' + new, headers=account).status_code == 200
    response = api.request('DELETE','/auth/account',json={'email':'alice@example.com','password':'StrongPass123!'},headers=account)
    assert response.status_code == 200, response.text
    assert db.wishlist.count_documents({}) == 0


def test_stock_and_preview_orders(client, account):
    api, db = client
    db.products.insert_one({'name':'Limited','price_cents':1999,'stock_quantity':2})
    payload = {'user_email':'alice@example.com','product_name':'Limited','quantity':3}
    assert api.post('/cart/add',json=payload,headers=account).status_code == 409
    assert api.post('/orders',json=payload,headers=account).status_code == 409
    payload['quantity'] = 2
    assert api.post('/orders',json=payload,headers=account).status_code == 200
    assert db.products.find_one()['stock_quantity'] == 2
    order = db.orders.find_one()
    assert order['payment_status'] == 'not_charged' and order['order_kind'] == 'demo'
    assert api.get('/config').json()['payments_enabled'] is False
    assert api.post('/checkout',headers=account).status_code == 503
    assert api.post('/checkout').status_code == 401
    assert db.orders.count_documents({}) == 1


def test_stock_admin_json_and_update(client, account):
    api, db = client
    db.users.update_one({'email':'alice@example.com'}, {'$set':{'is_admin':True}})
    base={'name':'Shirt','description':'Cotton','price':'19.99','category':'men','size':['M'],'color':['Black'],'image':'https://example.com/image.jpg'}
    for invalid in [-1, 1.5, True, '5', 1000001]:
        assert api.post('/products/bulk',json=[{**base,'stock_quantity':invalid}],headers=account).status_code == 422
    assert api.post('/products/bulk',json=[{**base,'stock_quantity':0}],headers=account).status_code == 200
    product = api.get('/products').json()[0]
    assert product['availability'] == 'out_of_stock'
    assert api.put('/products/'+product['id'],data={'stock_quantity':'5'},headers=account).status_code == 200
    assert api.get('/products/'+product['id']).json()['availability'] == 'in_stock'
    assert api.put('/products/'+product['id'],data={'stock_quantity':'-1'},headers=account).status_code == 200
    assert api.get('/products/'+product['id']).json()['availability'] == 'unknown'


def test_cart_quantity_and_removal_ownership(client, account):
    api, db = client
    db.products.insert_one({'name':'Shirt','price':20,'stock_quantity':5})
    payload={'user_email':'alice@example.com','product_name':'Shirt','quantity':1}
    assert api.post('/cart/add',json=payload,headers=account).status_code == 200
    assert api.put('/cart/item',json={**payload,'quantity':3},headers=account).status_code == 200
    assert db.cart.find_one()['quantity'] == 3
    assert api.put('/cart/item',json={**payload,'quantity':6},headers=account).status_code == 409
    assert api.put('/cart/item',json={**payload,'user_email':'bob@example.com'},headers=account).status_code == 403
    assert api.delete('/cart/item?product_name=Shirt').status_code == 401
    assert api.delete('/cart/item?product_name=Shirt',headers=account).status_code == 200
    assert db.cart.count_documents({}) == 0


def test_concurrent_cart_change_cannot_bypass_stock(client, account, monkeypatch):
    api, db = client
    db.products.insert_one({'name':'Shirt','price':20,'stock_quantity':5})
    db.cart.insert_one({'user_email':'alice@example.com','product_name':'Shirt','quantity':4})
    original = db.cart.update_one
    raced = False
    def interleave(query, update, **kwargs):
        nonlocal raced
        if not raced:
            raced = True
            original({'product_name':'Shirt'},{'$inc':{'quantity':1}})
        return original(query, update, **kwargs)
    monkeypatch.setattr(db.cart, 'update_one', interleave)
    response=api.post('/cart/add',json={'user_email':'alice@example.com','product_name':'Shirt','quantity':1},headers=account)
    assert response.status_code == 409
    assert db.cart.find_one()['quantity'] == 5


def test_excel_stock_is_optional_and_validated(client, account):
    import io, zipfile, openpyxl
    from PIL import Image
    api, db = client
    db.users.update_one({'email':'alice@example.com'}, {'$set':{'is_admin':True}})
    workbook=openpyxl.Workbook();sheet=workbook.active
    sheet.append(['name','description','price','category','image','stock_quantity'])
    sheet.append(['Known','Cotton',19.99,'men','shirt.png',5])
    sheet.append(['Unknown','Cotton',25,'women','shirt.png',None])
    sheet.append(['Negative','Cotton',25,'women','shirt.png',-1])
    sheet.append(['Fraction','Cotton',25,'women','shirt.png',1.5])
    excel=io.BytesIO();workbook.save(excel)
    image=io.BytesIO();Image.new('RGB',(2,2)).save(image,format='PNG')
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as z:z.writestr('shirt.png',image.getvalue())
    response=api.post('/products/bulk-upload',files={'excel_file':('stock.xlsx',excel.getvalue()),'images_zip':('images.zip',archive.getvalue())},headers=account)
    assert response.status_code == 200, response.text
    assert response.json()['inserted'] == 2 and response.json()['failed'] == 2
    assert db.products.find_one({'name':'Known'})['stock_quantity'] == 5
    assert db.products.find_one({'name':'Unknown'})['stock_quantity'] is None
