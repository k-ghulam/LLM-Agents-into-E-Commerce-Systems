import { loadWishlist } from "../services/wishlist.js";
import {
  renderProductCard,
  wireProductCards,
} from "../components/ProductCard.js";
import { state } from "../services/state.js";
import { currentRoute } from "../services/nav.js";
import { escapeHtml } from "../utils/escapeHtml.js";
export async function renderWishlist() {
  const app = document.getElementById("app");
  app.innerHTML = '<div class="container loading">Opening your edit…</div>';
  try {
    const products = await loadWishlist(true);
    if (currentRoute().path !== "/wishlist") return;
    app.innerHTML = `<section class="catalog container"><p class="eyebrow">PIECES TO COME BACK TO</p><h1 class="catalog-heading">Your personal edit.</h1><p class="wishlist-note">${state.isLoggedIn ? "Saved to your account, ready whenever you are." : "Saved on this browser. Account wishlists are separate and sync when you sign in."}</p>${products.length ? `<div class="products-grid wishlist-grid">${products.map(renderProductCard).join("")}</div>` : '<div class="empty-state"><h2>A little space for your favourites.</h2><p>Tap the heart on a piece you love to save it here.</p><a class="btn btn-primary" href="#/">Discover the collection</a></div>'}</section>`;
    wireProductCards(app, products, renderWishlist);
  } catch (error) {
    if (currentRoute().path !== "/wishlist") return;
    app.innerHTML = `<div class="container empty-state"><h1>Your edit couldn’t load.</h1><p>${escapeHtml(error.message)}</p><a href="#/profile" class="btn btn-primary">Open your account</a></div>`;
  }
}
