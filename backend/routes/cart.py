"""
Shopping cart routes: add an item, list a user's items, clear the cart.
"""


from fastapi import APIRouter, Depends, HTTPException
from ..auth import current_user, require_owner
from ..models import CartItem
from ..database import cart_collection, products_collection


# Split so the read replica / write replica of the deployment can each mount only
# the half it serves. The monolith (main.py) mounts both.
read_router = APIRouter(prefix="/cart", tags=["Cart"])
write_router = APIRouter(prefix="/cart", tags=["Cart"])


@write_router.post("/add")
def add_to_cart(item: CartItem, user: dict = Depends(current_user)):
    """
    Add an item to the user's shopping cart. If the same product is already in
    the cart, its quantity is increased instead of adding a duplicate row.
    """
    email = require_owner(item.user_email, user)
    matches = list(products_collection.find({"name": item.product_name}).limit(2))
    if len(matches) != 1:
        raise HTTPException(409, "Product is missing or its name is ambiguous")
    cart_collection.update_one(
        {"user_email": email, "product_name": item.product_name},
        {"$inc": {"quantity": item.quantity}}, upsert=True,
    )
    return {"message": "Item added to cart"}


@read_router.get("/{user_email}")
def get_cart(user_email: str, user: dict = Depends(current_user)):
    """
    Get all shopping cart items for a specific user.
    """
    user_email = require_owner(user_email, user)
    items = list(cart_collection.find({"user_email": user_email}, {"_id": 0}))
    return items


@write_router.delete("/{user_email}")
def clear_cart(user_email: str, user: dict = Depends(current_user)):
    """
    Clear all shopping cart items for a specific user after checkout.
    """
    user_email = require_owner(user_email, user)
    cart_collection.delete_many({"user_email": user_email})
    return {"message": "Cart cleared successfully"}
