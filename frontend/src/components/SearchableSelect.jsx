import { useState, useEffect, useRef } from "react";
import { ChevronDown } from "lucide-react";

export default function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = "Search...",
  displayKey = "name",
  valueKey = "id",
  formatOption = null,
  className = "",
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const sortedOptions = [...options].sort((a, b) =>
    (a[displayKey] || "").localeCompare(b[displayKey] || "")
  );

  const filteredOptions = sortedOptions.filter((opt) => {
    const searchLower = search.toLowerCase();
    const name = (opt[displayKey] || "").toLowerCase();
    const sku = (opt.sku || "").toLowerCase();
    return name.includes(searchLower) || sku.includes(searchLower);
  });

  const selectedOption = options.find(
    (opt) => String(opt[valueKey]) === String(value)
  );
  const displayText = selectedOption
    ? formatOption
      ? formatOption(selectedOption)
      : `${selectedOption[displayKey]} (${selectedOption.sku})`
    : "";

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div
        onClick={() => {
          setIsOpen(true);
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
        className="w-full bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-[var(--text-primary)] cursor-pointer flex items-center justify-between"
      >
        <span className={selectedOption ? "text-[var(--text-primary)]" : "text-[var(--text-muted)]"}>
          {displayText || placeholder}
        </span>
        <ChevronDown size={16} className="text-[var(--text-secondary)]" />
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg shadow-xl max-h-64 overflow-hidden">
          <div className="p-2 border-b border-[var(--border-subtle)]">
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Type to search..."
              className="w-full bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded px-3 py-2 text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--primary)] transition-colors"
              autoFocus
            />
          </div>
          <div className="max-h-48 overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-2 text-[var(--text-muted)] text-sm">
                No results found
              </div>
            ) : (
              filteredOptions.map((opt) => (
                <div
                  key={opt[valueKey]}
                  onClick={() => {
                    onChange(String(opt[valueKey]));
                    setIsOpen(false);
                    setSearch("");
                  }}
                  className={`px-3 py-2 cursor-pointer text-sm transition-colors ${
                    String(opt[valueKey]) === String(value)
                      ? "bg-[var(--primary)]/20 text-[var(--primary-light)]"
                      : "text-[var(--text-primary)] hover:bg-[var(--bg-card)]"
                  }`}
                >
                  {formatOption
                    ? formatOption(opt)
                    : `${opt[displayKey]} (${opt.sku})`}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
