/**
 * MaterialForm - Simple form for creating material items (filament)
 *
 * Uses the new POST /api/v1/items/material endpoint.
 * Pre-filled for material creation with material type and color selection.
 * Allows creating new colors on-the-fly if none exist for the material type.
 */
import { useState, useEffect, useCallback } from "react";
import { API_URL } from "../config/api";
import Modal from "./Modal";
import Input from "./ui/Input";
import Button from "./ui/Button";

export default function MaterialForm({ isOpen, onClose, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [materialTypes, setMaterialTypes] = useState([]);
  const [colors, setColors] = useState([]);
  const [selectedMaterialType, setSelectedMaterialType] = useState("");

  const [showColorForm, setShowColorForm] = useState(false);
  const [newColorName, setNewColorName] = useState("");
  const [newColorHex, setNewColorHex] = useState("#000000");
  const [creatingColor, setCreatingColor] = useState(false);

  const [formData, setFormData] = useState({
    material_type_code: "",
    color_code: "",
    initial_qty_kg: 0,
    cost_per_kg: "",
    selling_price: "",
  });

  const fetchMaterialTypes = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/materials/types?customer_visible_only=false`,
        {
          credentials: "include",
        }
      );
      if (res.ok) {
        const data = await res.json();
        setMaterialTypes(data.materials || []);
      }
    } catch {
      // Material types fetch failure is non-critical
    }
  }, []);

  const fetchColors = useCallback(
    async (materialTypeCode) => {
      try {
        const res = await fetch(
          `${API_URL}/api/v1/materials/types/${materialTypeCode}/colors?in_stock_only=false&customer_visible_only=false`,
          {
            credentials: "include",
          }
        );
        if (res.ok) {
          const data = await res.json();
          setColors(data.colors || []);
        }
      } catch {
        setColors([]);
      }
    },
    []
  );

  useEffect(() => {
    if (isOpen) {
      fetchMaterialTypes();
      setFormData({
        material_type_code: "",
        color_code: "",
        initial_qty_kg: 0,
        cost_per_kg: "",
        selling_price: "",
      });
      setSelectedMaterialType("");
      setError(null);
      setShowColorForm(false);
      setNewColorName("");
      setNewColorHex("#000000");
    }
  }, [isOpen, fetchMaterialTypes]);

  useEffect(() => {
    if (selectedMaterialType) {
      fetchColors(selectedMaterialType);
    } else {
      setColors([]);
    }
  }, [selectedMaterialType, fetchColors]);

  const handleCreateColor = async () => {
    if (!newColorName.trim()) {
      setError("Color name is required");
      return;
    }

    setCreatingColor(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_URL}/api/v1/materials/types/${selectedMaterialType}/colors`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: newColorName.trim(),
            hex_code: newColorHex || null,
          }),
        }
      );

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to create color");
      }

      const data = await res.json();

      await fetchColors(selectedMaterialType);
      setFormData({ ...formData, color_code: data.code });
      setShowColorForm(false);
      setNewColorName("");
      setNewColorHex("#000000");
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingColor(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        material_type_code: formData.material_type_code,
        color_code: formData.color_code,
        initial_qty_kg: parseFloat(formData.initial_qty_kg) || 0,
        cost_per_kg: formData.cost_per_kg
          ? parseFloat(formData.cost_per_kg)
          : null,
        selling_price: formData.selling_price
          ? parseFloat(formData.selling_price)
          : null,
      };

      const res = await fetch(`${API_URL}/api/v1/items/material`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to create material");
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

  const selectedMaterial = materialTypes.find(
    (m) => m.code === formData.material_type_code
  );

  const selectClasses = "w-full px-3 py-2 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] focus:border-[var(--primary)] focus:outline-none transition-colors";

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Material" disableClose={loading}>
      <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">
              Create New Material
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

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="material-type" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Material Type <span className="text-[var(--error)]">*</span>
              </label>
              <select
                id="material-type"
                required
                value={formData.material_type_code}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    material_type_code: e.target.value,
                    color_code: "",
                  });
                  setSelectedMaterialType(e.target.value);
                }}
                className={selectClasses}
              >
                <option value="">Select material type...</option>
                {materialTypes.map((mt) => (
                  <option key={mt.code} value={mt.code}>
                    {mt.name} ({mt.base_material})
                  </option>
                ))}
              </select>
              {selectedMaterial && (
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  {selectedMaterial.description}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="material-color" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Color <span className="text-[var(--error)]">*</span>
              </label>

              {!showColorForm ? (
                <>
                  <select
                    id="material-color"
                    required={!showColorForm}
                    value={formData.color_code}
                    onChange={(e) =>
                      setFormData({ ...formData, color_code: e.target.value })
                    }
                    className={selectClasses}
                    disabled={!formData.material_type_code}
                  >
                    <option value="">
                      {formData.material_type_code
                        ? colors.length === 0
                          ? "No colors available - create one below"
                          : "Select color..."
                        : "Select material type first"}
                    </option>
                    {colors.map((color) => (
                      <option key={color.code} value={color.code}>
                        {color.name} {color.hex && `(${color.hex})`}
                      </option>
                    ))}
                  </select>

                  {formData.material_type_code && (
                    <button
                      type="button"
                      onClick={() => setShowColorForm(true)}
                      className="mt-2 text-sm text-[var(--primary-light)] hover:text-[var(--primary)] flex items-center gap-1 transition-colors"
                    >
                      <span>+</span> Create new color for this material
                    </button>
                  )}
                </>
              ) : (
                <div className="border border-[var(--border-subtle)] rounded-xl p-3 bg-[var(--bg-elevated)] space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-[var(--text-secondary)]">
                      New Color
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setShowColorForm(false);
                        setNewColorName("");
                        setNewColorHex("#000000");
                      }}
                      className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm transition-colors"
                    >
                      Cancel
                    </button>
                  </div>

                  <Input
                    id="material-new-color-name"
                    label="Color Name *"
                    value={newColorName}
                    onChange={(e) => setNewColorName(e.target.value)}
                    placeholder="e.g., Mystic Blue"
                  />

                  <div>
                    <label htmlFor="material-new-color-hex" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                      Hex Color (optional)
                    </label>
                    <div className="flex gap-2 items-center">
                      <input
                        type="color"
                        value={newColorHex}
                        onChange={(e) => setNewColorHex(e.target.value)}
                        aria-label="Color picker"
                        className="w-10 h-10 border border-[var(--border-subtle)] rounded cursor-pointer bg-[var(--bg-elevated)]"
                      />
                      <input
                        id="material-new-color-hex"
                        type="text"
                        value={newColorHex}
                        onChange={(e) => setNewColorHex(e.target.value)}
                        placeholder="#000000"
                        className="flex-1 px-3 py-2 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] text-sm focus:border-[var(--primary)] focus:outline-none transition-colors"
                      />
                    </div>
                  </div>

                  <Button
                    variant="primary"
                    type="button"
                    onClick={handleCreateColor}
                    disabled={creatingColor || !newColorName.trim()}
                    loading={creatingColor}
                    className="w-full"
                  >
                    Create Color
                  </Button>
                </div>
              )}
            </div>

            <Input
              id="material-initial-qty"
              label="Initial Quantity (kg)"
              type="number"
              step="0.001"
              min="0"
              value={formData.initial_qty_kg}
              onChange={(e) =>
                setFormData({ ...formData, initial_qty_kg: e.target.value })
              }
              placeholder="0.000"
            />

            <div className="grid grid-cols-2 gap-4">
              <Input
                id="material-cost-per-kg"
                label="Cost per kg"
                type="number"
                step="0.01"
                min="0"
                value={formData.cost_per_kg}
                onChange={(e) =>
                  setFormData({ ...formData, cost_per_kg: e.target.value })
                }
                placeholder="0.00"
              />

              <Input
                id="material-selling-price"
                label="Selling Price per kg"
                type="number"
                step="0.01"
                min="0"
                value={formData.selling_price}
                onChange={(e) =>
                  setFormData({ ...formData, selling_price: e.target.value })
                }
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
                disabled={
                  !formData.material_type_code ||
                  !formData.color_code
                }
              >
                Create Material
              </Button>
            </div>
          </form>

          <div className="mt-4 p-3 rounded-xl text-sm" style={{ backgroundColor: 'rgba(2, 109, 248, 0.1)', border: '1px solid rgba(2, 109, 248, 0.3)', color: 'var(--primary-light)' }}>
            <strong>Note:</strong> This will create a Product with SKU format:
            MAT-{formData.material_type_code || "TYPE"}-
            {formData.color_code || "COLOR"}
          </div>
        </div>
    </Modal>
  );
}
