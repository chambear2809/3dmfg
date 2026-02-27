/* eslint-disable react-refresh/only-export-components */
/**
 * LocaleContext — company locale and currency settings.
 *
 * Fetches /api/v1/settings/company (cookie-auth) once at mount and provides:
 *   { currency_code, locale, updateLocaleSettings }
 *
 * Falls back to USD / en-US when not authenticated or fetch fails.
 *
 * Usage:
 *   const { currency_code, locale } = useLocale();
 *
 * After saving settings in AdminSettings, call updateLocaleSettings() so all
 * components reflect the new locale without a full page reload.
 */
import { createContext, useContext, useState, useEffect, useMemo, useCallback } from "react";
import { API_URL } from "../config/api";

const DEFAULTS = { currency_code: "USD", locale: "en-US" };

const LocaleContext = createContext({ ...DEFAULTS, updateLocaleSettings: () => {} });

export function LocaleProvider({ children }) {
  const [settings, setSettings] = useState(DEFAULTS);

  useEffect(() => {
    let cancelled = false;

    fetch(`${API_URL}/api/v1/settings/company`, { credentials: "include" })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        setSettings({
          currency_code: data.currency_code || DEFAULTS.currency_code,
          locale: data.locale || DEFAULTS.locale,
        });
      })
      .catch(() => {
        // Unauthenticated or network error — keep defaults
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const updateLocaleSettings = useCallback((patch) => {
    setSettings((prev) => ({ ...prev, ...patch }));
  }, []);

  const value = useMemo(
    () => ({ ...settings, updateLocaleSettings }),
    [settings, updateLocaleSettings]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}

export default LocaleContext;
