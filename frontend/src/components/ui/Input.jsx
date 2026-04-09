import { forwardRef, useId } from "react";

const Input = forwardRef(function Input(
  { label, error, helpText, className = "", id: externalId, ...rest },
  ref
) {
  const generatedId = useId();
  const id = externalId || generatedId;
  const errorId = `${id}-error`;
  const helpId = `${id}-help`;

  const borderClass = error
    ? "border-[var(--error)] focus:border-[var(--error)]"
    : "border-[var(--border-subtle)] focus:border-[var(--primary)]";

  return (
    <div>
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-medium text-[var(--text-secondary)] mb-1"
        >
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={id}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={
          error ? errorId : helpText ? helpId : undefined
        }
        className={`w-full bg-[var(--bg-elevated)] border rounded-lg px-3 py-2 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none transition-colors ${borderClass} ${className}`}
        {...rest}
      />
      {error && (
        <p id={errorId} className="mt-1 text-sm text-[var(--error)]">
          {error}
        </p>
      )}
      {helpText && !error && (
        <p id={helpId} className="mt-1 text-sm text-[var(--text-muted)]">
          {helpText}
        </p>
      )}
    </div>
  );
});

export default Input;
