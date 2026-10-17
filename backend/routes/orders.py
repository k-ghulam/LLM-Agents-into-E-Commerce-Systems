"""
Order management routes for placing new orders and viewing order history.
"""
from datetime import datetime, timezone

import logfire
from fastapi import APIRouter, Depends, HTTPException
from ..auth import current_user, require_owner
from ..models import Order
from ..database import orders_collection, products_collection

# Split so the read replica / write replica of the deployment can each mount only
# the half it serves. The monolith (main.py) mounts both.
read_router = APIRouter(prefix="/orders", tags=["Orders"])
write_router = APIRouter(prefix="/orders", tags=["Orders"])

@write_router.post("")
def place_order(order: Order, user: dict = Depends(current_user)):
    """
    Place a new order for a user.
    """
    email = require_owner(order.user_email, user)
    matches = list(products_collection.find({"name": order.product_name}).limit(2))
    if len(matches) != 1:
        raise HTTPException(409, "Product is missing or its name is ambiguous")
    product = matches[0]
    if not isinstance(product.get("price"), int) or product["price"] < 0:
        raise HTTPException(409, "Invalid catalog price")
    order_data = order.model_dump()
    order_data.update(user_email=email, price=product["price"], product_id=str(product["_id"]))
    order_data["created_at"] = datetime.now(timezone.utc).isoformat()
    orders_collection.insert_one(order_data)
    logfire.info(
        "Order placed: {quantity}x {product} @ {price} by {user}",
        quantity=order.quantity,
        product=order.product_name,
        price=product["price"],
        user=order.user_email,
    )
    return {"message": "Order placed successfully"}


@read_router.get("/{user_email}")
def get_order_history(user_email: str, user: dict = Depends(current_user)):
    """
    Get a user's past orders, most recent first.
    """
    user_email = require_owner(user_email, user)
    orders = list(
        orders_collection.find({"user_email": user_email}, {"_id": 0}).sort("created_at", -1)
    )
    return orders
