import { ITEM_TYPES, PROCUREMENT_TYPES } from "../item-wizard/constants";

/**
 * BasicInfoStep - Step 1 of the Item Wizard.
 *
 * Collects item type, procurement type, SKU, name, description,
 * category, and unit of measure.
 *
 * Props:
 * - item: object - Current item form state
 * - categories: array - Available categories for the dropdown
 * - itemNeedsBom: boolean - Whether the current procurement type needs a BOM
 * - onItemChange: (updatedItem) => void
 */
export default function BasicInfoStep({ item, categories, itemNeedsBom, onItemChange }) {
  return (
    <div className="space-y-6">
      {/* Item Type */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">Item Type</label>
        <div className="grid grid-cols-4 gap-2">
          {ITEM_TYPES.map(type => (
            <button
              key={type.value}
              type="button"
              onClick={() => {
                onItemChange({
                  ...item,
                  item_type: type.value,
                  procurement_type: type.defaultProcurement,
                });
              }}
              className={`p-3 rounded-lg border text-sm font-medium transition-all ${
                item.item_type === type.value
                  ? `bg-${type.color}-600/20 border-${type.color}-500 text-${type.color}-400`
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600"
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Procurement Type (Make vs Buy) */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">Procurement Type</label>
        <div className="grid grid-cols-3 gap-2">
          {PROCUREMENT_TYPES.map(proc => {
            let activeStyle = "";
            if (item.procurement_type === proc.value) {
              if (proc.value === "make") {
                activeStyle = "bg-green-600/20 border-green-500 text-green-400";
              } else if (proc.value === "buy") {
                activeStyle = "bg-blue-600/20 border-blue-500 text-blue-400";
              } else {
                activeStyle = "bg-yellow-600/20 border-yellow-500 text-yellow-400";
              }
            }

            return (
              <button
                key={proc.value}
                type="button"
                onClick={() => onItemChange({ ...item, procurement_type: proc.value })}
                className={`p-3 rounded-lg border text-left transition-all ${
                  item.procurement_type === proc.value
                    ? activeStyle
                    : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600"
                }`}
              >
                <div className="font-medium text-sm">{proc.label}</div>
                <div className="text-xs opacity-70">{proc.description}</div>
              </button>
            );
          })}
        </div>
        {itemNeedsBom && (
          <p className="text-xs text-green-400 mt-2">This item will have a BOM and/or routing</p>
        )}
      </div>

      {/* Basic fields */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">SKU *</label>
          <input
            type="text"
            value={item.sku}
            onChange={(e) => onItemChange({ ...item, sku: e.target.value.toUpperCase() })}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white font-mono"
            placeholder="Auto-generated"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Name *</label>
          <input
            type="text"
            value={item.name}
            onChange={(e) => onItemChange({ ...item, name: e.target.value })}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            placeholder="Item name"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Description</label>
        <textarea
          value={item.description}
          onChange={(e) => onItemChange({ ...item, description: e.target.value })}
          rows={2}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Category</label>
          <select
            value={item.category_id || ""}
            onChange={(e) => onItemChange({ ...item, category_id: e.target.value ? parseInt(e.target.value) : null })}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
          >
            <option value="">-- None --</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>{cat.full_path || cat.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Unit</label>
          <input
            type="text"
            value={item.unit}
            onChange={(e) => onItemChange({ ...item, unit: e.target.value.toUpperCase() })}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
          />
        </div>
      </div>
    </div>
  );
}
