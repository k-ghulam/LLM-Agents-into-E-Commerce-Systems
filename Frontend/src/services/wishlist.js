import { state } from "./state.js";
import { request } from "./api/http.js";
import { fetchProduct } from "./api/products.js";
let identity = null,
  products = [],
  loaded = false;
const GUEST_KEY = "kooshkwear_guest_wishlist_v1";
function ensureIdentity() {
  const next = state.isLoggedIn ? state.sessionId : "guest";
  if (identity !== next) {
    identity = next;
    products = [];
    loaded = false;
  }
}
export function isSaved(id) {
  ensureIdentity();
  return products.some((p) => p.id === id);
}
export async function loadWishlist(force = false) {
  ensureIdentity();
  if (loaded && !force) return products;
  const owner = identity;
  let result;
  if (state.isLoggedIn) result = await request("/wishlist");
  else {
    let ids;
    try {
      ids = JSON.parse(localStorage.getItem(GUEST_KEY) || "[]");
    } catch {
      ids = [];
    }
    ids = Array.isArray(ids)
      ? ids
          .filter((id) => typeof id === "string" && /^[a-f0-9]{24}$/.test(id))
          .slice(0, 200)
      : [];
    result = [];
    for (let i = 0; i < ids.length; i += 6) {
      const batch = await Promise.allSettled(
        ids.slice(i, i + 6).map(fetchProduct),
      );
      result.push(
        ...batch.filter((r) => r.status === "fulfilled").map((r) => r.value),
      );
    }
  }
  ensureIdentity();
  if (identity !== owner) return products;
  products = result;
  loaded = true;
  return products;
}
export async function toggleSaved(product) {
  ensureIdentity();
  const saved = isSaved(product.id),
    owner = identity;
  if (!saved && products.length >= 200)
    throw new Error("Your wishlist is full (200 products).");
  if (state.isLoggedIn)
    await request(`/wishlist/${encodeURIComponent(product.id)}`, {
      method: saved ? "DELETE" : "PUT",
      write: true,
    });
  ensureIdentity();
  if (identity !== owner) return false;
  const next = saved
    ? products.filter((p) => p.id !== product.id)
    : [...products, product];
  if (!state.isLoggedIn)
    localStorage.setItem(GUEST_KEY, JSON.stringify(next.map((p) => p.id)));
  products = next;
  loaded = true;
  window.dispatchEvent(new Event("wishlist-changed"));
  return !saved;
}
