export default function BOMCostRollupCard({ costRollup }) {
  if (!costRollup || !costRollup.has_sub_assemblies) return null;

  return (
    <div className="bg-gradient-to-r from-purple-600/10 to-blue-600/10 border border-purple-500/30 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-purple-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <span className="text-purple-300 font-medium">
            Multi-Level BOM
          </span>
        </div>
        <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded-full">
          {costRollup.sub_assembly_count} Sub-Assemblies
        </span>
      </div>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-400">Direct Cost:</span>
          <span className="text-white ml-2">
            ${parseFloat(costRollup.direct_cost || 0).toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-gray-400">Sub-Assembly Cost:</span>
          <span className="text-purple-400 ml-2">
            ${parseFloat(costRollup.sub_assembly_cost || 0).toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-gray-400">Rolled-Up Total:</span>
          <span className="text-green-400 ml-2 font-semibold">
            ${parseFloat(costRollup.rolled_up_cost || 0).toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
