/**
 * useFormatNumber — locale-aware number formatting hook.
 *
 * Returns a memoized formatter using the company locale from LocaleContext.
 * Accepts any Intl.NumberFormat options for flexible formatting.
 *
 * Usage:
 *   const formatNumber = useFormatNumber();
 *   formatNumber(1234.5)                          // → "1,234.5" (en-US)
 *   formatNumber(0.875, { style: "percent" })     // → "87.5%"
 *   formatNumber(1234, { maximumFractionDigits: 0 }) // → "1,234"
 */
import { useCallback } from "react";
import { useLocale } from "../contexts/LocaleContext";

export function useFormatNumber() {
  const { locale } = useLocale();

  return useCallback(
    (n, options = {}) => {
      if (n == null || !Number.isFinite(Number(n))) return "";
      return new Intl.NumberFormat(locale, options).format(Number(n));
    },
    [locale]
  );
}
