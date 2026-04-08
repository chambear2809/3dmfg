import { test as setup, expect } from '@playwright/test';
import { E2E_CONFIG } from './config';
import * as fs from 'fs';

const authFile = './tests/e2e/.auth/user.json';
const API_BASE_URL = process.env.API_URL || 'http://localhost:8000';

/**
 * Ensure test user exists by calling the seed endpoint.
 * This creates the admin@filaops.test user for authentication.
 */
async function ensureTestUser(): Promise<void> {
  // First cleanup any stale data
  await fetch(`${API_BASE_URL}/api/v1/test/cleanup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  }).catch(() => { /* Ignore cleanup errors */ });

  // Seed the empty scenario which creates the admin user
  const response = await fetch(`${API_BASE_URL}/api/v1/test/seed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario: 'empty' }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to seed test user: ${error}`);
  }
}

/**
 * Check if the stored authenticated session is missing or near expiry.
 * Returns true if the refresh cookie is missing or expires within 7 days.
 */
function isTokenExpiredOrExpiringSoon(): boolean {
  try {
    if (!fs.existsSync(authFile)) {
      return true; // No auth file exists
    }

    const authData = JSON.parse(fs.readFileSync(authFile, 'utf-8'));
    const refreshCookie = authData.cookies?.find(
      (cookie: any) => cookie.name === 'refresh_token'
    );

    if (!refreshCookie) {
      return true; // No session cookie found
    }

    if (!refreshCookie.expires || refreshCookie.expires <= 0) {
      return true; // Session cookie missing an expiry
    }

    const now = Math.floor(Date.now() / 1000);
    const expiresIn = refreshCookie.expires - now;
    const SEVEN_DAYS = 604800;

    if (expiresIn < SEVEN_DAYS) {
      console.log(`[auth] Token expires in ${Math.floor(expiresIn / 86400)} days - re-authenticating`);
      return true;
    }

    return false; // Token is valid
  } catch (error) {
    console.log(`[auth] Error checking token: ${error} - re-authenticating`);
    return true; // On any error, force re-auth
  }
}

setup('authenticate', async ({ page }) => {
  // Skip authentication if token is still valid
  if (!isTokenExpiredOrExpiringSoon()) {
    console.log('[auth] Existing auth token is valid - skipping re-authentication');
    return;
  }

  console.log('[auth] Authenticating test user...');

  // Ensure test user exists before trying to login
  await ensureTestUser();

  // Navigate to login page
  await page.goto('/admin/login');
  await page.waitForLoadState('networkidle');

  // Fill and submit login form
  await page.fill('input[type="email"]', E2E_CONFIG.email);
  await page.fill('input[type="password"]', E2E_CONFIG.password);
  await page.click('button[type="submit"]');

  // Check for login errors before waiting for navigation
  const errorMessage = page.getByText(/incorrect.*password|invalid.*credentials/i);
  const errorVisible = await errorMessage.isVisible({ timeout: 2000 }).catch(() => false);

  if (errorVisible) {
    throw new Error(
      `[auth] Login failed: Test user doesn't exist.\n` +
      `Run: docker-compose -f docker-compose.dev.yml exec backend python scripts/seed_test_data.py`
    );
  }

  // Wait for successful navigation
  await page.waitForURL(/\/admin(?!\/login)/, { timeout: 10000 });

  // Dismiss any promotional modals
  await page.waitForTimeout(500);

  const closeButtons = [
    page.getByRole('button', { name: /don't show|got it|close|dismiss/i }),
    page.locator('button:has-text("×")'),
    page.locator('[aria-label="Close"]'),
  ];

  for (const button of closeButtons) {
    if (await button.isVisible().catch(() => false)) {
      await button.click();
      await page.waitForTimeout(300);
      break; // Only click first visible close button
    }
  }

  // Verify authentication succeeded
  await expect(page.getByText(/dashboard|orders|production/i).first()).toBeVisible({ timeout: 5000 });

  // Save authentication state for reuse
  await page.context().storageState({ path: authFile });

  console.log('[auth] Authentication successful, state saved');
});
