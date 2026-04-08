import { SpanKind, SpanStatusCode, trace } from "@opentelemetry/api";

let initialized = false;
let initPromise = null;
let rumModulePromise = null;

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);
const TRACKING_MODES = new Set(["noTracking", "anonymousTracking"]);
const EXPORTER_MODES = new Set(["direct", "otlp"]);
const WORKFLOW_TRACER_NAME = "filaops.browser.workflows";
const URL_ATTRIBUTE_KEYS = new Set([
  "http.url",
  "page.url",
  "url.full",
  "url",
]);
const PATH_ATTRIBUTE_KEYS = new Set([
  "http.route",
  "http.target",
  "page.path",
  "url.path",
]);
const PRIVACY_SENSITIVITY_RULES = [
  { rule: "mask", selector: '[data-rum-mask="true"]' },
  { rule: "mask", selector: '[data-rum-mask="true"] *' },
  { rule: "exclude", selector: '[data-rum-exclude="true"]' },
];
const ROUTE_NORMALIZATION_RULES = [
  [/^\/admin\/orders\/(?!import$)[^/]+$/u, "/admin/orders/:orderId"],
  [/^\/admin\/production\/[^/]+$/u, "/admin/production/:orderId"],
  [/^\/reset-password\/[^/]+$/u, "/reset-password/:token"],
  [
    /^\/admin\/password-reset\/[^/]+\/[^/]+$/u,
    "/admin/password-reset/:action/:token",
  ],
];

function readRuntimeConfig() {
  return window.__FILAOPS_CONFIG__ || {};
}

function readString(config, key, fallback, envFallback = "") {
  const value = config[key];
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (typeof envFallback === "string" && envFallback.trim()) {
    return envFallback.trim();
  }
  return fallback;
}

function readBoolean(config, key, fallback = false, envFallback = "") {
  const value = config[key];
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value !== "string" || !value.trim()) {
    if (typeof envFallback === "string" && envFallback.trim()) {
      return TRUE_VALUES.has(envFallback.trim().toLowerCase());
    }
    return fallback;
  }
  return TRUE_VALUES.has(value.trim().toLowerCase());
}

function readNumber(config, key, fallback, envFallback = "") {
  const value = Number.parseFloat(config[key]);
  if (Number.isFinite(value)) {
    return value;
  }

  const envValue = Number.parseFloat(envFallback);
  return Number.isFinite(envValue) ? envValue : fallback;
}

function clampUnitInterval(value) {
  return Math.max(0, Math.min(1, value));
}

function readTrackingMode(config, key, fallback, envFallback = "") {
  const value = config[key];
  if (typeof value === "string" && TRACKING_MODES.has(value.trim())) {
    return value.trim();
  }
  if (
    typeof envFallback === "string" &&
    envFallback.trim() &&
    TRACKING_MODES.has(envFallback.trim())
  ) {
    return envFallback.trim();
  }
  return fallback;
}

function readExporterMode(config, key, fallback, envFallback = "") {
  const value = config[key];
  if (typeof value === "string" && EXPORTER_MODES.has(value.trim())) {
    return value.trim();
  }
  if (
    typeof envFallback === "string" &&
    envFallback.trim() &&
    EXPORTER_MODES.has(envFallback.trim())
  ) {
    return envFallback.trim();
  }
  return fallback;
}

function isUrlLikeAttribute(key) {
  return URL_ATTRIBUTE_KEYS.has(key) || key.endsWith(".url");
}

function isPathLikeAttribute(key) {
  return PATH_ATTRIBUTE_KEYS.has(key) || key.endsWith(".route");
}

export function normalizeRoutePath(pathname) {
  if (typeof pathname !== "string" || !pathname.trim()) {
    return pathname;
  }

  const normalizedPath = pathname.trim();
  for (const [pattern, replacement] of ROUTE_NORMALIZATION_RULES) {
    if (pattern.test(normalizedPath)) {
      return replacement;
    }
  }
  return normalizedPath;
}

function sanitizeUrlValue(value) {
  if (typeof value !== "string" || !value.trim()) {
    return value;
  }

  try {
    const parsed = new URL(value, window.location.origin);
    parsed.pathname = normalizeRoutePath(parsed.pathname);
    parsed.search = "";
    parsed.hash = "";

    const isAbsolute = /^[a-z][a-z0-9+.-]*:\/\//iu.test(value);
    return isAbsolute ? parsed.toString() : `${parsed.pathname}${parsed.search}`;
  } catch {
    return normalizeRoutePath(value.split(/[?#]/u, 1)[0]);
  }
}

function sanitizeAttributeValue(key, value) {
  if (typeof value !== "string") {
    return value;
  }
  if (isUrlLikeAttribute(key)) {
    return sanitizeUrlValue(value);
  }
  if (isPathLikeAttribute(key)) {
    return normalizeRoutePath(value.split(/[?#]/u, 1)[0]);
  }
  return value;
}

export function sanitizeRumAttributes(attributes) {
  if (!attributes || typeof attributes !== "object") {
    return attributes;
  }

  for (const [key, value] of Object.entries(attributes)) {
    attributes[key] = sanitizeAttributeValue(key, value);
  }
  return attributes;
}

function buildRumGlobalAttributes({
  applicationName,
  deploymentEnvironment,
  version,
}) {
  return {
    "app.name": applicationName,
    "app.version": version,
    "deployment.environment.name": deploymentEnvironment,
  };
}

function readOtlpEndpoint(config) {
  return readString(
    config,
    "SPLUNK_RUM_BEACON_ENDPOINT",
    "",
    import.meta.env.VITE_SPLUNK_RUM_BEACON_ENDPOINT ||
      import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT
  ) || readString(config, "OTEL_EXPORTER_OTLP_ENDPOINT", "", "");
}

export function buildRumExporterOptions(exporterMode, otlpEndpoint = "") {
  const exporter = {
    onAttributesSerializing: sanitizeRumAttributes,
  };

  if (exporterMode === "otlp") {
    exporter.otlp = true;
    if (otlpEndpoint) {
      exporter.beaconEndpoint = otlpEndpoint;
    }
  }

  return exporter;
}

function buildSpaMetricsConfig(otlpEndpoint) {
  const ignoreUrls = [];
  if (otlpEndpoint) {
    ignoreUrls.push(otlpEndpoint);
  }

  return {
    ignoreUrls,
    maxResourcesToWatch: 100,
    quietTime: 1000,
  };
}

async function getRumModule() {
  if (!rumModulePromise) {
    rumModulePromise = import("@splunk/otel-web").catch((error) => {
      rumModulePromise = null;
      throw error;
    });
  }
  return rumModulePromise;
}

export async function setBrowserRumGlobalAttributes(attributes) {
  if (
    typeof window === "undefined" ||
    !attributes ||
    (!initialized && !initPromise)
  ) {
    return;
  }

  try {
    await (initPromise || Promise.resolve());
    const rumModule = await getRumModule();
    rumModule?.SplunkRum?.setGlobalAttributes(attributes);
  } catch {
    // Ignore telemetry-only failures.
  }
}

export function recordWorkflowEvent(name, attributes = {}, options = {}) {
  if (typeof window === "undefined" || !name) {
    return;
  }

  const tracer = trace.getTracer(WORKFLOW_TRACER_NAME);
  const span = tracer.startSpan(name, { kind: SpanKind.INTERNAL });

  try {
    span.setAttribute("app.workflow.name", name);
    span.setAttribute("app.route", normalizeRoutePath(window.location.pathname));

    for (const [key, value] of Object.entries(attributes)) {
      if (
        value === undefined ||
        value === null ||
        (typeof value === "number" && !Number.isFinite(value))
      ) {
        continue;
      }
      if (
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
      ) {
        span.setAttribute(key, value);
      }
    }

    if (options.error) {
      span.recordException(options.error);
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: options.error?.message || "workflow error",
      });
      span.setAttribute("app.workflow.status", "error");
    } else {
      span.setAttribute("app.workflow.status", "ok");
    }
  } finally {
    span.end();
  }
}

export function initBrowserTracing() {
  if (initialized || initPromise || typeof window === "undefined") {
    return;
  }

  const config = readRuntimeConfig();
  const enabled = readBoolean(
    config,
    "SPLUNK_RUM_ENABLED",
    false,
    import.meta.env.VITE_SPLUNK_RUM_ENABLED
  );
  if (!enabled) {
    return;
  }

  const realm = readString(
    config,
    "SPLUNK_RUM_REALM",
    "",
    import.meta.env.VITE_SPLUNK_RUM_REALM
  );
  const rumAccessToken = readString(
    config,
    "SPLUNK_RUM_ACCESS_TOKEN",
    "",
    import.meta.env.VITE_SPLUNK_RUM_ACCESS_TOKEN
  );

  if (!realm || !rumAccessToken) {
    console.warn("Splunk RUM is enabled but missing realm or access token.");
    return;
  }

  initialized = true;

  const applicationName = readString(
    config,
    "SPLUNK_RUM_APP_NAME",
    "filaops-frontend",
    import.meta.env.VITE_SPLUNK_RUM_APP_NAME
  );
  const deploymentEnvironment = readString(
    config,
    "APP_ENV",
    "production",
    import.meta.env.VITE_APP_ENV
  );
  const version = readString(
    config,
    "APP_VERSION",
    "unknown",
    import.meta.env.VITE_APP_VERSION
  );
  const debug = readBoolean(
    config,
    "SPLUNK_RUM_DEBUG",
    false,
    import.meta.env.VITE_SPLUNK_RUM_DEBUG
  );
  const exporterMode = readExporterMode(
    config,
    "SPLUNK_RUM_EXPORTER",
    "direct",
    import.meta.env.VITE_SPLUNK_RUM_EXPORTER
  );
  const sessionReplayEnabled = readBoolean(
    config,
    "SPLUNK_RUM_SESSION_REPLAY_ENABLED",
    false,
    import.meta.env.VITE_SPLUNK_RUM_SESSION_REPLAY_ENABLED
  );
  const maskAllText = readBoolean(
    config,
    "SPLUNK_RUM_MASK_ALL_TEXT",
    false,
    import.meta.env.VITE_SPLUNK_RUM_MASK_ALL_TEXT
  );
  const maskAllInputs = readBoolean(
    config,
    "SPLUNK_RUM_MASK_ALL_INPUTS",
    true,
    import.meta.env.VITE_SPLUNK_RUM_MASK_ALL_INPUTS
  );
  const sessionSampleRatio = clampUnitInterval(
    readNumber(
      config,
      "SPLUNK_RUM_SESSION_SAMPLE_RATIO",
      1,
      import.meta.env.VITE_SPLUNK_RUM_SESSION_SAMPLE_RATIO
    )
  );
  const trackingMode = readTrackingMode(
    config,
    "SPLUNK_RUM_USER_TRACKING_MODE",
    "noTracking",
    import.meta.env.VITE_SPLUNK_RUM_USER_TRACKING_MODE
  );
  const otlpEndpoint = readOtlpEndpoint(config);

  initPromise = Promise.all([
    getRumModule(),
    sessionReplayEnabled
      ? import("@splunk/otel-web-session-recorder")
      : Promise.resolve(null),
  ])
    .then(([rumModule, sessionRecorderModule]) => {
      const { SplunkRum, SessionBasedSampler } = rumModule;

      SplunkRum.init({
        realm,
        rumAccessToken,
        applicationName,
        deploymentEnvironment,
        version,
        debug,
        globalAttributes: buildRumGlobalAttributes({
          applicationName,
          deploymentEnvironment,
          version,
        }),
        user: {
          trackingMode,
        },
        privacy: {
          maskAllText,
          sensitivityRules: PRIVACY_SENSITIVITY_RULES,
        },
        tracer: {
          sampler: new SessionBasedSampler({
            ratio: sessionSampleRatio,
          }),
        },
        exporter: buildRumExporterOptions(exporterMode, otlpEndpoint),
        spaMetrics: buildSpaMetricsConfig(
          exporterMode === "otlp" ? otlpEndpoint : ""
        ),
        instrumentations: {
          connectivity: false,
          socketio: false,
          visibility: false,
          websocket: false,
        },
      });

      if (!sessionReplayEnabled || !sessionRecorderModule?.default) {
        return;
      }

      sessionRecorderModule.default.init({
        realm,
        rumAccessToken,
        debug,
        logLevel: debug ? "info" : "warn",
        maskAllInputs,
        maskAllText,
        sensitivityRules: PRIVACY_SENSITIVITY_RULES,
        features: {
          backgroundService: false,
          canvas: false,
          iframes: false,
          video: false,
        },
      });
    })
    .catch((error) => {
      initialized = false;
      console.warn("Splunk RUM initialization failed.", error);
    })
    .finally(() => {
      initPromise = null;
    });
}
