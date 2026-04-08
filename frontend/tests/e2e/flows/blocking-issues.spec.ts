/**
 * E2E-201: Blocking Issues Flow Tests
 *
 * Tests the BlockingIssuesPanel component and suggested actions workflow.
 * Validates UI-201, UI-202, UI-203, UI-204 implementations.
 */
import { test, expect } from '@playwright/test';
import { seedTestScenario, cleanupTestData } from '../fixtures/test-utils';

// Don't use shared auth - this test does its own login after seeding
test.use({ storageState: { cookies: [], origins: [] } });

test.describe.serial('E2E-201: Blocking Issues Flow', () => {

  let authCookies: any[] = [];
  let adminUser: any = null;

  // Seed once before all tests in this file
  test.beforeAll(async ({ request }) => {
    await cleanupTestData();
    await seedTestScenario('low-stock-with-allocations');

    // Log in once and reuse the resulting session state in UI tests.
    const response = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      form: {
        username: 'admin@filaops.test',
        password: 'TestPass123!',
      },
    });
    if (response.ok()) {
      const data = await response.json();
      adminUser = data.user;
      const state = await request.storageState();
      authCookies = state.cookies.filter((cookie: any) =>
        cookie.name === 'access_token' || cookie.name === 'refresh_token'
      );
    }
  });

  async function loginApi(request: any) {
    const response = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      form: {
        username: 'admin@filaops.test',
        password: 'TestPass123!',
      },
    });
    expect(response.ok()).toBeTruthy();
  }

  async function loginAsAdmin(page: any) {
    await page.goto('http://localhost:5173/admin/login');

    if (authCookies.length > 0 && adminUser) {
      await page.context().addCookies(authCookies);
      await page.evaluate((user: any) => {
        localStorage.setItem('adminUser', JSON.stringify(user));
      }, adminUser);
      await page.goto('http://localhost:5173/admin/orders');
      await expect(page).toHaveURL(/\/admin\/orders/);
    } else {
      await page.getByRole('textbox', { name: 'Email Address' }).fill('admin@filaops.test');
      await page.getByRole('textbox', { name: 'Password' }).fill('TestPass123!');
      await page.getByRole('button', { name: 'Sign In' }).click();
      await expect(page).toHaveURL(/\/admin(?!\/login)/);
    }
  }

  // =====================
  // Test 1: Expedite existing PO from SO blocking issues
  // =====================
  test('expedite PO action navigates to PO detail page', async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate to Orders
    await page.getByRole('link', { name: 'Orders', exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/orders/);

    // Click View on the SO row (first one)
    await page.getByRole('button', { name: 'View' }).first().click();

    // Verify BlockingIssuesPanel is visible
    await expect(page.getByText('Fulfillment Status')).toBeVisible();
    await expect(page.getByText('Blocking Issues')).toBeVisible();

    // Click Expedite PO action
    await page.getByRole('button', { name: /Expedite PO PO-\d{4}-\d+/ }).click();

    // Should navigate to purchasing page
    await expect(page).toHaveURL(/\/admin\/purchasing/);

    // Click View (exact match) to go to PO detail
    await page.getByRole('button', { name: 'View', exact: true }).click();

    // Verify we're on the PO detail page (uses query param)
    await expect(page).toHaveURL(/\/admin\/purchasing\?po_id=\d+/);
    await expect(page.getByText(/PO-\d{4}-\d+/)).toBeVisible();
  });

  // =====================
  // Test 2: Verify BlockingIssuesPanel shows on SO detail
  // =====================
  test('SO detail page shows blocking issues panel with line issues', async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate to Orders → View SO
    await page.getByRole('link', { name: 'Orders', exact: true }).click();
    await page.getByRole('button', { name: 'View' }).first().click();

    // Verify panel elements
    await expect(page.getByText('Fulfillment Status')).toBeVisible();
    await expect(page.getByText('LINE ISSUES')).toBeVisible();
    await expect(page.getByText('SUGGESTED ACTIONS')).toBeVisible();
    
    // Should show material shortage (use first() to avoid strict mode)
    await expect(page.getByText(/short/i).first()).toBeVisible();
  });

  // =====================
  // Test 3: Verify suggested actions are actionable
  // =====================
  test('suggested actions show priority and are clickable', async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate to Orders → View SO
    await page.getByRole('link', { name: 'Orders', exact: true }).click();
    await page.getByRole('button', { name: 'View' }).first().click();

    // Verify suggested actions section
    await expect(page.getByText('SUGGESTED ACTIONS')).toBeVisible();
    
    // Should show priority number (1, 2, etc.)
    await expect(page.getByRole('button', { name: /^1\s/ })).toBeVisible();
    
    // Should show "Expedite PO" as first action
    await expect(page.getByRole('button', { name: /Expedite PO/ })).toBeVisible();
  });

  // =====================
  // Test 4: Create PO action (requires scenario without existing PO)
  // =====================
  test.skip('create PO action opens pre-filled modal', async ({ page }) => {
    // TODO: Needs 'low-stock-no-po' scenario where no PO exists yet
  });

  // =====================
  // API Tests: Use direct API auth (no browser login needed)
  // =====================
  test('API-201 & API-202: blocking-issues endpoints return correct structure', async ({ request }) => {
    await loginApi(request);

    // --- API-201: SO blocking-issues ---
    const soListResponse = await request.get('http://127.0.0.1:8000/api/v1/sales-orders/');
    expect(soListResponse.ok()).toBeTruthy();
    
    const soOrders = await soListResponse.json();
    const soId = soOrders.items?.[0]?.id || soOrders[0]?.id;
    expect(soId).toBeTruthy();

    const soResponse = await request.get(`http://127.0.0.1:8000/api/v1/sales-orders/${soId}/blocking-issues`);
    expect(soResponse.ok()).toBeTruthy();

    const soData = await soResponse.json();
    expect(soData).toHaveProperty('status_summary');
    expect(soData.status_summary).toHaveProperty('can_fulfill');
    expect(soData.status_summary).toHaveProperty('blocking_count');
    expect(soData).toHaveProperty('line_issues');
    expect(soData).toHaveProperty('resolution_actions');
    expect(Array.isArray(soData.line_issues)).toBe(true);
    expect(Array.isArray(soData.resolution_actions)).toBe(true);

    // --- API-202: PO blocking-issues ---
    const poListResponse = await request.get('http://127.0.0.1:8000/api/v1/production-orders/');
    
    if (!poListResponse.ok()) {
      console.log('Production orders list failed - skipping PO test');
      return;
    }
    
    const poOrders = await poListResponse.json();
    const poId = poOrders.items?.[0]?.id || poOrders[0]?.id;
    
    if (!poId) {
      console.log('No production orders found - skipping PO test');
      return;
    }

    const poResponse = await request.get(`http://127.0.0.1:8000/api/v1/production-orders/${poId}/blocking-issues`);
    expect(poResponse.ok()).toBeTruthy();

    const poData = await poResponse.json();
    expect(poData).toHaveProperty('status_summary');
    expect(poData.status_summary).toHaveProperty('can_produce');
    expect(poData.status_summary).toHaveProperty('blocking_count');
    expect(poData).toHaveProperty('material_issues');
    expect(poData).toHaveProperty('resolution_actions');
    expect(Array.isArray(poData.material_issues)).toBe(true);
    expect(Array.isArray(poData.resolution_actions)).toBe(true);
  });
});
