import ItemCreationWizard from "./ItemCreationWizard";

export default function ProductSelectionStep({
  products,
  productSearch,
  setProductSearch,
  lineItems,
  addLineItem,
  removeLineItem,
  updateLineQuantity,
  updateLinePrice,
  orderTotal,
  startNewItem,
  // Item creation wizard props
  showItemWizard,
  itemWizardProps,
}) {
  if (showItemWizard) {
    return (
      <div className="space-y-6">
        <ItemCreationWizard {...itemWizardProps} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-white">
          Add Products
        </h3>
        <button
          onClick={startNewItem}
          className="px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-500 hover:to-emerald-500 text-sm"
        >
          + Create New Product
        </button>
      </div>

      {/* Product Search */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search products by SKU or name..."
          value={productSearch}
          onChange={(e) => setProductSearch(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white pl-10"
        />
        <svg
          className="w-5 h-5 absolute left-3 top-3.5 text-gray-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        {productSearch && (
          <button
            onClick={() => setProductSearch("")}
            className="absolute right-3 top-3.5 text-gray-500 hover:text-white"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-3 gap-3 max-h-[300px] overflow-auto">
        {(() => {
          const searchTerm = productSearch.trim().toLowerCase();
          const filteredProducts = products.filter((p) => {
            if (!p.has_bom) return false;
            if (!searchTerm) return true;
            const nameMatch = (p.name || "").toLowerCase().includes(searchTerm);
            const skuMatch = (p.sku || "").toLowerCase().includes(searchTerm);
            return nameMatch || skuMatch;
          });

          if (filteredProducts.length === 0) {
            return (
              <div className="col-span-3 text-center py-8 text-gray-500">
                {searchTerm
                  ? `No products with BOM found matching "${productSearch}"`
                  : "No products with BOM available. Create a BOM for your products to sell them."}
              </div>
            );
          }

          return filteredProducts.map((product) => (
            <button
              key={product.id}
              onClick={() => addLineItem(product)}
              className="text-left p-3 bg-gray-800 border border-gray-700 rounded-lg hover:border-blue-500 hover:bg-gray-800/80 transition-colors"
            >
              <div className="text-white font-medium text-sm truncate">
                {product.name}
              </div>
              <div className="text-gray-500 text-xs font-mono">
                {product.sku}
              </div>
              <div className="text-green-400 text-sm mt-1">
                ${parseFloat(product.selling_price || 0).toFixed(2)}
              </div>
            </button>
          ));
        })()}
      </div>

      {/* Selected Line Items */}
      {lineItems.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-md font-medium text-white">
            Order Lines
          </h4>
          <div className="bg-gray-800/50 rounded-lg border border-gray-700 divide-y divide-gray-700">
            {lineItems.map((li) => (
              <div
                key={li.product_id}
                className="p-3 flex items-center gap-4"
              >
                <div className="flex-1">
                  <div className="text-white font-medium">
                    {li.product?.name}
                  </div>
                  <div className="text-gray-500 text-xs font-mono">
                    {li.product?.sku}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-gray-400 text-sm">
                    Qty:
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={li.quantity}
                    onChange={(e) =>
                      updateLineQuantity(
                        li.product_id,
                        parseInt(e.target.value) || 1
                      )
                    }
                    className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-center"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-gray-400 text-sm">$</label>
                  <input
                    type="number"
                    step="0.01"
                    value={li.unit_price}
                    onChange={(e) =>
                      updateLinePrice(
                        li.product_id,
                        parseFloat(e.target.value) || 0
                      )
                    }
                    className="w-24 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-right"
                  />
                </div>
                <div className="text-green-400 font-medium w-24 text-right">
                  ${(li.quantity * li.unit_price).toFixed(2)}
                </div>
                <button
                  onClick={() => removeLineItem(li.product_id)}
                  className="text-red-400 hover:text-red-300 p-1"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            ))}
            <div className="p-3 flex justify-between items-center bg-gray-800/80">
              <span className="text-white font-medium">
                Order Total
              </span>
              <span className="text-green-400 font-bold text-lg">
                ${orderTotal.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
