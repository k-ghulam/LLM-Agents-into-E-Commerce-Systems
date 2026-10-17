import { state } from "../services/state.js";
import { navigate, currentRoute } from "../services/nav.js";
import { escapeHtml } from "../utils/escapeHtml.js";
import { icon } from "../utils/icons.js";
export function renderHeader() {
  const { params, path } = currentRoute();
  return `<div class="announcement">THE KOOSHKWEAR EDIT <span>Explore the collection · Preview store · Payments coming later</span></div>
  <header class="header"><div class="container header-inner">
    <button class="icon-btn menu-btn" id="menuToggle" aria-label="Open navigation" aria-expanded="false" aria-controls="mainNav">${icon("menu")}</button>
    <a class="header-logo" href="#/" aria-label="KooshkWear home">Kooshk<span>Wear</span><small>THE EVERYDAY, RECONSIDERED.</small></a>
    <form class="header-search" id="catalogSearch" role="search"><label class="sr-only" for="headerQuery">Search the collection</label>${icon("search")}<input id="headerQuery" name="q" type="search" maxlength="120" placeholder="Find your next favourite…" value="${escapeHtml(params.get("q") || "")}"/><button type="submit" aria-label="Search">${icon("arrow")}</button></form>
    <div class="header-right">${state.isAdmin ? '<a href="#/admin" class="admin-link">Studio</a>' : ""}
    <a class="icon-btn" href="#/wishlist" aria-label="Wishlist">${icon("heart")}</a>
    <a class="icon-btn" href="#/profile" aria-label="${state.isLoggedIn ? "Your account" : "Sign in"}">${icon("user")}</a>
    <a class="icon-btn relative" href="#/cart" aria-label="Shopping bag">${icon("bag")}${state.cartItemCount ? `<span class="cart-badge">${state.cartItemCount}</span>` : ""}</a></div>
  </div><nav class="collection-nav container" id="mainNav" aria-label="Collections">${[
    ["", "Discover"],
    ["women", "Women"],
    ["men", "Men"],
    ["kids", "Kids"],
  ]
    .map(
      ([value, label]) =>
        `<a class="nav-link ${path === "/" && (params.get("cat") || "") === value ? "active" : ""}" href="#/${value ? "?cat=" + value : ""}">${label}</a>`,
    )
    .join(
      "",
    )}<a class="nav-link" href="#/wishlist">Your favourites</a><a class="nav-link nav-assistant" href="#/help">The KooshkWear guide ${icon("arrow")}</a></nav></header>`;
}
export function mountHeader() {
  const host = document.getElementById("site-header");
  if (!host) return;
  host.innerHTML = renderHeader();
  host.querySelector("#catalogSearch")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const q = host.querySelector("#headerQuery").value.trim();
    navigate(q ? "#/?q=" + encodeURIComponent(q) : "#/");
  });
  host.querySelector("#menuToggle")?.addEventListener("click", (event) => {
    const opened = host.querySelector(".header").classList.toggle("nav-open");
    event.currentTarget.setAttribute("aria-expanded", String(opened));
  });
}
