import { renderWishlist } from "./pages/Wishlist.js";
import { renderHelp } from "./pages/Help.js";
import { renderHome } from "./pages/Home.js";
import { renderAdmin } from "./pages/Admin.js";
import { renderProductDetail } from "./pages/ProductDetail.js";
import { renderCart } from "./pages/Cart.js";
import { renderProfile } from "./pages/Profile.js";
import { mountHeader } from "./components/Header.js";
import { state, resetTransientUi } from "./services/state.js";
import { navigate, currentRoute } from "./services/nav.js";

let lastPath = null;

export async function router() {
  const { path } = currentRoute();

  // Reset per-page UI toggles whenever the page itself changes (not on an
  // in-page re-render such as a filter change, which keeps the same path).
  if (path !== lastPath) {
    resetTransientUi();
    lastPath = path;
  }

  mountHeader();

  if (path === "/add-products" || path === "/admin") {
    if (!state.isAdmin) {
      alert("Admins only.");
      navigate("#/");
      return;
    }
    await renderAdmin();
  } else if (path === "/wishlist") {
    await renderWishlist();
  } else if (path === "/help") {
    renderHelp();
  } else if (path === "/cart") {
    await renderCart();
  } else if (path === "/profile") {
    await renderProfile();
  } else if (path.startsWith("/product/")) {
    await renderProductDetail(path.split("/")[2]);
  } else if (path === "/") {
    await renderHome();
  } else {
    document.getElementById("app").innerHTML =
      '<div class="container empty-state"><h1>This page isn’t in the collection.</h1><a class="btn btn-primary" href="#/">Back to KooshkWear</a></div>';
  }
}
