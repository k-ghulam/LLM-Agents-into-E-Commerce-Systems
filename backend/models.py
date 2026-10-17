"""
Pydantic request/response models.

Two groups:
  - Catalog & commerce: Product (bulk-JSON shape), Order, CartItem
  - Accounts: UserRegister, UserLogin, ProfileUpdate, AccountDelete, GoogleAuth

Note on images: single-product create/update (`POST`/`PUT /products`) is
multipart and does not use a model — the image is uploaded and stored as base64.
`Product` below is only the JSON bulk-add shape, where `image` is a URL string.
"""
from typing import List, Optional
from .utils.money import EuroAmount

from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_validator


# --------------------------------------------------------------------------- #
# Catalog & commerce
# --------------------------------------------------------------------------- #

class Product(BaseModel):
    """One product in a `POST /products/bulk` JSON payload (image is a URL)."""
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    price: EuroAmount = Field(ge=0)
    category: str = Field(pattern="^(men|women|kids)$")
    size: List[str]        # e.g. ["S", "M", "L", "XL"]
    color: List[str]       # e.g. ["Black", "Blue"]
    image: HttpUrl             # image URL


class Order(BaseModel):
    """Order placement payload."""
    user_email: EmailStr
    product_name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=100)
    price: EuroAmount = Field(default=0, ge=0)   # compatibility only; server selects price


class CartItem(BaseModel):
    """Add-to-cart payload."""
    user_email: EmailStr
    product_name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=100)


# --------------------------------------------------------------------------- #
# Accounts
# --------------------------------------------------------------------------- #

class UserRegister(BaseModel):
    """Registration payload: plaintext password is hashed before storage."""
    username: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 10 or len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at least 10 characters and at most 72 UTF-8 bytes")
        return value


class UserLogin(BaseModel):
    """Login payload: email or username, plus password."""
    identifier: str
    password: str = Field(min_length=1, max_length=200)


class ProfileUpdate(BaseModel):
    """Edit-profile payload — current_password re-verifies identity before any change."""
    current_email: str
    current_password: str
    new_username: Optional[str] = None
    new_email: Optional[str] = None
    new_password: Optional[str] = None


class AccountDelete(BaseModel):
    """Payload to permanently delete an account."""
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class GoogleAuth(BaseModel):
    """Google Sign-In payload: the ID-token JWT from Google Identity Services."""
    credential: str = Field(min_length=1, max_length=10000)
