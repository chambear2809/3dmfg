import { forwardRef } from "react";

const Table = forwardRef(function Table(
  { children, className = "", ...rest },
  ref
) {
  return (
    <div className={`bg-[var(--bg-card)] rounded-lg border border-[var(--border-subtle)] overflow-hidden ${className}`}>
      <table ref={ref} className="w-full" {...rest}>
        {children}
      </table>
    </div>
  );
});

const TableHeader = forwardRef(function TableHeader(
  { children, className = "", ...rest },
  ref
) {
  return (
    <thead ref={ref} className={`bg-[var(--bg-elevated)]/50 ${className}`} {...rest}>
      {children}
    </thead>
  );
});

const TableBody = forwardRef(function TableBody(
  { children, className = "", ...rest },
  ref
) {
  return (
    <tbody ref={ref} className={`divide-y divide-[var(--border-subtle)] ${className}`} {...rest}>
      {children}
    </tbody>
  );
});

const TableRow = forwardRef(function TableRow(
  { children, className = "", ...rest },
  ref
) {
  return (
    <tr ref={ref} className={`hover:bg-[var(--bg-elevated)]/30 transition-colors ${className}`} {...rest}>
      {children}
    </tr>
  );
});

const TableHead = forwardRef(function TableHead(
  { children, className = "", ...rest },
  ref
) {
  return (
    <th
      ref={ref}
      className={`px-4 py-3 text-left text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider ${className}`}
      {...rest}
    >
      {children}
    </th>
  );
});

const TableCell = forwardRef(function TableCell(
  { children, className = "", ...rest },
  ref
) {
  return (
    <td ref={ref} className={`px-4 py-3 text-[var(--text-primary)] ${className}`} {...rest}>
      {children}
    </td>
  );
});

const TableEmpty = forwardRef(function TableEmpty(
  { colSpan = 1, children, className = "", ...rest },
  ref
) {
  return (
    <tr ref={ref} {...rest}>
      <td
        colSpan={colSpan}
        className={`px-4 py-8 text-center text-[var(--text-muted)] ${className}`}
      >
        {children}
      </td>
    </tr>
  );
});

export { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty };
