import { formatEUR, priceCents } from "../utils/money.js";
import { loadWishlist, isSaved, toggleSaved } from "../services/wishlist.js";
import { icon, notify } from "../utils/icons.js";
import { currentRoute } from "../services/nav.js";
import { state } from "../services/state.js";
import { fetchProduct, placeOrder } from "../services/api_v2.js";
import { handleAddToCartClick } from "../services/cartActions.js";
import { navigate } from "../services/nav.js";
import { escapeHtml } from "../utils/escapeHtml.js";
import { PLACEHOLDER_IMAGE } from "../utils/placeholder.js";

export async function renderProductDetail(id) {
  const app = document.getElementById("app");
  app.innerHTML = `<div class="loading">Loading…</div>`;

  let product;
  try {
    [product] = await Promise.all([
      fetchProduct(id),
      loadWishlist().catch(() => []),
    ]);
    if (currentRoute().path !== `/product/${id}`) return;
  } catch (err) {
    if (currentRoute().path !== `/product/${id}`) return;
    console.error("Failed to load product:", err);
    app.innerHTML = `
      <div class="product-detail">
        <button class="back-btn" id="backBtn">← Back to Products</button>
        <div class="empty-state">
          <p>Sorry, we couldn't find that product.</p>
          <a href="#/" class="btn btn-primary">Browse all products</a>
        </div>
      </div>`;
    document
      .getElementById("backBtn")
      ?.addEventListener("click", () => navigate("#/"));
    return;
  }

  const sizes = Array.isArray(product.size) ? product.size : [];
  const colors = Array.isArray(product.color) ? product.color : [];

  app.innerHTML = `
    <div class="product-detail">
      <button class="back-btn" id="backBtn">← Back to Products</button>
      <div class="product-detail-grid">
        <div class="product-detail-image">
          <img src="${escapeHtml(product.image || PLACEHOLDER_IMAGE)}" alt="${escapeHtml(product.name)}" loading="lazy" />
        </div>
        <div class="product-detail-info">
          <span class="product-detail-category">${escapeHtml(product.category)}</span>
          <h1>${escapeHtml(product.name)}</h1>
          <p class="product-detail-price">${formatEUR(priceCents(product))}</p>
          <p class="availability ${escapeHtml(product.availability || "unknown")}">${product.availability === "in_stock" ? "Recorded in stock" : product.availability === "out_of_stock" ? "Currently out of stock" : "Availability not yet confirmed"}</p>
          <p class="product-detail-desc">${escapeHtml(product.description)}</p>
          ${
            sizes.length
              ? `
            <div class="option-group">
              <h3 class="option-label">Sizes in this listing:</h3>
              <div class="option-values">
                ${sizes.map((s) => `<span class="option-value">${escapeHtml(s)}</span>`).join("")}
              </div>
            </div>`
              : ""
          }
          ${
            colors.length
              ? `
            <div class="option-group">
              <h3 class="option-label">Colours in this listing:</h3>
              <div class="option-values">
                ${colors.map((c) => `<span class="option-value">${escapeHtml(c)}</span>`).join("")}
              </div>
            </div>`
              : ""
          }
          <div class="detail-actions">
            <button class="detail-btn detail-btn-primary" id="btnAddToCart" ${product.availability === "out_of_stock" ? "disabled" : ""}>Add to bag</button>
            <button class="detail-btn detail-btn-secondary" id="btnBuyNow" ${product.availability === "out_of_stock" ? "disabled" : ""}>Place Demo Order</button>
          </div>
          <button class="detail-save ${isSaved(product.id) ? "is-saved" : ""}" id="detailSave" aria-pressed="${isSaved(product.id)}">${icon("heart")} Save to your favourites</button>
          <p class="detail-note">Preview store. Demo orders do not charge money or reserve stock. Sizes and colours above describe this listing; variant selection is not yet available.</p>
          <details class="detail-info-panel"><summary>About this piece</summary><p>${escapeHtml(product.description)}</p></details>
          <details class="detail-info-panel"><summary>Delivery, payment &amp; returns</summary><p>Real checkout and delivery are not enabled. Seller details, final delivery costs and return terms will be published before real purchases open.</p><a class="text-link" href="#/help">Read the store guide →</a></details>
        </div>
      </div>
    </div>
  `;

  document
    .getElementById("backBtn")
    ?.addEventListener("click", () => navigate("#/"));
  document
    .getElementById("detailSave")
    ?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      try {
        const saved = await toggleSaved(product);
        button.classList.toggle("is-saved", saved);
        button.setAttribute("aria-pressed", String(saved));
        notify(
          saved ? "Saved to your favourites" : "Removed from your favourites",
        );
      } catch (error) {
        notify(error.message);
      } finally {
        button.disabled = false;
      }
    });

  document.getElementById("btnAddToCart")?.addEventListener("click", (e) => {
    handleAddToCartClick(e.target, product.name, {
      onSuccess: () => {
        if (currentRoute().path === `/product/${id}`) renderProductDetail(id);
      },
      delay: 1500,
    });
  });

  document.getElementById("btnBuyNow")?.addEventListener("click", async (e) => {
    if (!state.isLoggedIn) {
      navigate("#/profile");
      return;
    }
    e.target.disabled = true;
    e.target.textContent = "Processing...";
    try {
      await placeOrder(state.sessionId, product.name, 1, product.price);
      e.target.textContent = "Demo Order Recorded";
      setTimeout(() => navigate("#/"), 2000);
    } catch (err) {
      console.error(err);
      alert(`Failed to place order: ${err.message}`);
      e.target.disabled = false;
      e.target.textContent = "Place Demo Order";
    }
  });
}
