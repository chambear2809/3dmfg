import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '../fixtures/auth';

function loadManifest() {
  const manifestJson = process.env.LOADGEN_MANIFEST_JSON;

  if (manifestJson) {
    try {
      return JSON.parse(manifestJson);
    } catch (error) {
      throw new Error(
        `Unable to parse LOADGEN_MANIFEST_JSON: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  const manifestPath = path.resolve(
    process.cwd(),
    process.env.LOADGEN_MANIFEST_PATH || process.env.MANIFEST_PATH || '../scripts/loadgen/manifest.json',
  );

  if (!fs.existsSync(manifestPath)) {
    throw new Error(
      `Loadgen manifest not found at ${manifestPath}. Run backend/scripts/seed_loadgen_data.py first or set LOADGEN_MANIFEST_JSON.`,
    );
  }

  return JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
}

const browserRunId = process.env.RUN_ID || `pw-${Date.now()}`;

test.describe('@load-smoke Loadgen Browser Smoke', () => {
  test.describe.configure({ mode: 'serial' });

  test('@load-smoke dashboard and command center render benchmark data', async ({ authenticatedPage: page }) => {
    loadManifest();

    await page.goto('/admin');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Action Items')).toBeVisible({ timeout: 15000 });

    await page.goto('/admin/command-center');
    await expect(page.getByRole('heading', { name: 'Command Center' })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Today's Summary")).toBeVisible({ timeout: 15000 });
  });

  test('@load-smoke orders and items can find seeded benchmark entities', async ({ authenticatedPage: page }) => {
    const manifest = loadManifest();
    const seededOrder = manifest.orders.representative.ready_to_ship;
    const seededItem = manifest.products.make[0];

    await page.goto(`/admin/orders?search=${seededOrder.order_number}`);
    await expect(page.getByRole('heading', { name: 'Order Management' })).toBeVisible();
    await expect(page.getByText(seededOrder.order_number)).toBeVisible();

    await page.goto(`/admin/orders/${seededOrder.id}`);
    await expect(page.getByText('Order Command Center')).toBeVisible();
    await expect(page.getByRole('heading', { name: `Order: ${seededOrder.order_number}` })).toBeVisible();

    await page.goto('/admin/items');
    await expect(page.getByPlaceholder('Search by SKU, name, or UPC...')).toBeVisible();
    await page.getByPlaceholder('Search by SKU, name, or UPC...').fill(seededItem.sku);
    await expect(page.getByText(seededItem.sku)).toBeVisible();
  });

  test('@load-smoke can create a benchmark-tagged order through the browser session', async ({ authenticatedPage: page }) => {
    const manifest = loadManifest();
    const customerId = manifest.customers[0].id;
    const makeProductId = manifest.products.make[0].id;

    const createdOrder = await page.evaluate(
      async ({ customerId: targetCustomerId, makeProductId: targetProductId, runId, tag }) => {
        const response = await fetch('/api/v1/sales-orders/', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': `${runId}-browser-create`,
          },
          body: JSON.stringify({
            customer_id: targetCustomerId,
            source: 'loadgen',
            source_order_id: `${tag}-${runId}-browser`,
            lines: [
              {
                product_id: targetProductId,
                quantity: 2,
              },
            ],
          }),
        });

        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || `Order creation failed with ${response.status}`);
        }
        return payload;
      },
      {
        customerId,
        makeProductId,
        runId: browserRunId,
        tag: manifest.tag,
      },
    );

    await page.goto(`/admin/orders/${createdOrder.id}`);
    await expect(page.getByText('Order Command Center')).toBeVisible();
    await expect(page.getByRole('heading', { name: `Order: ${createdOrder.order_number}` })).toBeVisible();
  });
});
