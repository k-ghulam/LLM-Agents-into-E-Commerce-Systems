import { setCartQuantity, removeCartItem } from "../services/api/cart.js";
import { currentRoute } from "../services/nav.js";
import { invalidateProductsCache } from "../services/api/products.js";
import { notify } from "../utils/icons.js";
import { formatEUR, priceCents } from "../utils/money.js";
import { state } from "../services/state.js";
import {
  getCart,
  placeOrder,
  clearCart,
  fetchProducts,
} from "../services/api_v2.js";
import { setCartCount } from "../services/cartCount.js";
import { escapeHtml } from "../utils/escapeHtml.js";
import { PLACEHOLDER_IMAGE } from "../utils/placeholder.js";

export async function renderCart() {
  if (!state.isLoggedIn) {
    window.location.hash = "#/profile";
    return;
  }
  document.getElementById("app").innerHTML = `
    <div class="container page page-lg">
      <p class="eyebrow">YOUR EVERYDAY EDIT</p><h1 class="page-title">Your shopping bag.</h1><p class="preview-notice">Preview store — only demo orders can be recorded. No payment is collected, no inventory is reserved and no delivery is arranged.</p>
      <div id="cartContent"><p>Loading cart...</p></div>
    </div>
  `;
  const contentDiv = document.getElementById("cartContent");

  let cartItems;
  try {
    // The cart only stores product names + quantities; join against the catalog
    // for prices and images.
    invalidateProductsCache();
    const [rawCartItems, productsDB] = await Promise.all([
      getCart(state.sessionId),
      fetchProducts(),
    ]);
    if (currentRoute().path !== "/cart") return;
    cartItems = rawCartItems.map((item) => {
      const match = productsDB.find((p) => p.name === item.product_name) || {};
      return {
        ...item,
        price: match.price,
        price_cents:
          match.price_cents ?? (match.price != null ? priceCents(match) : 0),
        unavailable: !match.id || match.availability === "out_of_stock",
        image: match.image || PLACEHOLDER_IMAGE,
      };
    });
  } catch (err) {
    console.error("Failed to load cart:", err);
    contentDiv.innerHTML = `<div class="empty-state"><p>Couldn't load your cart. Please try again.</p></div>`;
    return;
  }

  if (!cartItems.length) {
    contentDiv.innerHTML = `
      <div class="cart-empty">
        <div style="font-size: 4rem; margin-bottom: 1rem;">🛒</div>
        <h2 style="font-size: 1.5rem; color: #4b5563; margin-bottom: 1rem;">Your cart is empty!</h2>
        <a href="#/" class="btn btn-primary">Continue Shopping</a>
      </div>
    `;
    setCartCount(0);
    return;
  }

  const total = cartItems.reduce(
    (sum, item) => sum + priceCents(item) * item.quantity,
    0,
  );
  setCartCount(cartItems.reduce((sum, item) => sum + (item.quantity || 0), 0));

  contentDiv.innerHTML = `
    <div class="card">
      <div class="list-stack">
        ${cartItems.map(renderCartItem).join("")}
      </div>
      <div class="cart-total-row">
        <h2 style="font-size: 1.5rem; font-weight: bold;">Catalog Total (Demo):</h2>
        <span style="font-size: 1.5rem; font-weight: bold; color: #111827;">${formatEUR(total)}</span>
      </div>
      <div class="cart-actions">
        <a href="#/" class="btn btn-outline" style="flex: 1; text-align: center;">Keep Shopping</a>
        <button id="clearCartBtn" class="btn btn-outline btn-danger-outline" style="flex: 1;">Clear bag</button>
        <button id="buyAllBtn" class="btn btn-primary" style="flex: 2;" ${cartItems.some((item) => item.unavailable) ? "disabled" : ""}>Place Demo Orders</button>
      </div>
    </div>
  `;

  wireCartItems(cartItems);
  wireClearCart();
  wireBuyAll(cartItems);
}

function renderCartItem(item) {
  return `
    <div class="cart-item">
      <img class="cart-item-img" src="${escapeHtml(item.image)}" alt="${escapeHtml(item.product_name)}" loading="lazy" />
      <div class="cart-item-info">
        <h3 style="font-weight: bold; font-size: 1.1rem; color: #111827;">${escapeHtml(item.product_name)}</h3>
        ${item.unavailable ? '<p class="muted">This item is unavailable. Remove it to continue.</p>' : ""}
        <div class="qty-controls"><button data-quantity="${escapeHtml(item.product_name)}" data-next="${item.quantity - 1}" ${item.quantity <= 1 ? "disabled" : ""} aria-label="Decrease quantity for ${escapeHtml(item.product_name)}">−</button><span aria-label="Quantity">${escapeHtml(item.quantity)}</span><button data-quantity="${escapeHtml(item.product_name)}" data-next="${item.quantity + 1}" ${item.quantity >= 100 || item.unavailable ? "disabled" : ""} aria-label="Increase quantity for ${escapeHtml(item.product_name)}">+</button><button class="remove-cart-item" data-remove="${escapeHtml(item.product_name)}">Remove</button></div>
      </div>
      <div class="price-lg">${item.unavailable ? "Unavailable" : formatEUR(priceCents(item))}</div>
    </div>`;
}

function wireCartItems() {
  document
    .querySelectorAll("[data-quantity], [data-remove]")
    .forEach((button) =>
      button.addEventListener("click", async () => {
        document
          .querySelectorAll(
            "[data-quantity], [data-remove], #buyAllBtn, #clearCartBtn",
          )
          .forEach((control) => (control.disabled = true));
        try {
          if (button.dataset.remove)
            await removeCartItem(button.dataset.remove);
          else
            await setCartQuantity(
              state.sessionId,
              button.dataset.quantity,
              Number(button.dataset.next),
            );
        } catch (error) {
          notify(error.message);
        }
        if (currentRoute().path === "/cart") await renderCart();
      }),
    );
}

function wireClearCart() {
  document
    .getElementById("clearCartBtn")
    ?.addEventListener("click", async (e) => {
      if (!confirm("Are you sure you want to clear your cart?")) return;
      const btn = e.target.closest("button");
      btn.disabled = true;
      btn.textContent = "Clearing... ⏳";
      try {
        await clearCart(state.sessionId);
        setCartCount(0);
        renderCart();
      } catch (err) {
        alert(`Failed to clear cart: ${err.message}`);
        btn.disabled = false;
        btn.textContent = "Clear bag";
      }
    });
}

function wireBuyAll(cartItems) {
  document.getElementById("buyAllBtn")?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    btn.disabled = true;
    btn.textContent = "Recording demo order…";
    try {
      await Promise.all(
        cartItems.map((item) =>
          placeOrder(
            state.sessionId,
            item.product_name,
            item.quantity,
            item.price,
          ),
        ),
      );
      await clearCart(state.sessionId);
      setCartCount(0);
      btn.textContent = "Demo Orders Recorded";
      btn.classList.add("btn-success");
      setTimeout(() => {
        window.location.hash = "#/";
      }, 2000);
    } catch (err) {
      alert(`Failed to place the order: ${err.message}`);
      btn.disabled = false;
      btn.textContent = "Place Demo Orders";
    }
  });
}
