import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const manifestPath = __ENV.MANIFEST_PATH || 'scripts/loadgen/manifest.json';
const manifest = JSON.parse(open(manifestPath));

const baseUrl = ((__ENV.BASE_URL || 'http://127.0.0.1:8000')).replace(/\/$/, '');
const apiBaseUrl = ((__ENV.API_BASE_URL || `${baseUrl}/api/v1`)).replace(/\/$/, '');
const adminEmail = __ENV.LOADGEN_ADMIN_EMAIL || __ENV.ADMIN_EMAIL || manifest.admin.email;
const adminPassword = __ENV.LOADGEN_ADMIN_PASSWORD || __ENV.ADMIN_PASSWORD || 'LoadgenPass123!';
const workloadMode = (__ENV.WORKLOAD || 'all').toLowerCase().replace(/_/g, '-');
const runId = __ENV.RUN_ID || `lg-${Math.floor(Date.now() / 1000)}`;
const cookiePoolSize = Number(__ENV.COOKIE_POOL_SIZE || 3);
const serviceMapDuration = __ENV.SERVICE_MAP_DURATION || '4m';
const serviceMapVus = Math.max(1, Number(__ENV.SERVICE_MAP_VUS || 2) || 2);
const serviceMapSleepMinSeconds = Math.max(0, Number(__ENV.SERVICE_MAP_SLEEP_MIN_SECONDS || 1) || 0);
const serviceMapSleepMaxSeconds = Math.max(
  serviceMapSleepMinSeconds,
  Number(__ENV.SERVICE_MAP_SLEEP_MAX_SECONDS || 2) || serviceMapSleepMinSeconds,
);

const ordersCreated = new Counter('loadgen_orders_created');
const productionOrdersCreated = new Counter('loadgen_production_orders_created');
const businessLatency = new Trend('loadgen_business_latency', true);

function mergeObjects() {
  const merged = {};

  for (let i = 0; i < arguments.length; i += 1) {
    const source = arguments[i] || {};
    const keys = Object.keys(source);

    for (let j = 0; j < keys.length; j += 1) {
      const key = keys[j];
      merged[key] = source[key];
    }
  }

  return merged;
}

function scenarioDefinition() {
  const scenarios = {};
  const serviceMap = {
    executor: 'constant-vus',
    exec: 'service_map_flow',
    vus: serviceMapVus,
    duration: serviceMapDuration,
  };

  const read = {
    executor: 'ramping-vus',
    exec: 'read_heavy',
    stages: [
      { duration: '2m', target: 30 },
      { duration: '5m', target: 30 },
      { duration: '1m', target: 0 },
    ],
  };

  const mixed = {
    executor: 'ramping-vus',
    exec: 'mixed_crud',
    stages: [
      { duration: '1m', target: 15 },
      { duration: '4m', target: 15 },
      { duration: '1m', target: 0 },
    ],
  };

  const write = {
    executor: 'ramping-vus',
    exec: 'write_stress',
    stages: [
      { duration: '1m', target: 5 },
      { duration: '3m', target: 5 },
      { duration: '1m', target: 0 },
    ],
  };

  if (workloadMode === 'read') {
    scenarios.read = read;
    return scenarios;
  }
  if (workloadMode === 'mixed') {
    scenarios.mixed = mixed;
    return scenarios;
  }
  if (workloadMode === 'write') {
    scenarios.write = write;
    return scenarios;
  }
  if (workloadMode === 'service-map') {
    scenarios.service_map = serviceMap;
    return scenarios;
  }

  scenarios.read = read;
  scenarios.mixed = mergeObjects(mixed, { startTime: '8m' });
  scenarios.write = mergeObjects(write, { startTime: '14m' });
  return scenarios;
}

export const options = {
  scenarios: scenarioDefinition(),
  thresholds: {
    'http_req_failed{workload:service_map}': ['rate<0.05'],
    'http_req_duration{workload:service_map}': ['p(95)<5000'],
    'http_req_failed{workload:read}': ['rate<0.01'],
    'http_req_duration{workload:read}': ['p(95)<1500'],
    'http_req_failed{workload:mixed}': ['rate<0.02'],
    'http_req_duration{workload:mixed}': ['p(95)<2000'],
    'http_req_failed{workload:write}': ['rate<0.05'],
    'http_req_duration{workload:write}': ['p(95)<3000'],
    checks: ['rate>0.98'],
  },
};

function representativeOrders() {
  return Object.values(manifest.orders.representative || {});
}

function normalizeBaseUrl(value) {
  return (value || '').replace(/\/$/, '');
}

function serviceMapProbeTargets() {
  return [
    { name: 'asset_service', url: normalizeBaseUrl(__ENV.ASSET_SERVICE_BASE_URL) },
    { name: 'order_ingest', url: normalizeBaseUrl(__ENV.ORDER_INGEST_BASE_URL) },
    { name: 'pricing_service', url: normalizeBaseUrl(__ENV.PRICING_SERVICE_BASE_URL) },
    { name: 'notification_service', url: normalizeBaseUrl(__ENV.NOTIFICATION_SERVICE_BASE_URL) },
  ].filter((target) => target.url);
}

function serviceMapProductSku() {
  const groups = [
    manifest.products.make,
    manifest.products.buy,
    manifest.products.components,
    manifest.products.materials,
  ];

  for (let groupIndex = 0; groupIndex < groups.length; groupIndex += 1) {
    const group = groups[groupIndex];
    if (Array.isArray(group) && group.length > 0 && group[0].sku) {
      return group[(__ITER + groupIndex) % group.length].sku;
    }
  }

  throw new Error('Loadgen manifest does not contain a product SKU for service-map imports.');
}

function pick(list, indexOffset = 0) {
  return list[(__ITER + indexOffset) % list.length];
}

function makeRequestId(workload, suffix) {
  return `${runId}-${workload}-vu${__VU}-iter${__ITER}-${suffix}`;
}

function sessionFor(data) {
  return data.sessions[(__VU - 1) % data.sessions.length];
}

function cookieHeader(session) {
  return `access_token=${session.accessToken}`;
}

function requestParams(data, workload, suffix, extra = {}) {
  return mergeObjects(extra, {
    headers: mergeObjects(extra.headers, {
      Cookie: cookieHeader(sessionFor(data)),
      'User-Agent': `filaops-loadgen/${workload}`,
      'X-Request-ID': makeRequestId(workload, suffix),
    }),
    tags: mergeObjects(extra.tags, {
      workload,
    }),
  });
}

function directRequestParams(workload, suffix, extra = {}) {
  return mergeObjects(extra, {
    headers: mergeObjects(extra.headers, {
      'User-Agent': `filaops-loadgen/${workload}`,
      'X-Request-ID': makeRequestId(workload, suffix),
    }),
    tags: mergeObjects(extra.tags, {
      workload,
    }),
  });
}

function checkJson(response, label) {
  return check(response, {
    [`${label} status is 2xx`]: (res) => res.status >= 200 && res.status < 300,
    [`${label} returned body`]: (res) => !!res.body,
  });
}

function batchGet(data, workload, requests) {
  const responses = http.batch(
    requests.map((request, index) => ({
      method: 'GET',
      url: `${apiBaseUrl}${request.path}`,
      params: requestParams(data, workload, `batch-${index}`, {
        tags: { endpoint: request.endpoint || request.path },
      }),
    })),
  );

  responses.forEach((response, index) => {
    checkJson(response, `${workload}-${index}`);
  });
  return responses;
}

function csvCell(value) {
  const text = String(value ?? '');
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function buildServiceMapCsv() {
  const sku = serviceMapProductSku();
  const orderId = `${manifest.tag || 'LG'}-SM-${runId}-${__VU}-${__ITER}-${Date.now()}`;
  const orderDate = new Date().toISOString().slice(0, 10);
  const emailLocalPart = `${runId}-${__VU}-${__ITER}-${Date.now()}`.toLowerCase().replace(/[^a-z0-9-]/g, '-');
  const header = [
    'Order ID',
    'Order Date',
    'Order Status',
    'Payment Status',
    'Customer Email',
    'Customer Name',
    'Product SKU',
    'Quantity',
    'Unit Price',
    'Shipping Cost',
    'Tax Amount',
    'Shipping Address Line 1',
    'Shipping City',
    'Shipping State',
    'Shipping Zip',
    'Shipping Country',
    'Customer Notes',
  ];
  const row = [
    orderId,
    orderDate,
    'pending',
    'paid',
    `servicemap+${emailLocalPart}@filaops.local`,
    'Service Map Loadgen',
    sku,
    '1',
    '19.99',
    '5.00',
    '1.50',
    '100 Observability Way',
    'New York',
    'NY',
    '10001',
    'USA',
    `service-map import ${runId}`,
  ];

  return `${header.map(csvCell).join(',')}\n${row.map(csvCell).join(',')}\n`;
}

function importOrdersCsv(data, workload, csvText) {
  const response = http.post(
    `${apiBaseUrl}/admin/orders/import?create_customers=true&source=loadgen`,
    {
      file: http.file(csvText, `${workload}-${runId}-${__VU}-${__ITER}.csv`, 'text/csv'),
    },
    requestParams(data, workload, 'order-import', {
      tags: { endpoint: 'admin-orders-import' },
    }),
  );

  check(response, {
    [`${workload} order import succeeded`]: (res) => res.status === 200,
  });

  if (response.status !== 200) {
    return null;
  }

  const payload = response.json();
  const created = Number(payload.created || 0);
  if (created > 0) {
    ordersCreated.add(created, { workload });
  }
  return payload;
}

function createOrder(data, workload, { customerId, productIds }) {
  const body = JSON.stringify({
    customer_id: customerId,
    source: 'loadgen',
    source_order_id: `${manifest.tag}-${runId}-${workload}-${__VU}-${__ITER}-${Date.now()}`,
    shipping_cost: 8.5,
    lines: productIds.map((productId, index) => ({
      product_id: productId,
      quantity: index === 0 ? 2 : 1,
    })),
  });

  const response = http.post(
    `${apiBaseUrl}/sales-orders/`,
    body,
    requestParams(data, workload, 'create-order', {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'sales-orders-create' },
    }),
  );
  check(response, {
    [`${workload} create order succeeded`]: (res) => res.status === 201,
  });
  if (response.status !== 201) {
    return null;
  }

  ordersCreated.add(1, { workload });
  return response.json();
}

function patchOrderStatus(data, workload, orderId, status) {
  const response = http.patch(
    `${apiBaseUrl}/sales-orders/${orderId}/status`,
    JSON.stringify({ status }),
    requestParams(data, workload, 'status-update', {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'sales-orders-status' },
    }),
  );
  check(response, {
    [`${workload} status update ${status}`]: (res) => res.status >= 200 && res.status < 300,
  });
  return response;
}

function generateProductionOrders(data, workload, orderId) {
  const response = http.post(
    `${apiBaseUrl}/sales-orders/${orderId}/generate-production-orders`,
    null,
    requestParams(data, workload, 'generate-po', {
      tags: { endpoint: 'sales-orders-generate-production-orders' },
    }),
  );
  check(response, {
    [`${workload} production generation succeeded`]: (res) => res.status >= 200 && res.status < 300,
  });
  if (response.status >= 200 && response.status < 300) {
    const payload = response.json();
    const created = Array.isArray(payload.created_orders) ? payload.created_orders.length : 0;
    if (created > 0) {
      productionOrdersCreated.add(created, { workload });
    }
  }
  return response;
}

function getOrderDetail(data, workload, orderId, suffix = 'detail') {
  const response = http.get(
    `${apiBaseUrl}/sales-orders/${orderId}`,
    requestParams(data, workload, suffix, {
      tags: { endpoint: 'sales-orders-detail' },
    }),
  );
  checkJson(response, `${workload}-order-detail`);
  return response;
}

export function setup() {
  const sessions = [];

  for (let index = 0; index < cookiePoolSize; index += 1) {
    const response = http.post(
      `${apiBaseUrl}/auth/login`,
      {
        username: adminEmail,
        password: adminPassword,
      },
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'User-Agent': 'filaops-loadgen/setup',
          'X-Request-ID': `${runId}-setup-login-${index}`,
        },
      },
    );

    check(response, {
      [`setup login ${index} succeeded`]: (res) => res.status === 200,
      [`setup login ${index} returned auth cookie`]: (res) => !!(res.cookies.access_token && res.cookies.access_token[0]),
    });

    if (response.status !== 200 || !(response.cookies.access_token && response.cookies.access_token[0])) {
      throw new Error(`Unable to authenticate loadgen session ${index}.`);
    }

    sessions.push({
      accessToken: response.cookies.access_token[0].value,
    });
  }

  const probe = http.get(
    `${apiBaseUrl}/system/info`,
    {
      headers: {
        Cookie: `access_token=${sessions[0].accessToken}`,
        'User-Agent': 'filaops-loadgen/setup',
        'X-Request-ID': `${runId}-setup-probe`,
      },
    },
  );
  check(probe, {
    'setup probe succeeded': (res) => res.status === 200,
  });

  return { sessions };
}

export function read_heavy(data) {
  const startedAt = Date.now();

  group('read-heavy core surfaces', () => {
    batchGet(data, 'read', [
      { path: '/system/info', endpoint: 'system-info' },
      { path: '/admin/dashboard/summary', endpoint: 'dashboard-summary' },
      { path: '/admin/dashboard/recent-orders?limit=5', endpoint: 'dashboard-recent-orders' },
      { path: '/admin/dashboard/sales-trend?period=MTD', endpoint: 'dashboard-sales-trend' },
      { path: '/command-center/summary', endpoint: 'command-center-summary' },
      { path: '/command-center/action-items', endpoint: 'command-center-action-items' },
      { path: '/command-center/resources', endpoint: 'command-center-resources' },
    ]);
  });

  group('read-heavy order and inventory views', () => {
    batchGet(data, 'read', [
      {
        path: '/sales-orders/?include_fulfillment=true&limit=100&sort_by=fulfillment_priority&sort_order=asc',
        endpoint: 'sales-orders-list',
      },
      { path: '/items?limit=100&active_only=true', endpoint: 'items-list' },
      { path: '/items/stats', endpoint: 'items-stats' },
      { path: '/purchase-orders?status=ordered&limit=25', endpoint: 'purchase-orders-list' },
      { path: '/invoices/summary', endpoint: 'invoice-summary' },
    ]);
  });

  const detailOrder = pick(representativeOrders(), 1);
  getOrderDetail(data, 'read', detailOrder.id, 'detail-primary');

  const fulfillmentResponse = http.get(
    `${apiBaseUrl}/sales-orders/${detailOrder.id}/fulfillment-status`,
    requestParams(data, 'read', 'fulfillment', {
      tags: { endpoint: 'sales-orders-fulfillment-status' },
    }),
  );
  checkJson(fulfillmentResponse, 'read-fulfillment-status');

  businessLatency.add(Date.now() - startedAt, { workload: 'read' });
  sleep(1 + Math.random() * 2);
}

function uploadAndDeleteAsset(data, workload) {
  const assetTag = `${runId}-${__VU}-${__ITER}-${Date.now()}`;
  const payload = `asset-sm-${assetTag}`;
  const filename = `sm-${assetTag}.png`;

  const uploadResponse = http.post(
    `${apiBaseUrl}/admin/uploads/product-image`,
    {
      file: http.file(payload, filename, 'image/png'),
    },
    requestParams(data, workload, 'asset-upload', {
      tags: { endpoint: 'admin-uploads-product-image' },
    }),
  );

  check(uploadResponse, {
    [`${workload} asset upload succeeded`]: (res) => res.status === 200,
  });

  if (uploadResponse.status !== 200) {
    return;
  }

  const uploadData = uploadResponse.json();
  const assetKey = uploadData.filename || '';

  if (assetKey) {
    const deleteResponse = http.del(
      `${apiBaseUrl}/admin/uploads/product-image/${assetKey}`,
      null,
      requestParams(data, workload, 'asset-delete', {
        tags: { endpoint: 'admin-uploads-product-image-delete' },
      }),
    );
    check(deleteResponse, {
      [`${workload} asset delete succeeded`]: (res) => res.status >= 200 && res.status < 300,
    });
  }
}

function probeServiceMapRoots() {
  const targets = serviceMapProbeTargets();
  if (targets.length === 0) {
    return;
  }

  const responses = http.batch(
    targets.map((target, index) => ({
      method: 'GET',
      url: `${target.url}/`,
      params: directRequestParams('service_map', `root-probe-${index}`, {
        tags: {
          endpoint: `${target.name}-root`,
          target_service: target.name,
        },
      }),
    })),
  );

  responses.forEach((response, index) => {
    const target = targets[index];
    checkJson(response, `service_map-${target.name}-root`);
  });
}

export function service_map_flow(data) {
  const startedAt = Date.now();

  group('service-map direct service probes', () => {
    probeServiceMapRoots();
  });

  group('service-map order import', () => {
    const probe = http.get(
      `${apiBaseUrl}/system/info`,
      requestParams(data, 'service_map', 'probe', {
        tags: { endpoint: 'system-info' },
      }),
    );
    check(probe, {
      'service_map probe succeeded': (res) => res.status === 200,
    });

    importOrdersCsv(data, 'service_map', buildServiceMapCsv());
  });

  group('service-map asset cycle', () => {
    uploadAndDeleteAsset(data, 'service_map');
  });

  businessLatency.add(Date.now() - startedAt, { workload: 'service_map' });
  sleep(serviceMapSleepMinSeconds + Math.random() * (serviceMapSleepMaxSeconds - serviceMapSleepMinSeconds));
}

export function mixed_crud(data) {
  const startedAt = Date.now();

  batchGet(data, 'mixed', [
    { path: '/admin/dashboard/summary', endpoint: 'dashboard-summary' },
    { path: '/sales-orders/?include_fulfillment=true&limit=50&sort_by=order_date&sort_order=desc', endpoint: 'sales-orders-list' },
  ]);

  const customer = pick(manifest.customers);
  const makeProduct = pick(manifest.products.make);
  const buyProduct = pick(manifest.products.buy, 1);
  const createdOrder = createOrder(data, 'mixed', {
    customerId: customer.id,
    productIds: [makeProduct.id, buyProduct.id],
  });

  if (createdOrder) {
    getOrderDetail(data, 'mixed', createdOrder.id, 'detail-after-create');
    patchOrderStatus(data, 'mixed', createdOrder.id, 'confirmed');
    getOrderDetail(data, 'mixed', createdOrder.id, 'detail-after-confirm');
  }

  businessLatency.add(Date.now() - startedAt, { workload: 'mixed' });
  sleep(1 + Math.random());
}

export function write_stress(data) {
  const startedAt = Date.now();

  const customer = pick(manifest.customers, 2);
  const makeProduct = pick(manifest.products.make, 1);
  const createdOrder = createOrder(data, 'write', {
    customerId: customer.id,
    productIds: [makeProduct.id],
  });

  if (createdOrder) {
    generateProductionOrders(data, 'write', createdOrder.id);
    patchOrderStatus(data, 'write', createdOrder.id, 'confirmed');
    getOrderDetail(data, 'write', createdOrder.id, 'detail-after-write');
  }

  businessLatency.add(Date.now() - startedAt, { workload: 'write' });
  sleep(0.5 + Math.random());
}
