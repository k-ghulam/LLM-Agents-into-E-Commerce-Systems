"""Private account wishlists keyed by immutable user ID, capped at 200 IDs."""
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError
from ..auth import current_user
from ..database import wishlist_collection, products_collection
from .products import _object_id, _public_product

read_router = APIRouter(prefix="/wishlist", tags=["Wishlist"])
write_router = APIRouter(prefix="/wishlist", tags=["Wishlist"])

@read_router.get("")
def get_wishlist(user: dict = Depends(current_user)):
    saved = wishlist_collection.find_one({"user_id": user["_id"]}) or {}
    ids = [_object_id(value) for value in saved.get("product_ids", [])[:200]]
    return [_public_product(product) for product in products_collection.find({"_id": {"$in": ids}})]

@write_router.put("/{product_id}")
def save_product(product_id: str, user: dict = Depends(current_user)):
    object_id = _object_id(product_id)
    if not products_collection.find_one({"_id": object_id}, {"_id": 1}):
        raise HTTPException(404, "Product not found")
    product_id = str(object_id)
    try:
        wishlist_collection.update_one({"user_id": user["_id"]}, {"$setOnInsert": {"product_ids": []}}, upsert=True)
    except DuplicateKeyError:
        pass  # A concurrent first save already created this user's document.
    result = wishlist_collection.update_one({"user_id": user["_id"], "$or": [
        {"product_ids": product_id}, {"product_ids.199": {"$exists": False}}]},
        {"$addToSet": {"product_ids": product_id}})
    if not result.matched_count:
        raise HTTPException(409, "Your wishlist is full (200 products)")
    return {"saved": True}

@write_router.delete("/{product_id}")
def remove_product(product_id: str, user: dict = Depends(current_user)):
    product_id = str(_object_id(product_id))
    wishlist_collection.update_one({"user_id": user["_id"]}, {"$pull": {"product_ids": product_id}})
    return {"saved": False}
