import { defineConfig, devices } from '@playwright/test';

/**
 * FilaOps E2E Test Configuration
 *
 * Run tests: npm run test:e2e
 * Run specific: npm run test:e2e -- --grep "customers"
 * Run with UI: npm run test:e2e -- --ui
 */

const reporter = process.env.PLAYWRIGHT_REPORTER || (process.env.CI ? 'line' : 'html');

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // Serial execution for workflow tests
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker to avoid parallel auth issues
  reporter,
  timeout: 60000, // 60s timeout per test

  use: {
    // Use DEV environment - Vite default port 5173
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: process.env.CI ? 'retain-on-failure' : 'on-first-retry',
    screenshot: process.env.CI ? 'only-on-failure' : 'off',
  },

  projects: [
    // Setup project - runs first to authenticate
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
      testDir: './tests/e2e',
    },
    // Main tests - depend on setup and use stored auth
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Use stored auth state from setup
        storageState: './tests/e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    // Walkthrough — self-contained auth, no setup dependency
    {
      name: 'walkthrough',
      testMatch: /walkthrough-screenshots\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    // Load smoke — self-contained auth against the benchmark dataset
    {
      name: 'load-smoke',
      testMatch: /load\/.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Docker containers should be running before tests
  // DEV: docker-compose -f docker-compose.dev.yml up -d
});
