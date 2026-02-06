/**
 * AddOperationForm - Form for adding a new operation to a routing.
 *
 * Props:
 * - workCenters: array - Available work centers
 * - newOperation: object - The new operation state
 * - onOperationChange: (updatedOperation) => void
 * - onAdd: () => void - Called when the Add button is clicked
 * - onCancel: () => void - Called when the Cancel button is clicked
 */
export default function AddOperationForm({
  workCenters,
  newOperation,
  onOperationChange,
  onAdd,
  onCancel,
}) {
  function updateField(field, value) {
    onOperationChange({ ...newOperation, [field]: value });
  }

  return (
    <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
      <h4 className="font-semibold mb-3 text-white">
        Add Operation
      </h4>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1 text-gray-300">
            Work Center
          </label>
          <select
            value={newOperation.work_center_id}
            onChange={(e) => updateField("work_center_id", e.target.value)}
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white"
          >
            <option value="">Select work center...</option>
            {workCenters.map((wc) => (
              <option key={wc.id} value={wc.id}>
                {wc.code} - {wc.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Operation Name
          </label>
          <input
            type="text"
            value={newOperation.operation_name}
            onChange={(e) => updateField("operation_name", e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
            placeholder="e.g., 3D Print, Support Removal"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Operation Code
          </label>
          <input
            type="text"
            value={newOperation.operation_code}
            onChange={(e) => updateField("operation_code", e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
            placeholder="e.g., OP10, OP20"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Setup Time (minutes)
          </label>
          <input
            type="number"
            step="0.1"
            min="0"
            value={newOperation.setup_time_minutes}
            onChange={(e) => updateField("setup_time_minutes", parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Run Time (minutes)
          </label>
          <input
            type="number"
            step="0.1"
            min="0"
            value={newOperation.run_time_minutes}
            onChange={(e) => updateField("run_time_minutes", parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Units per Cycle
          </label>
          <input
            type="number"
            step="1"
            min="1"
            value={newOperation.units_per_cycle}
            onChange={(e) => updateField("units_per_cycle", parseInt(e.target.value) || 1)}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <button
          onClick={onAdd}
          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
        >
          Add
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-gray-300 rounded-md hover:bg-gray-400"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
