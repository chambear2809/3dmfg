/**
 * PricingStep - Step 3 of the Item Wizard.
 *
 * Displays cost summary, margin calculator, standard cost, selling price,
 * and actual margin/profit calculations.
 *
 * Props:
 * - item: object - Current item form state
 * - calculatedCost: number - Material cost from BOM lines
 * - laborCost: number - Labor cost from routing operations
 * - totalCost: number - calculatedCost + laborCost
 * - targetMargin: number - Target margin percentage
 * - suggestedPrice: number - Calculated suggested selling price
 * - onItemChange: (updatedItem) => void
 * - onTargetMarginChange: (margin) => void
 */
export default function PricingStep({
  item,
  calculatedCost,
  laborCost,
  totalCost,
  targetMargin,
  suggestedPrice,
  onItemChange,
  onTargetMarginChange,
}) {
  return (
    <div className="space-y-6">
      {/* Cost Summary */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4 space-y-3">
        <div className="flex justify-between">
          <span className="text-gray-400">Material Cost</span>
          <span className="text-white">${calculatedCost.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Labor Cost</span>
          <span className="text-white">${laborCost.toFixed(2)}</span>
        </div>
        <div className="flex justify-between border-t border-gray-700 pt-3">
          <span className="text-white font-medium">Total Cost</span>
          <span className="text-green-400 font-bold">${totalCost.toFixed(2)}</span>
        </div>
      </div>

      {/* Margin Calculator */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">Target Margin: {targetMargin}%</label>
        <input
          type="range"
          min="10"
          max="80"
          value={targetMargin}
          onChange={(e) => onTargetMarginChange(parseInt(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>10%</span>
          <span>80%</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Standard Cost</label>
          <input
            type="number"
            step="0.01"
            value={totalCost > 0 ? totalCost.toFixed(2) : item.standard_cost || ""}
            onChange={(e) => onItemChange({ ...item, standard_cost: parseFloat(e.target.value) || null })}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
          />
          <p className="text-xs text-gray-500 mt-1">Auto-filled from BOM + Labor</p>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Selling Price</label>
          <div className="flex gap-2">
            <input
              type="number"
              step="0.01"
              value={item.selling_price || ""}
              onChange={(e) => onItemChange({ ...item, selling_price: parseFloat(e.target.value) || null })}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            />
            <button
              type="button"
              onClick={() => onItemChange({ ...item, selling_price: suggestedPrice })}
              className="px-3 py-2 bg-green-600/20 border border-green-500/30 text-green-400 rounded-lg text-sm hover:bg-green-600/30"
            >
              ${suggestedPrice.toFixed(2)}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">Click suggested price to apply</p>
        </div>
      </div>

      {item.selling_price && totalCost > 0 && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
          <div className="flex justify-between items-center">
            <span className="text-blue-400">Actual Margin</span>
            <span className="text-white font-bold">
              {(((item.selling_price - totalCost) / item.selling_price) * 100).toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between items-center mt-1">
            <span className="text-blue-400">Profit per Unit</span>
            <span className="text-green-400 font-bold">${(item.selling_price - totalCost).toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
