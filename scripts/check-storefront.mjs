// Unit-level module tests. These do not replace real browser/layout validation.
import assert from "node:assert/strict";
import vm from "node:vm";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../Frontend/src/", import.meta.url));
const store = () => {
  const entries = new Map();
  return {
    getItem: (key) => entries.get(key) ?? null,
    setItem: (key, value) => entries.set(key, String(value)),
    removeItem: (key) => entries.delete(key),
  };
};
const app = { innerHTML: "", querySelectorAll: () => [] };
const nodes = new Map([["app", app]]);
const products = [
  {
    id: "a".repeat(24),
    name: "Linen Shirt",
    price_cents: 1999,
    currency: "EUR",
    category: "women",
    size: ["M"],
    image: "",
  },
];
const accountLists = new Map();
let delayed = null;
const context = vm.createContext({
  console,
  URL,
  URLSearchParams,
  Response,
  AbortController,
  FormData,
  Event,
  localStorage: store(),
  sessionStorage: store(),
  setTimeout: () => 0,
  clearTimeout: () => {},
  window: { location: { hash: "#/" }, dispatchEvent: () => {} },
  document: {
    getElementById: (id) => {
      if (!nodes.has(id)) nodes.set(id, { addEventListener: () => {} });
      return nodes.get(id);
    },
    querySelectorAll: () => [],
  },
  fetch: async (path, options = {}) => {
    if (path.includes("/products/search")) {
      if (delayed) {
        const fn = delayed;
        delayed = null;
        return fn();
      }
      return Response.json({
        items: products,
        total: 1,
        page: 1,
        limit: 12,
        has_more: false,
      });
    }
    if (path.startsWith("/products/")) return Response.json(products[0]);
    if (path.startsWith("/auth/logout")) return Response.json({});
    const key = options.headers?.Authorization || "none";
    const list = accountLists.get(key) || [];
    if (path === "/wishlist") return Response.json(list);
    if (path.startsWith("/wishlist/")) {
      accountLists.set(key, options.method === "DELETE" ? [] : products);
      return Response.json({ saved: options.method !== "DELETE" });
    }
    throw new Error("Unexpected test request: " + path);
  },
});
const modules = new Map();
async function getModule(filename) {
  filename = resolve(filename);
  if (!filename.startsWith(root)) throw new Error("Import outside frontend");
  if (!modules.has(filename))
    modules.set(
      filename,
      readFile(filename, "utf8").then(
        (source) =>
          new vm.SourceTextModule(source, { context, identifier: filename }),
      ),
    );
  return modules.get(filename);
}
async function evaluate(name) {
  const module = await getModule(resolve(root, name));
  if (module.status === "unlinked")
    await module.link((specifier, parent) =>
      getModule(resolve(dirname(parent.identifier), specifier)),
    );
  if (module.status !== "evaluated") await module.evaluate();
  return module.namespace;
}
const wishlist = await evaluate("services/wishlist.js");
const { state, login, logout } = await evaluate("services/state.js");
await wishlist.loadWishlist();
assert.equal(wishlist.isSaved(products[0].id), false);
await wishlist.toggleSaved(products[0]);
assert.equal(wishlist.isSaved(products[0].id), true);
login("a@example.test", "A", "token-a");
await wishlist.loadWishlist();
assert.equal(wishlist.isSaved(products[0].id), false);
await wishlist.toggleSaved(products[0]);
assert.equal(wishlist.isSaved(products[0].id), true);
login("b@example.test", "B", "token-b");
await wishlist.loadWishlist();
assert.equal(wishlist.isSaved(products[0].id), false);
logout();
await wishlist.loadWishlist();
assert.equal(wishlist.isSaved(products[0].id), true); // guest edit is separate
const { renderHome } = await evaluate("pages/Home.js");
let finishOld;
delayed = () =>
  new Promise((resolve) => {
    finishOld = resolve;
  });
const old = renderHome();
await new Promise((resolve) => setImmediate(resolve));
context.window.location.hash = "#/?q=linen";
await renderHome();
const latest = app.innerHTML;
assert.match(latest, /Results for/);
assert.match(latest, /Linen Shirt/);
finishOld(
  Response.json({ items: [], total: 0, page: 1, limit: 12, has_more: false }),
);
await old;
assert.equal(
  app.innerHTML,
  latest,
  "A stale catalog response must not replace the current route",
);
context.window.location.hash = "#/?q=%3Cscript%3E";
await renderHome();
assert.ok(app.innerHTML.includes("&lt;script&gt;"));
assert.ok(!app.innerHTML.includes("Results for “<script>"));
assert.equal(state.isLoggedIn, false);
console.log(
  "Storefront module tests passed: wishlist identity isolation, persistence, stale response protection and escaped search text.",
);
