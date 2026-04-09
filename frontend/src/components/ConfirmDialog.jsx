/**
 * ConfirmDialog - Accessible confirmation dialog to replace browser confirm()
 *
 * Usage:
 * const [showConfirm, setShowConfirm] = useState(false);
 * const [itemToDelete, setItemToDelete] = useState(null);
 *
 * <ConfirmDialog
 *   isOpen={showConfirm}
 *   title="Delete Item"
 *   message="Are you sure you want to delete this item?"
 *   confirmLabel="Delete"
 *   confirmVariant="danger"
 *   onConfirm={() => { deleteItem(itemToDelete); setShowConfirm(false); }}
 *   onCancel={() => setShowConfirm(false)}
 * />
 */
import { useEffect, useRef } from 'react';
import { AlertTriangle, AlertCircle, Info, Loader2 } from 'lucide-react';

const VARIANTS = {
  danger: {
    button: 'bg-red-600 hover:bg-red-500 text-white',
    icon: <AlertTriangle size={24} className="text-red-400" />,
  },
  warning: {
    button: 'bg-yellow-600 hover:bg-yellow-500 text-white',
    icon: <AlertCircle size={24} className="text-yellow-400" />,
  },
  info: {
    button: 'bg-[var(--primary)] hover:bg-[var(--primary-light)] text-white hover:shadow-glow',
    icon: <Info size={24} className="text-[var(--primary-light)]" />,
  },
};

export default function ConfirmDialog({
  isOpen,
  title = 'Confirm',
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  confirmVariant = 'danger',
  onConfirm,
  onCancel,
  isLoading = false,
}) {
  const cancelButtonRef = useRef(null);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (isOpen && cancelButtonRef.current) {
      cancelButtonRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen && !isLoading) {
        onCancel();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isLoading, onCancel]);

  useEffect(() => {
    if (!isOpen) return;

    const dialog = dialogRef.current;
    if (!dialog) return;

    const focusableElements = dialog.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTabKey = (e) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    dialog.addEventListener('keydown', handleTabKey);
    return () => dialog.removeEventListener('keydown', handleTabKey);
  }, [isOpen]);

  if (!isOpen) return null;

  const variant = VARIANTS[confirmVariant] || VARIANTS.danger;

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) {
          onCancel();
        }
      }}
    >
      <div
        ref={dialogRef}
        className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl w-full max-w-md p-6 shadow-xl animate-slide-up"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
      >
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 p-2 bg-[var(--bg-elevated)] rounded-full">
            {variant.icon}
          </div>
          <div className="flex-1">
            <h2
              id="confirm-dialog-title"
              className="text-lg font-semibold text-[var(--text-primary)]"
            >
              {title}
            </h2>
            <p
              id="confirm-dialog-message"
              className="mt-2 text-[var(--text-secondary)]"
            >
              {message}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            ref={cancelButtonRef}
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] rounded-lg transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 rounded-lg font-medium transition-all disabled:opacity-50 ${variant.button}`}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <Loader2 size={16} className="animate-spin" />
                Processing...
              </span>
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
