/**
 * RoutingEditor - Modal wrapper for RoutingEditorContent
 *
 * Thin shell that provides the modal overlay and container.
 * All routing logic lives in RoutingEditorContent.
 */
import RoutingEditorContent from "./routing/RoutingEditorContent";

export default function RoutingEditor({
  isOpen,
  onClose,
  productId = null,
  routingId = null,
  onSuccess,
  products = [],
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-y-auto p-6">
        <RoutingEditorContent
          productId={productId}
          routingId={routingId}
          products={products}
          isActive={isOpen}
          onSuccess={(data) => {
            onSuccess?.(data);
            onClose();
          }}
          onCancel={onClose}
        />
      </div>
    </div>
  );
}
