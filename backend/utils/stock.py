"""Catalog availability only; demo orders never reserve or decrement stock."""
from fastapi import HTTPException


def public_stock(product):
    quantity = product.get("stock_quantity")
    product["availability"] = ("unknown" if quantity is None else "in_stock" if type(quantity) is int and quantity > 0 else "out_of_stock")
    return product


def check_demo_stock(product, quantity):
    stock = product.get("stock_quantity")
    if stock is not None and (type(stock) is not int or stock < quantity):
        raise HTTPException(409, "Requested quantity exceeds the recorded stock. Refresh the product.")
