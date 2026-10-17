import { renderHero } from "../components/Hero.js";
import {
  renderProductCard,
  wireProductCards,
} from "../components/ProductCard.js";
import { loadWishlist } from "../services/wishlist.js";
import { request } from "../services/api/http.js";
import { currentRoute, navigate } from "../services/nav.js";
import { state } from "../services/state.js";
import { escapeHtml } from "../utils/escapeHtml.js";
import { icon } from "../utils/icons.js";
let renderVersion = 0;
export async function renderHome() {
  const version = ++renderVersion,
    route = currentRoute(),
    params = route.params,
    routeHash = window.location.hash;
  state.currentCategory = params.get("cat") || "";
  const selectedCategory = ["men", "women", "kids"].includes(
    state.currentCategory,
  )
    ? state.currentCategory
    : "";
  const app = document.getElementById("app");
  app.innerHTML = `${params.size ? "" : renderHero()}<section class="catalog container" aria-busy="true"><p class="eyebrow">THE COLLECTION</p><h1 class="catalog-heading">Finding your next favourite…</h1><div class="skeleton-grid">${Array(4).fill('<div class="skeleton-card"></div>').join("")}</div></section>`;
  const query = new URLSearchParams();
  for (const [from, to] of [
    ["q", "q"],
    ["cat", "category"],
    ["min", "min_price"],
    ["max", "max_price"],
    ["size", "size"],
    ["color", "color"],
    ["sort", "sort"],
    ["page", "page"],
    ["in_stock", "in_stock"],
  ])
    if (params.get(from)) query.set(to, params.get(from));
  let catalog;
  try {
    [catalog] = await Promise.all([
      request("/products/search?" + query),
      loadWishlist().catch(() => []),
    ]);
  } catch (error) {
    if (version !== renderVersion || currentRoute().path !== "/") return;
    app.innerHTML = `<div class="container empty-state"><p class="eyebrow">A LITTLE INTERRUPTION</p><h1>We couldn’t load the collection.</h1><p>${escapeHtml(error.message)}</p><button class="btn btn-primary" id="retryCatalog">Try again</button></div>`;
    document.getElementById("retryCatalog").onclick = renderHome;
    return;
  }
  if (
    version !== renderVersion ||
    window.location.hash !== routeHash ||
    currentRoute().path !== "/"
  )
    return;
  state.products = catalog.items;
  const heading = params.get("q")
    ? "Results for “" + params.get("q") + "”"
    : selectedCategory
      ? {
          men: "The menswear edit",
          women: "The womenswear edit",
          kids: "For their little adventures",
        }[selectedCategory]
      : "Find your everyday favourites.";
  const headingTag = params.size ? "h1" : "h2";
  const active = [...params].filter(([key]) => !["page", "sort"].includes(key));
  app.innerHTML = `${params.size ? "" : renderHero()}<section class="catalog container" id="collection"><div class="catalog-intro"><div><p class="eyebrow">CURATED BY YOU</p><${headingTag} class="catalog-heading">${escapeHtml(heading)}</${headingTag}></div><p class="catalog-count">${catalog.total} ${catalog.total === 1 ? "piece" : "pieces"} to discover</p></div><div class="catalog-layout"><aside class="catalog-filters"><form id="filterForm"><div class="filter-title">Make it yours <button type="button" id="resetFilters" class="text-link">Reset</button></div><label for="filterCategory">Collection</label><select id="filterCategory" name="cat">${[
    ["", "All collections"],
    ["women", "Women"],
    ["men", "Men"],
    ["kids", "Kids"],
  ]
    .map(
      ([value, label]) =>
        `<option value="${value}" ${value === selectedCategory ? "selected" : ""}>${label}</option>`,
    )
    .join(
      "",
    )}</select><label>Price range (€)</label><div class="price-inputs"><input name="min" type="number" min="0" max="1000000" step="0.01" placeholder="From" aria-label="Minimum price in euros" value="${escapeHtml(params.get("min") || "")}"/><span>—</span><input name="max" type="number" min="0" max="1000000" step="0.01" placeholder="To" aria-label="Maximum price in euros" value="${escapeHtml(params.get("max") || "")}"/></div><label for="filterSize">Size</label><select name="size" id="filterSize"><option value="">All sizes</option>${["XS", "S", "M", "L", "XL", "XXL"].map((size) => `<option ${size === params.get("size") ? "selected" : ""}>${size}</option>`).join("")}</select><label for="filterColor">Colour</label><input name="color" id="filterColor" maxlength="60" placeholder="For example, Black" value="${escapeHtml(params.get("color") || "")}"/><label class="stock-check"><input type="checkbox" name="in_stock" value="true" ${params.get("in_stock") === "true" ? "checked" : ""}/> Confirmed in stock only</label><button class="btn btn-primary" type="submit">Apply filters ${icon("arrow")}</button></form><div class="filter-note"><span class="eyebrow">NEED A LITTLE INSPIRATION?</span><p>Ask the shopping assistant to find a piece by style, category or budget.</p><button id="askStylist" class="text-link">Ask the assistant ${icon("arrow")}</button></div></aside><div class="catalog-results"><div class="catalog-toolbar"><span>${active.length ? `<button class="filter-clear" id="clearResults">Clear filters ${icon("close")}</button>` : "Considered pieces. Your own style."}</span><label for="catalogSort" class="sr-only">Sort products</label><select id="catalogSort">${[
    ["newest", "Recently added"],
    ["price_asc", "Price: low to high"],
    ["price_desc", "Price: high to low"],
    ["name", "Name: A–Z"],
  ]
    .map(
      ([value, label]) =>
        `<option value="${value}" ${value === (params.get("sort") || "newest") ? "selected" : ""}>${label}</option>`,
    )
    .join(
      "",
    )}</select></div>${catalog.items.length ? `<div class="products-grid">${catalog.items.map(renderProductCard).join("")}</div>` : `<div class="empty-state"><span class="empty-symbol">${icon("search")}</span><h2>A fresh search, perhaps?</h2><p>No pieces match these filters. Try another price, size or keyword.</p><a class="btn btn-primary" href="#/">Explore the collection</a></div>`}<nav class="pagination" aria-label="Catalog pages"><button class="btn btn-outline" id="prevPage" ${catalog.page <= 1 ? "disabled" : ""}>← Previous</button><span>Page ${catalog.page}${catalog.total ? " of " + Math.ceil(catalog.total / catalog.limit) : ""}</span><button class="btn btn-outline" id="nextPage" ${!catalog.has_more ? "disabled" : ""}>Next →</button></nav></div></div></section><section class="brand-note container"><p class="eyebrow">THE KOOSHKWEAR WAY</p><h2>Good style starts<br>with feeling like yourself.</h2><p>Explore at your pace. Save what catches your eye.<br>Make your everyday a little more you.</p><a class="text-link" href="#/wishlist">Start your edit ${icon("arrow")}</a></section>`;
  wireProductCards(app, catalog.items);
  const change = (key, value) => {
    const next = new URLSearchParams(params);
    next.delete("page");
    value ? next.set(key, value) : next.delete(key);
    navigate("#/?" + next);
  };
  document.getElementById("filterForm").onsubmit = (event) => {
    event.preventDefault();
    const next = new URLSearchParams(params);
    next.delete("page");
    for (const key of ["cat", "min", "max", "size", "color", "in_stock"])
      next.delete(key);
    for (const [key, value] of new FormData(event.currentTarget))
      if (String(value).trim()) next.set(key, String(value).trim());
    navigate(next.size ? "#/?" + next : "#/");
  };
  document.getElementById("catalogSort").onchange = (event) =>
    change("sort", event.target.value);
  document.getElementById("resetFilters").onclick = () => navigate("#/");
  document
    .getElementById("clearResults")
    ?.addEventListener("click", () => navigate("#/"));
  for (const [id, page] of [
    ["prevPage", catalog.page - 1],
    ["nextPage", catalog.page + 1],
  ])
    document.getElementById(id).onclick = () => {
      const next = new URLSearchParams(params);
      next.set("page", page);
      navigate("#/?" + next);
    };
  document.getElementById("askStylist").onclick = () => {
    if (!state.chatOpen) document.getElementById("chatToggle")?.click();
    document.getElementById("chatInput")?.focus();
  };
}
