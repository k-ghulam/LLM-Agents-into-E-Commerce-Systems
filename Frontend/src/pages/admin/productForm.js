import { parseEUR } from "../../utils/money.js";
import { state, resetAdminForm } from "../../services/state.js";
import { addProduct, updateProduct } from "../../services/api_v2.js";
import { escapeHtml } from "../../utils/escapeHtml.js";

/**
 * The add/edit product form card.
 */
export function renderProductForm() {
  const colorValue = Array.isArray(state.adminForm.color)
    ? state.adminForm.color.join(", ")
    : state.adminForm.color || "";
  return `
    <div class="admin-form">
      <h2 class="admin-form-title">${state.isEditing ? "Edit Product" : "Add New Product"}</h2>
      <div class="form-grid">
        <input placeholder="Name" class="form-input" id="adminName" value="${escapeHtml(state.adminForm.name)}" />
        <input placeholder="Description" class="form-input" id="adminDesc" value="${escapeHtml(state.adminForm.description)}" />
        <input placeholder="Price" type="number" min="0" step="0.01" class="form-input" id="adminPrice" value="${escapeHtml(state.adminForm.price ?? "")}" />

        <div class="form-col-span"><label class="form-label" for="adminStock">Recorded stock (optional)</label><input id="adminStock" class="form-input" type="number" min="0" max="1000000" step="1" value="${escapeHtml(state.adminForm.stock_quantity ?? "")}" placeholder="Blank = availability not confirmed"/><p class="muted">Product-level count only. Demo orders do not reserve or reduce this quantity. Size/colour inventory is not yet supported.</p></div>
        <div class="form-col-span">
          <label class="form-label">Category:</label>
          <div class="category-buttons" id="adminCategoryButtons">
            ${["men", "women", "kids"]
              .map(
                (cat) => `
              <button class="category-btn ${state.adminForm.category === cat ? "active" : ""}" data-cat="${cat}">${cat.charAt(0).toUpperCase() + cat.slice(1)}</button>
            `,
              )
              .join("")}
          </div>
        </div>

        <div class="form-col-span">
          <label class="form-label">${state.isEditing ? "Change Image (optional):" : "Product Image:"}</label>
          <input type="file" accept="image/png, image/jpeg, image/jpg" id="adminImage" class="form-input full-width" />
          ${state.adminForm.image && !state.imageFile ? `<p class="muted" style="margin-top: 0.5rem;">Current image: ${escapeHtml(state.adminForm.image)}</p>` : ""}
        </div>

        <div class="form-col-span">
          <label class="form-label">Select Sizes:</label>
          <div class="checkbox-group">
            ${["S", "M", "L", "XL", "XXL"]
              .map(
                (size) => `
              <label class="checkbox-label">
                <input type="checkbox" ${state.adminForm.size?.includes(size) ? "checked" : ""} data-size="${size}" />
                <span>${size}</span>
              </label>
            `,
              )
              .join("")}
          </div>
        </div>

        <div class="form-col-span">
          <label class="form-label">Color:</label>
          <input placeholder="Enter color (e.g., Black, Blue, Red)" class="form-input full-width" id="adminColor" value="${escapeHtml(colorValue)}" />
        </div>
      </div>

      <div class="form-actions">
        ${
          state.isEditing
            ? `
          <button id="updateProductBtn" class="btn btn-blue">Update Product</button>
          <button id="cancelEditBtn" class="btn btn-outline">Cancel</button>
        `
            : `
          <button id="addProductBtn" class="btn btn-success">Add Product</button>
        `
        }
      </div>
    </div>
  `;
}

export function setupProductFormEvents(rerender) {
  // Preserve edits when category selection redraws the form.
  for (const [id, field] of [
    ["adminName", "name"],
    ["adminDesc", "description"],
    ["adminPrice", "price"],
    ["adminColor", "color"],
    ["adminStock", "stock_quantity"],
  ]) {
    document.getElementById(id)?.addEventListener("input", (event) => {
      state.adminForm[field] =
        field === "price"
          ? event.target.value
          : field === "color"
            ? event.target.value.split(",").map((value) => value.trim())
            : event.target.value;
    });
  }
  document.querySelectorAll("[data-cat]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.adminForm.category = btn.dataset.cat;
      rerender();
    });
  });

  document.querySelectorAll("[data-size]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const size = cb.dataset.size;
      const currentSizes = state.adminForm.size || [];
      if (cb.checked) {
        state.adminForm.size = [...currentSizes, size];
      } else {
        state.adminForm.size = currentSizes.filter((s) => s !== size);
      }
    });
  });

  document.getElementById("adminImage")?.addEventListener("change", (e) => {
    state.imageFile = e.target.files?.[0] || null;
  });

  document
    .getElementById("addProductBtn")
    ?.addEventListener("click", () => handleAddProduct(rerender));
  document
    .getElementById("updateProductBtn")
    ?.addEventListener("click", () => handleUpdateProduct(rerender));
  document.getElementById("cancelEditBtn")?.addEventListener("click", () => {
    resetAdminForm();
    rerender();
  });
}

/**
 * Prepopulate the form for editing an existing product.
 */
export function editProduct(product, rerender) {
  state.isEditing = true;
  state.editId = product.id;
  state.imageFile = null;
  const colorValue = product.color
    ? typeof product.color === "string"
      ? product.color.split(",").map((c) => c.trim())
      : product.color
    : [];
  state.adminForm = {
    name: product.name,
    description: product.description,
    price: product.price,
    stock_quantity: product.stock_quantity,
    category: product.category,
    image: product.image,
    size: product.size || [],
    color: colorValue,
  };
  rerender();
}

/**
 * Read the form inputs back into state.adminForm and validate. Returns true when
 * the form is ready to submit, false (after alerting) when a field is missing.
 */
function collectAdminForm() {
  const adminForm = state.adminForm;
  adminForm.name = document.getElementById("adminName").value.trim();
  adminForm.description = document.getElementById("adminDesc").value.trim();
  adminForm.price = document.getElementById("adminPrice").value.trim();
  const stock = document.getElementById("adminStock").value.trim();
  if (stock !== "" && (!/^\d+$/.test(stock) || Number(stock) > 1000000)) {
    alert("Stock must be a whole number from 0 to 1000000, or blank.");
    return false;
  }
  adminForm.stock_quantity = stock === "" ? -1 : Number(stock);
  adminForm.color = document
    .getElementById("adminColor")
    .value.split(",")
    .map((c) => c.trim())
    .filter(Boolean);
  // category is already set on state by the category buttons

  if (
    !adminForm.name ||
    !adminForm.description ||
    parseEUR(adminForm.price) === null ||
    !adminForm.category
  ) {
    alert("Please fill in all fields");
    return false;
  }
  return true;
}

/**
 * Build the multipart body for POST/PUT /products. The endpoint is
 * form-data only, so the image (when picked) and every field go in here.
 */
function buildProductFormData() {
  const { name, description, price, category, size, color } = state.adminForm;
  const formData = new FormData();
  formData.append("name", name);
  formData.append("description", description);
  formData.append("price", String(price));
  formData.append(
    "stock_quantity",
    String(state.adminForm.stock_quantity ?? -1),
  );
  formData.append("category", category);
  formData.append("size", size?.join(",") || "M,L");
  formData.append("color", color?.join(", ") || "Black");
  if (state.imageFile) formData.append("image", state.imageFile);
  return formData;
}

async function handleAddProduct(rerender) {
  if (!collectAdminForm()) return;
  try {
    await addProduct(buildProductFormData());
  } catch (err) {
    alert(`Failed to add product: ${err.message}`);
    return;
  }
  alert("Product added ✅");
  resetAdminForm();
  rerender();
}

async function handleUpdateProduct(rerender) {
  if (!collectAdminForm()) return;
  try {
    await updateProduct(state.editId, buildProductFormData());
  } catch (err) {
    alert(`Failed to update product: ${err.message}`);
    return;
  }
  alert("Product updated ✅");
  resetAdminForm();
  rerender();
}
