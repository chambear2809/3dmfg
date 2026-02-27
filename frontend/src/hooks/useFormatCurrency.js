/**
 * useFormatCurrency — locale-aware currency formatting hook.
 *
 * Returns a memoized formatter that uses the company's currency_code and locale
 * from LocaleContext. Falls back to USD / en-US if context is unavailable.
 *
 * Usage:
 *   const formatCurrency = useFormatCurrency();
 *   formatCurrency(1234.56)  // → "$1,234.56" (USD/en-US) or "1.234,56 €" (EUR/de-DE)
 */
import { useCallback } from "react";
import { useLocale } from "../contexts/LocaleContext";

export function useFormatCurrency() {
  const { currency_code, locale } = useLocale();

  return useCallback(
    (n) => {
      if (n == null || !Number.isFinite(Number(n))) return "";
      return new Intl.NumberFormat(locale, {
        style: "currency",
        currency: currency_code,
        maximumFractionDigits: 2,
      }).format(Number(n));
    },
    [currency_code, locale]
  );
}
