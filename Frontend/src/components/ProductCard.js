import { escapeHtml } from "../utils/escapeHtml.js";
import { formatEUR, priceCents } from "../utils/money.js";
import { icon, notify } from "../utils/icons.js";
import { isSaved, toggleSaved } from "../services/wishlist.js";
import { handleAddToCartClick } from "../services/cartActions.js";
export function renderProductCard(p) {
  const id = escapeHtml(p.id),
    saved = isSaved(p.id);
  return `<article class="product-card"><div class="product-image"><a href="#/product/${id}" aria-label="View ${escapeHtml(p.name)}">${p.image ? `<img src="${escapeHtml(p.image)}" alt="${escapeHtml(p.name)}" loading="lazy"/>` : '<span class="product-placeholder">KOOSHKWEAR<br>Image coming soon</span>'}</a><button class="save-product ${saved ? "is-saved" : ""}" data-save="${id}" aria-label="${saved ? "Remove from" : "Save to"} wishlist: ${escapeHtml(p.name)}" aria-pressed="${saved}">${icon("heart")}</button>${p.availability === "out_of_stock" ? '<span class="product-status">Out of stock</span>' : ""}</div><div class="product-info"><span class="product-category">${escapeHtml(p.category)} / THE EDIT</span><a class="product-name" href="#/product/${id}">${escapeHtml(p.name)}</a><div class="product-card-meta"><span class="product-price">${formatEUR(priceCents(p))}</span><span class="product-sizes">${escapeHtml((p.size || []).join(" · "))}</span></div><button class="add-to-cart-btn" data-add="${id}" ${p.availability === "out_of_stock" ? "disabled" : ""}>${p.availability === "out_of_stock" ? "Unavailable" : "Add to bag"} ${icon("bag")}</button></div></article>`;
}
export function wireProductCards(host, products, onChange) {
  host.querySelectorAll("[data-save]").forEach((button) =>
    button.addEventListener("click", async () => {
      button.disabled = true;
      const product = products.find((p) => p.id === button.dataset.save);
      try {
        const saved = await toggleSaved(product);
        button.classList.toggle("is-saved", saved);
        button.setAttribute("aria-pressed", String(saved));
        button.setAttribute(
          "aria-label",
          `${saved ? "Remove from" : "Save to"} wishlist: ${product.name}`,
        );
        notify(
          saved ? "Saved to your favourites" : "Removed from your favourites",
        );
        if (onChange) onChange();
      } catch (error) {
        notify(error.message);
      } finally {
        button.disabled = false;
      }
    }),
  );
  host.querySelectorAll("[data-add]").forEach((button) =>
    button.addEventListener("click", () => {
      const product = products.find((p) => p.id === button.dataset.add);
      handleAddToCartClick(button, product.name, {
        onSuccess: () => {
          button.disabled = false;
          button.innerHTML = "Add to bag " + icon("bag");
        },
        delay: 1000,
      });
    }),
  );
}
