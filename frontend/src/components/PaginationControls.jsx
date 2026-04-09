/**
 * Reusable Pagination Controls Component
 * Works with the standardized pagination from usePagination hook
 */
import React from "react";

/**
 * @typedef {Object} PaginationControlsProps
 * @property {Object} pagination - Pagination object from usePagination hook
 * @property {number} pagination.currentPage - Current page number
 * @property {number} pagination.totalPages - Total number of pages
 * @property {number} pagination.total - Total number of items
 * @property {number} pagination.offset - Current offset
 * @property {number} pagination.limit - Items per page
 * @property {number} [pagination.returned] - Actual items returned (from API)
 * @property {boolean} pagination.hasNext - Whether there's a next page
 * @property {boolean} pagination.hasPrev - Whether there's a previous page
 * @property {() => void} pagination.nextPage - Go to next page
 * @property {() => void} pagination.prevPage - Go to previous page
 * @property {(page: number) => void} pagination.goToPage - Go to specific page
 * @property {string} [className] - Additional CSS classes
 * @property {boolean} [showPageSize=false] - Show page size selector
 * @property {(limit: number) => void} [onPageSizeChange] - Called when page size changes
 * @property {number[]} [pageSizeOptions] - Available page size options
 */

/**
 * Pagination controls with page info and navigation buttons
 * @param {PaginationControlsProps} props
 */
export function PaginationControls({
  pagination,
  className = "",
  showPageSize = false,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100, 200],
}) {
  if (!pagination || pagination.totalPages === 0) {
    return null;
  }

  const {
    currentPage,
    totalPages,
    total,
    offset,
    limit,
    returned,
    hasNext,
    hasPrev,
    nextPage,
    prevPage,
    goToPage,
  } = pagination;

  const startItem = offset + 1;
  const endItem = returned !== undefined ? offset + returned : Math.min(offset + limit, total);

  const getPageNumbers = () => {
    const pages = [];
    const maxPages = 7;

    if (totalPages <= maxPages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);

      if (currentPage > 3) {
        pages.push("...");
      }

      const startPage = Math.max(2, currentPage - 1);
      const endPage = Math.min(totalPages - 1, currentPage + 1);

      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }

      if (currentPage < totalPages - 2) {
        pages.push("...");
      }

      pages.push(totalPages);
    }

    return pages;
  };

  const pageNumbers = getPageNumbers();

  return (
    <div className={`flex flex-col sm:flex-row items-center justify-between gap-4 ${className}`}>
      <div className="text-sm text-[var(--text-secondary)]">
        {total > 0 ? (
          <>
            Showing <span className="font-medium text-[var(--text-primary)]">{startItem}</span> to{" "}
            <span className="font-medium text-[var(--text-primary)]">{endItem}</span> of{" "}
            <span className="font-medium text-[var(--text-primary)]">{total}</span> results
          </>
        ) : (
          "No results"
        )}
      </div>

      {showPageSize && onPageSizeChange && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-[var(--text-secondary)]">Show:</span>
          <select
            value={limit}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="px-2 py-1 bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] rounded text-sm focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
          <span className="text-sm text-[var(--text-secondary)]">per page</span>
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={prevPage}
          disabled={!hasPrev}
          className="px-3 py-1 bg-[var(--bg-elevated)] text-[var(--text-primary)] rounded border border-[var(--border-subtle)] hover:bg-[var(--border-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          aria-label="Previous page"
        >
          Previous
        </button>

        <div className="hidden sm:flex items-center gap-1">
          {pageNumbers.map((page, index) => {
            if (page === "...") {
              return (
                <span key={`ellipsis-${index}`} className="px-2 text-[var(--text-muted)]">
                  ...
                </span>
              );
            }

            const isActive = page === currentPage;

            return (
              <button
                key={page}
                onClick={() => goToPage(page)}
                className={`px-3 py-1 rounded text-sm transition-all ${
                  isActive
                    ? "bg-[var(--primary)] text-white font-medium shadow-glow"
                    : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--border-active)] border border-[var(--border-subtle)]"
                }`}
                aria-label={`Go to page ${page}`}
                aria-current={isActive ? "page" : undefined}
              >
                {page}
              </button>
            );
          })}
        </div>

        <div className="sm:hidden px-3 py-1 text-sm text-[var(--text-secondary)]">
          Page {currentPage} of {totalPages}
        </div>

        <button
          onClick={nextPage}
          disabled={!hasNext}
          className="px-3 py-1 bg-[var(--bg-elevated)] text-[var(--text-primary)] rounded border border-[var(--border-subtle)] hover:bg-[var(--border-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          aria-label="Next page"
        >
          Next
        </button>
      </div>
    </div>
  );
}

/**
 * Simple pagination controls (just prev/next, no page numbers)
 * @param {PaginationControlsProps} props
 */
export function SimplePaginationControls({ pagination, className = "" }) {
  if (!pagination || pagination.totalPages === 0) {
    return null;
  }

  const { currentPage, totalPages, hasNext, hasPrev, nextPage, prevPage } = pagination;

  return (
    <div className={`flex items-center justify-between ${className}`}>
      <button
        onClick={prevPage}
        disabled={!hasPrev}
        className="px-4 py-2 bg-[var(--bg-elevated)] text-[var(--text-primary)] rounded border border-[var(--border-subtle)] hover:bg-[var(--border-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Previous
      </button>

      <span className="text-sm text-[var(--text-secondary)]">
        Page {currentPage} of {totalPages}
      </span>

      <button
        onClick={nextPage}
        disabled={!hasNext}
        className="px-4 py-2 bg-[var(--bg-elevated)] text-[var(--text-primary)] rounded border border-[var(--border-subtle)] hover:bg-[var(--border-active)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </div>
  );
}
