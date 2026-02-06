import MaterialWizardForm from "../item-wizard/MaterialWizardForm";
import SubComponentWizardForm from "../item-wizard/SubComponentWizardForm";

/**
 * BomBuilderStep - Step 2 of the Item Wizard.
 *
 * Provides the BOM builder with component selection, material wizard,
 * sub-component wizard, BOM line editing, and routing template selection.
 *
 * Props:
 * - components: array - All available components/materials
 * - bomLines: array - Current BOM lines
 * - calculatedCost: number - Sum of BOM line costs
 * - routingTemplates: array - Available routing templates
 * - selectedTemplate: object|null - Currently selected routing template
 * - routingOperations: array - Operations from the selected template
 * - laborCost: number - Calculated labor cost from routing
 * - showMaterialWizard: boolean
 * - showSubComponentWizard: boolean
 * - materialTypes: array
 * - allColors: array
 * - newMaterial: object
 * - subComponent: object
 * - loading: boolean
 * - onAddBomLine: (component) => void
 * - onRemoveBomLine: (componentId) => void
 * - onUpdateBomQuantity: (componentId, quantity) => void
 * - onShowMaterialWizard: (show) => void
 * - onShowSubComponentWizard: (show) => void
 * - onMaterialChange: (material) => void
 * - onColorTypeChange: (code) => void
 * - onCreateMaterial: () => void
 * - onSubComponentChange: (subComponent) => void
 * - onSaveSubComponent: () => void
 * - onStartSubComponent: () => void
 * - onApplyRoutingTemplate: (template) => void
 */
export default function BomBuilderStep({
  components,
  bomLines,
  calculatedCost,
  routingTemplates,
  selectedTemplate,
  routingOperations,
  laborCost,
  showMaterialWizard,
  showSubComponentWizard,
  materialTypes,
  allColors,
  newMaterial,
  subComponent,
  loading,
  onAddBomLine,
  onRemoveBomLine,
  onUpdateBomQuantity,
  onShowMaterialWizard,
  onShowSubComponentWizard,
  onMaterialChange,
  onColorTypeChange,
  onCreateMaterial,
  onSubComponentChange,
  onSaveSubComponent,
  onStartSubComponent,
  onApplyRoutingTemplate,
}) {
  return (
    <div className="space-y-6">
      {/* BOM Components Section */}
      <div>
        <div className="flex justify-between items-center mb-3">
          <label className="text-sm text-gray-400 font-medium">BOM Components</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onShowMaterialWizard(true)}
              className="text-xs px-2 py-1 bg-pink-600/20 border border-pink-500/30 text-pink-400 rounded hover:bg-pink-600/30"
            >
              + Add Filament
            </button>
            <button
              type="button"
              onClick={onStartSubComponent}
              className="text-xs px-2 py-1 bg-purple-600/20 border border-purple-500/30 text-purple-400 rounded hover:bg-purple-600/30"
            >
              + Create Component
            </button>
          </div>
        </div>

        {/* Material Wizard */}
        {showMaterialWizard && (
          <MaterialWizardForm
            materialTypes={materialTypes}
            allColors={allColors}
            newMaterial={newMaterial}
            loading={loading}
            onMaterialChange={onMaterialChange}
            onColorTypeChange={onColorTypeChange}
            onCreateMaterial={onCreateMaterial}
            onCancel={() => onShowMaterialWizard(false)}
          />
        )}

        {/* Sub-Component Wizard */}
        {showSubComponentWizard && (
          <SubComponentWizardForm
            subComponent={subComponent}
            loading={loading}
            onSubComponentChange={onSubComponentChange}
            onSave={onSaveSubComponent}
            onCancel={() => onShowSubComponentWizard(false)}
          />
        )}

        {/* Component Dropdown */}
        <select
          onChange={(e) => {
            const val = e.target.value;
            const comp = components.find(c => String(c.id) === val);
            if (comp) onAddBomLine(comp);
            e.target.value = "";
          }}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
        >
          <option value="">-- Select component or material to add --</option>
          <optgroup label="Components & Supplies">
            {components.filter(c => !c.is_material && !bomLines.find(bl => bl.component_id === c.id)).map(c => (
              <option key={c.id} value={c.id}>
                {c.sku} - {c.name} (${parseFloat(c.standard_cost || c.average_cost || c.cost || 0).toFixed(2)}/{c.unit})
              </option>
            ))}
          </optgroup>
          <optgroup label="Filament / Materials">
            {components.filter(c => c.is_material && !bomLines.find(bl => bl.component_id === c.id)).map(c => (
              <option key={c.id} value={c.id}>
                {c.name} {c.in_stock ? "" : "(Out of Stock)"} (${parseFloat(c.standard_cost || 0).toFixed(3)}/{c.unit})
              </option>
            ))}
          </optgroup>
        </select>
      </div>

      {/* BOM Lines */}
      {bomLines.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700 divide-y divide-gray-700">
          {bomLines.map(line => (
            <div key={line.component_id} className="p-3 flex items-center gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-white font-medium">{line.component_name}</span>
                  {line.is_material && (
                    <span className="text-xs bg-purple-600/30 text-purple-300 px-1.5 py-0.5 rounded">Filament</span>
                  )}
                </div>
                <div className="text-gray-500 text-xs font-mono">{line.component_sku}</div>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-gray-400 text-sm">Qty:</label>
                <input
                  type="number"
                  min="0.001"
                  step="0.001"
                  value={line.quantity}
                  onChange={(e) => onUpdateBomQuantity(line.component_id, parseFloat(e.target.value) || 0.001)}
                  className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-center"
                />
                <span className="text-gray-500 text-sm">{line.component_unit}</span>
              </div>
              <div className="text-gray-400 text-sm">
                @ ${parseFloat(line.component_cost).toFixed(2)}
              </div>
              <div className="text-green-400 font-medium w-20 text-right">
                ${(line.quantity * line.component_cost).toFixed(2)}
              </div>
              <button
                type="button"
                onClick={() => onRemoveBomLine(line.component_id)}
                className="text-red-400 hover:text-red-300 p-1"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          <div className="p-3 flex justify-between items-center bg-gray-800/80">
            <span className="text-white font-medium">Material Cost</span>
            <span className="text-green-400 font-bold">${calculatedCost.toFixed(2)}</span>
          </div>
        </div>
      )}

      {bomLines.length === 0 && (
        <div className="text-center py-8 text-gray-500 border border-dashed border-gray-700 rounded-lg">
          No components added yet. Select from the dropdown above or create new ones.
        </div>
      )}

      {/* Routing Templates */}
      {routingTemplates.length > 0 && (
        <div className="border-t border-gray-700 pt-4">
          <label className="text-sm text-gray-400 font-medium mb-2 block">Routing Template (optional)</label>
          <select
            value={selectedTemplate?.id || ""}
            onChange={(e) => {
              const tpl = routingTemplates.find(t => t.id === parseInt(e.target.value));
              onApplyRoutingTemplate(tpl || null);
            }}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
          >
            <option value="">-- No routing --</option>
            {routingTemplates.map(t => (
              <option key={t.id} value={t.id}>{t.name || t.code}</option>
            ))}
          </select>
          {routingOperations.length > 0 && (
            <div className="mt-2 text-sm text-gray-400">
              {routingOperations.length} operations, est. labor: ${laborCost.toFixed(2)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
