"""
Shopping cart routes: add an item, list a user's items, clear the cart.
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import DuplicateKeyError
from ..auth import current_user, require_owner
from ..models import CartItem
from ..utils.stock import check_demo_stock
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
    key = {"user_email": email, "product_name": item.product_name}
    for _ in range(3):
        existing = cart_collection.find_one(key)
        previous = (existing or {}).get("quantity", 0)
        total = previous + item.quantity
        if total > 100:
            raise HTTPException(409, "At most 100 units of a product are allowed in a demo cart")
        check_demo_stock(matches[0], total)
        if existing:
            result = cart_collection.update_one({**key, "quantity": previous}, {"$inc": {"quantity": item.quantity}})
            if result.matched_count:
                return {"message": "Item added to cart"}
        else:
            try:
                cart_collection.insert_one({**key, "quantity": item.quantity})
                return {"message": "Item added to cart"}
            except DuplicateKeyError:
                continue
    raise HTTPException(409, "Your cart changed while adding this item. Refresh and try again.")



@write_router.put("/item")
def set_cart_quantity(item: CartItem, user: dict = Depends(current_user)):
    email = require_owner(item.user_email, user)
    products = list(products_collection.find({"name": item.product_name}).limit(2))
    if len(products) != 1:
        raise HTTPException(409, "Product is missing or its name is ambiguous")
    check_demo_stock(products[0], item.quantity)
    result = cart_collection.update_one({"user_email": email, "product_name": item.product_name},
                                        {"$set": {"quantity": item.quantity}})
    if not result.matched_count:
        raise HTTPException(404, "Cart item not found")
    return {"quantity": item.quantity}


@write_router.delete("/item")
def remove_cart_item(product_name: str = Query(..., min_length=1, max_length=200), user: dict = Depends(current_user)):
    cart_collection.delete_one({"user_email": user["email"], "product_name": product_name})
    return {"message": "Item removed"}


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
