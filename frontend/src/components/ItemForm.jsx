/**
 * ItemForm - Simple single-screen form for creating/editing items
 *
 * Replaces the complex ItemWizard with a clean, focused form.
 * BOM and Routing are managed separately via dedicated editors.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { API_URL } from "../config/api";
import {
  validateRequired,
  validatePrice,
  validateSKU,
  validateForm,
  hasErrors,
} from "../utils/validation";
import { FormErrorSummary, RequiredIndicator } from "./ErrorMessage";
import Modal from "./Modal";
import Input from "./ui/Input";
import Select from "./ui/Select";
import Button from "./ui/Button";

const ITEM_TYPES = [
  { value: "finished_good", label: "Finished Good" },
  { value: "component", label: "Component" },
  { value: "supply", label: "Supply" },
  { value: "service", label: "Service" },
  { value: "material", label: "Material (Filament)" },
];

const PROCUREMENT_TYPES = [
  { value: "make", label: "Make (Manufactured)" },
  { value: "buy", label: "Buy (Purchased)" },
  { value: "make_or_buy", label: "Make or Buy" },
];

const STOCKING_POLICIES = [
  { value: "on_demand", label: "On-Demand (MRP-driven)" },
  { value: "stocked", label: "Stocked (Reorder Point)" },
];

export default function ItemForm({
  isOpen,
  onClose,
  onSuccess,
  editingItem = null,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [errors, setErrors] = useState({});
  const [categories, setCategories] = useState([]);
  const [uomClasses, setUomClasses] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const [formData, setFormData] = useState({
    sku: editingItem?.sku || "",
    name: editingItem?.name || "",
    description: editingItem?.description || "",
    item_type: editingItem?.item_type || "finished_good",
    procurement_type: editingItem?.procurement_type || "make",
    stocking_policy: editingItem?.stocking_policy || "on_demand",
    category_id: editingItem?.category_id || null,
    unit: editingItem?.unit || "EA",
    standard_cost: editingItem?.standard_cost || "",
    selling_price: editingItem?.selling_price || "",
    reorder_point: editingItem?.reorder_point || "",
    image_url: editingItem?.image_url || "",
  });

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/items/categories`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setCategories(data);
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error("ItemForm: fetchCategories failed", {
          endpoint: `${API_URL}/api/v1/items/categories`,
          message: err?.message,
          stack: err?.stack,
        });
      }
    }
  }, []);

  const fetchUomClasses = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/uom/classes`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setUomClasses(data);
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error("ItemForm: fetchUomClasses failed", {
          endpoint: `${API_URL}/api/v1/admin/uom/classes`,
          message: err?.message,
          stack: err?.stack,
        });
      }
      setUomClasses([]);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchCategories();
      fetchUomClasses();
      if (editingItem) {
        setFormData({
          sku: editingItem.sku || "",
          name: editingItem.name || "",
          description: editingItem.description || "",
          item_type: editingItem.item_type || "finished_good",
          procurement_type: editingItem.procurement_type || "make",
          stocking_policy: editingItem.stocking_policy || "on_demand",
          category_id: editingItem.category_id || null,
          unit: editingItem.unit || "EA",
          standard_cost: editingItem.standard_cost || "",
          selling_price: editingItem.selling_price || "",
          reorder_point: editingItem.reorder_point || "",
          image_url: editingItem.image_url || "",
        });
      } else {
        setFormData({
          sku: "",
          name: "",
          description: "",
          item_type: "finished_good",
          procurement_type: "make",
          stocking_policy: "on_demand",
          category_id: null,
          unit: "EA",
          standard_cost: "",
          selling_price: "",
          reorder_point: "",
          image_url: "",
        });
      }
      setError(null);
      setErrors({});
    }
  }, [isOpen, editingItem, fetchCategories, fetchUomClasses]);

  useEffect(() => {
    if (formData.item_type === 'material' && !editingItem) {
      setFormData(prev => ({
        ...prev,
        unit: 'G',
        procurement_type: 'buy',
      }));
    }
  }, [formData.item_type, editingItem]);

  const validateFormData = () => {
    const validationRules = {
      name: [(v) => validateRequired(v, "Item name")],
      unit: [(v) => validateRequired(v, "Unit of measure")],
      item_type: [(v) => validateRequired(v, "Item type")],
      procurement_type: [(v) => validateRequired(v, "Procurement type")],
    };

    if (formData.sku && formData.sku.trim()) {
      validationRules.sku = [(v) => validateSKU(v)];
    }

    if (formData.standard_cost !== "" && formData.standard_cost !== null) {
      validationRules.standard_cost = [
        (v) => validatePrice(v, "Standard cost"),
      ];
    }

    if (formData.selling_price !== "" && formData.selling_price !== null) {
      validationRules.selling_price = [
        (v) => validatePrice(v, "Selling price"),
      ];
    }

    return validateForm(formData, validationRules);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setErrors({});

    const validationErrors = validateFormData();
    if (hasErrors(validationErrors)) {
      setErrors(validationErrors);
      return;
    }

    setLoading(true);

    try {
      const payload = {
        sku: formData.sku,
        name: formData.name,
        description: formData.description || null,
        item_type: formData.item_type,
        procurement_type: formData.procurement_type,
        stocking_policy: formData.stocking_policy,
        unit: formData.unit,
        standard_cost: formData.standard_cost
          ? parseFloat(formData.standard_cost)
          : null,
        selling_price: formData.selling_price
          ? parseFloat(formData.selling_price)
          : null,
        reorder_point: formData.stocking_policy === "stocked" && formData.reorder_point
          ? parseFloat(formData.reorder_point)
          : null,
        category_id: formData.category_id || null,
        image_url: formData.image_url || null,
      };

      const url = editingItem
        ? `${API_URL}/api/v1/items/${editingItem.id}`
        : `${API_URL}/api/v1/items`;

      const method = editingItem ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to save item");
      }

      const data = await res.json();
      onSuccess?.(data);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={editingItem ? "Edit Item" : "Create New Item"}
      className="w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      disableClose={loading}
    >
      <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">
              {editingItem ? "Edit Item" : "Create New Item"}
            </h2>
            <button
              onClick={onClose}
              className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              ✕
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-[var(--error)] rounded-xl">
              {error}
            </div>
          )}

          <FormErrorSummary errors={errors} className="mb-4" />

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Input
                id="item-sku"
                label={<>SKU <span className="text-[var(--text-muted)] text-xs">(auto-generated if empty)</span></>}
                value={formData.sku}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    sku: e.target.value.toUpperCase(),
                  })
                }
                error={errors.sku}
                placeholder="Leave empty for auto-generation"
              />

              <div>
                <label htmlFor="item-unit" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                  Unit <RequiredIndicator />
                </label>
                <select
                  id="item-unit"
                  value={formData.unit}
                  onChange={(e) =>
                    setFormData({ ...formData, unit: e.target.value })
                  }
                  aria-invalid={!!errors.unit}
                  aria-describedby={errors.unit ? "item-unit-error" : undefined}
                  className={`w-full px-3 py-2 bg-[var(--bg-elevated)] border rounded-lg text-[var(--text-primary)] focus:outline-none transition-colors ${
                    errors.unit
                      ? "border-[var(--error)] focus:border-[var(--error)]"
                      : "border-[var(--border-subtle)] focus:border-[var(--primary)]"
                  }`}
                >
                  {uomClasses.length > 0 ? (
                    uomClasses.map((cls) => (
                      <optgroup
                        key={cls.uom_class}
                        label={
                          cls.uom_class.charAt(0).toUpperCase() +
                          cls.uom_class.slice(1)
                        }
                      >
                        {cls.units.map((u) => (
                          <option key={u.code} value={u.code}>
                            {u.code} - {u.name}
                          </option>
                        ))}
                      </optgroup>
                    ))
                  ) : (
                    <>
                      <option value="EA">EA - Each</option>
                      <option value="KG">KG - Kilogram</option>
                      <option value="G">G - Gram</option>
                      <option value="LB">LB - Pound</option>
                      <option value="M">M - Meter</option>
                      <option value="FT">FT - Foot</option>
                      <option value="HR">HR - Hour</option>
                    </>
                  )}
                </select>
                {errors.unit && (
                  <p id="item-unit-error" role="alert" className="text-[var(--error)] text-sm mt-1">{errors.unit}</p>
                )}
              </div>
            </div>

            <Input
              id="item-name"
              label={<>Name <RequiredIndicator /></>}
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              error={errors.name}
              placeholder="Item name"
            />

            <div>
              <label htmlFor="item-description" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Description
              </label>
              <textarea
                id="item-description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full px-3 py-2 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                rows="3"
                placeholder="Item description"
              />
            </div>

            <div>
              <label htmlFor="item-image-url" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Product Image
              </label>
              <div className="flex gap-3 items-start">
                <div className="flex-1">
                  <div className="flex gap-2">
                    <input
                      id="item-image-url"
                      type="text"
                      value={formData.image_url}
                      onChange={(e) =>
                        setFormData({ ...formData, image_url: e.target.value })
                      }
                      className="flex-1 px-3 py-2 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--primary)] focus:outline-none transition-colors"
                      placeholder="https://example.com/image.jpg"
                    />
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept="image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif"
                      className="hidden"
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (!file) return;

                        if (file.size > 5 * 1024 * 1024) {
                          setError("Image must be less than 5MB");
                          return;
                        }

                        setUploading(true);
                        setError(null);

                        try {
                          const uploadData = new FormData();
                          uploadData.append("file", file);

                          const res = await fetch(
                            `${API_URL}/api/v1/admin/uploads/product-image`,
                            {
                              method: "POST",
                              credentials: "include",
                              body: uploadData,
                            }
                          );

                          if (!res.ok) {
                            const err = await res.json();
                            throw new Error(err.detail || "Upload failed");
                          }

                          const data = await res.json();
                          setFormData((prev) => ({ ...prev, image_url: data.url }));
                        } catch (err) {
                          setError("Image upload failed. Please try again or paste a URL instead.");
                        } finally {
                          setUploading(false);
                          if (fileInputRef.current) {
                            fileInputRef.current.value = "";
                          }
                        }
                      }}
                    />
                    <Button
                      variant="secondary"
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                    >
                      {uploading ? "Uploading..." : "Upload"}
                    </Button>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Paste a URL or upload an image (JPG, PNG, WebP, GIF - max 5MB)
                  </p>
                </div>
                {formData.image_url && (
                  <div className="flex-shrink-0">
                    <img
                      src={formData.image_url}
                      alt="Product preview"
                      className="h-16 w-16 object-cover rounded border border-[var(--border-subtle)]"
                      onError={(e) => {
                        e.target.style.display = "none";
                      }}
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Select
                  id="item-type"
                  label={<>Item Type <RequiredIndicator /></>}
                  value={formData.item_type}
                  onChange={(e) =>
                    setFormData({ ...formData, item_type: e.target.value })
                  }
                  options={ITEM_TYPES}
                  error={errors.item_type}
                />
                {formData.item_type === 'material' && (
                  <p className="text-xs text-[var(--primary-light)] mt-1">
                    Materials use: Unit=G (grams), Purchase=KG (kilograms)
                  </p>
                )}
              </div>

              <Select
                id="item-procurement-type"
                label={<>Procurement Type <RequiredIndicator /></>}
                value={formData.procurement_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    procurement_type: e.target.value,
                  })
                }
                options={PROCUREMENT_TYPES}
                error={errors.procurement_type}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Select
                  id="item-stocking-policy"
                  label="Stocking Policy"
                  value={formData.stocking_policy}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      stocking_policy: e.target.value,
                    })
                  }
                  options={STOCKING_POLICIES}
                  helpText={
                    formData.stocking_policy === "stocked"
                      ? "Item will show as low stock when below reorder point"
                      : "Item is only ordered when MRP shows demand"
                  }
                />
              </div>

              {formData.stocking_policy === "stocked" && (
                <Input
                  id="item-reorder-point"
                  label="Reorder Point"
                  type="number"
                  step="1"
                  min="0"
                  value={formData.reorder_point}
                  onChange={(e) =>
                    setFormData({ ...formData, reorder_point: e.target.value })
                  }
                  placeholder="Min quantity to keep on hand"
                />
              )}
            </div>

            <Select
              id="item-category"
              label="Category"
              value={formData.category_id || ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  category_id: e.target.value
                    ? parseInt(e.target.value)
                    : null,
                })
              }
              options={categories.map((cat) => ({ value: cat.id, label: cat.name }))}
              placeholder="No category"
            />

            <div className="grid grid-cols-2 gap-4">
              <Input
                id="item-standard-cost"
                label="Standard Cost"
                type="number"
                step="0.01"
                value={formData.standard_cost}
                onChange={(e) =>
                  setFormData({ ...formData, standard_cost: e.target.value })
                }
                error={errors.standard_cost}
                placeholder="0.00"
              />

              <Input
                id="item-selling-price"
                label="Selling Price"
                type="number"
                step="0.01"
                value={formData.selling_price}
                onChange={(e) =>
                  setFormData({ ...formData, selling_price: e.target.value })
                }
                error={errors.selling_price}
                placeholder="0.00"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-[var(--border-subtle)]">
              <Button
                variant="ghost"
                type="button"
                onClick={onClose}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                type="submit"
                loading={loading}
              >
                {editingItem ? "Update Item" : "Create Item"}
              </Button>
            </div>
          </form>

          {formData.procurement_type === "make" && (
            <div className="mt-4 p-3 rounded-xl text-sm" style={{ backgroundColor: 'rgba(2, 109, 248, 0.1)', border: '1px solid rgba(2, 109, 248, 0.3)', color: 'var(--primary-light)' }}>
              <strong>Note:</strong> This item requires a BOM and Routing.
              Create the item first, then add BOM and Routing from the item
              detail page.
            </div>
          )}
        </div>
    </Modal>
  );
}
