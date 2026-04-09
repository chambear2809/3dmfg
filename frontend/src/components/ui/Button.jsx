import { forwardRef } from "react";

const VARIANT_CLASSES = {
  primary:
    "bg-[var(--primary)] hover:bg-[var(--primary-light)] text-white hover:shadow-glow disabled:opacity-50",
  secondary:
    "bg-[var(--bg-elevated)] hover:bg-[var(--border-active)] text-white border border-[var(--border-subtle)] disabled:opacity-50",
  danger:
    "bg-red-600 hover:bg-red-700 text-white disabled:opacity-50",
  ghost:
    "bg-transparent hover:bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-50",
};

const SIZE_CLASSES = {
  sm: "px-3 py-1.5 text-sm gap-1.5",
  md: "px-4 py-2 text-sm gap-2",
  lg: "px-5 py-2.5 text-base gap-2",
};

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

const Button = forwardRef(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    disabled = false,
    icon,
    children,
    className = "",
    type = "button",
    ...rest
  },
  ref
) {
  const variantClasses = VARIANT_CLASSES[variant] || VARIANT_CLASSES.primary;
  const sizeClasses = SIZE_CLASSES[size] || SIZE_CLASSES.md;

  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-[color:var(--primary)]/50 disabled:cursor-not-allowed ${variantClasses} ${sizeClasses} ${className}`}
      {...rest}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </button>
  );
});

export default Button;
