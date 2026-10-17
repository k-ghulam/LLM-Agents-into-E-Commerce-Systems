"""
Single-product routes: add, list, get one, update, delete. Bulk ingestion
(JSON bulk-add and the Excel + images-zip upload) lives in products_bulk.py.
"""
import base64
from typing import Optional, Literal

import logfire
from fastapi import APIRouter, Response, UploadFile, File, Form, HTTPException, Depends, Query
from bson import ObjectId
from bson.errors import InvalidId

from ..database import products_collection
from ..utils.stock import public_stock
from ..utils.mongo import case_insensitive_contains
from ..utils.money import EuroAmount, cents, public_money
from ..auth import require_admin
from ..utils.images import encode_upload_to_base64, resolve_image_field
from ..utils.mongo import case_insensitive_exact, price_range_filter

# Split so the read replica / write replica of the deployment can each mount only
# the half it serves. The monolith (main.py) mounts both.
read_router = APIRouter(prefix="/products", tags=["Products"])
write_router = APIRouter(prefix="/products", tags=["Products"])


def _object_id(raw: str) -> ObjectId:
    """Parse a product id from the URL, or raise 400 if it is not a valid ObjectId."""
    try:
        return ObjectId(raw)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Invalid product ID")


def _public_product(product: dict) -> dict:
    """Shape a raw MongoDB product document for an API response (in place)."""
    product["id"] = str(product["_id"])
    product.pop("_id", None)
    resolve_image_field(product)
    return public_stock(public_money(product))


@write_router.post("")
async def add_product(
    name: str = Form(..., min_length=1, max_length=200),
    description: str = Form(..., min_length=1, max_length=4000),
    price: EuroAmount = Form(..., ge=0),
    stock_quantity: int = Form(-1, ge=-1, le=1000000),
    category: str = Form(..., pattern="^(men|women|kids)$"),
    size: str = Form("M,L"),
    color: str = Form("Black"),
    image: UploadFile = File(...),
    admin_email: str = Depends(require_admin),
):
    """
    Add a new product to the store with an image upload.
    The image is stored as base64 string in MongoDB.
    """
    base64_image, content_type = await encode_upload_to_base64(image)

    product = {
        "name": name,
        "description": description,
        "price_cents": cents(price),
        "currency": "EUR",
        "stock_quantity": None if stock_quantity == -1 else stock_quantity,
        "category": category,
        "size": size.split(","),
        "color": color.split(","),
        "image_data": base64_image,
        "image_content_type": content_type,
    }
    products_collection.insert_one(product)
    return {"message": "Product added successfully"}


@read_router.get("")
def get_products(category: str = "", min_price: Optional[EuroAmount] = None, max_price: Optional[EuroAmount] = None):
    """
    Get products with optional category, min_price, and max_price filters.
    """
    products = []
    query = {"category": case_insensitive_exact(category)} if category else {}

    price_query = price_range_filter(min_price, max_price)
    if price_query:
        query.update(price_query)

    for product in products_collection.find(query):
        products.append(_public_product(product))
    return products


@read_router.get("/search")
def search_catalog(
    q: str = Query("", max_length=120),
    category: Literal["", "men", "women", "kids"] = "",
    min_price: Optional[EuroAmount] = None,
    max_price: Optional[EuroAmount] = None,
    size: str = Query("", max_length=40),
    color: str = Query("", max_length=60),
    in_stock: bool = False,
    sort: Literal["newest", "price_asc", "price_desc", "name"] = "newest",
    page: int = Query(1, ge=1, le=10000),
    limit: int = Query(12, ge=1, le=48),
):
    """Paginated storefront search; original /products remains compatible."""
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, "Minimum price must not exceed maximum price")
    clauses = []
    if category:
        clauses.append({"category": case_insensitive_exact(category)})
    if q.strip():
        pattern = case_insensitive_contains(q.strip())
        clauses.append({"$or": [{"name": pattern}, {"description": pattern}]})
    if bounds := price_range_filter(min_price, max_price):
        clauses.append(bounds)
    for field, value in (("size", size), ("color", color)):
        if value.strip():
            clauses.append({field: case_insensitive_exact(value.strip())})
    if in_stock:
        clauses.append({"stock_quantity": {"$gt": 0}})
    query = {"$and": clauses} if clauses else {}
    order = {"newest": {"_id": -1}, "price_asc": {"_sort_price": 1, "_id": 1},
             "price_desc": {"_sort_price": -1, "_id": 1}, "name": {"_sort_name": 1, "_id": 1}}[sort]
    pipeline = [{"$match": query}, {"$addFields": {
        "_sort_price": {"$ifNull": ["$price_cents", {"$multiply": ["$price", 100]}]},
        "_sort_name": {"$toLower": "$name"}}},
        {"$sort": order}, {"$skip": (page - 1) * limit}, {"$limit": limit},
        {"$project": {"_sort_price": 0, "_sort_name": 0}}]
    total = products_collection.count_documents(query)
    return {"items": [_public_product(product) for product in products_collection.aggregate(pipeline)],
            "total": total, "page": page, "limit": limit, "has_more": page * limit < total}


@read_router.get("/{id}")
def get_product(id: str):
    """Get a single product by its ID."""
    product = products_collection.find_one({"_id": _object_id(id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _public_product(product)


@read_router.get("/{id}/image")
def get_product_image(id: str):
    """
    Stream a product's stored image directly, so product list/detail
    responses can link to this instead of embedding the base64 bytes inline.
    """
    product = products_collection.find_one(
        {"_id": _object_id(id)}, {"image_data": 1, "image_content_type": 1}
    )
    if not product or not product.get("image_data"):
        raise HTTPException(status_code=404, detail="Image not found")
    image_bytes = base64.b64decode(product["image_data"])
    return Response(
        content=image_bytes,
        media_type=product.get("image_content_type") or "image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@write_router.delete("")
def delete_all_products(admin_email: str = Depends(require_admin)):
    """
    Delete all products from the store.
    """
    result = products_collection.delete_many({})
    logfire.warn(
        "Admin wiped the entire product catalog: {count} products deleted by {admin}",
        count=result.deleted_count,
        admin=admin_email,
    )
    return {"message": f"{result.deleted_count} products deleted"}


@write_router.delete("/{id}")
def delete_product(id: str, admin_email: str = Depends(require_admin)):
    """Delete a specific product by its ID."""
    result = products_collection.delete_one({"_id": _object_id(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Deleted successfully"}


@write_router.put("/{id}")
async def update_product(
    id: str,
    name: str = Form(None, min_length=1, max_length=200),
    description: str = Form(None, min_length=1, max_length=4000),
    price: EuroAmount = Form(None, ge=0),
    stock_quantity: Optional[int] = Form(None, ge=-1, le=1000000),
    category: str = Form(None, pattern="^(men|women|kids)$"),
    size: str = Form(None),
    color: str = Form(None),
    image: UploadFile = File(None),
    admin_email: str = Depends(require_admin),
):
    """
    Update an existing product. Send the fields to change as multipart/form-data
    (the same encoding as `POST /products`); only the fields present are modified.
    """
    object_id = _object_id(id)

    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if price is not None:
        update_data["price_cents"] = cents(price)
        update_data["currency"] = "EUR"
    if stock_quantity is not None:
        update_data["stock_quantity"] = None if stock_quantity == -1 else stock_quantity
    if category is not None:
        update_data["category"] = category
    if size is not None:
        update_data["size"] = size.split(",")
    if color is not None:
        update_data["color"] = color.split(",")
    if image:
        base64_image, content_type = await encode_upload_to_base64(image)
        update_data["image_data"] = base64_image
        update_data["image_content_type"] = content_type

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = products_collection.update_one({"_id": object_id}, {"$set": update_data, **({"$unset": {"price": ""}} if price is not None else {})})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product updated successfully"}
