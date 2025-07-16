import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('user can register successfully', async ({ page }) => {
    // Navigate to registration
    await page.click('text=Register');
    
    // Fill registration form
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'testpassword123');
    await page.fill('[data-testid="full-name-input"]', 'Test User');
    
    // Submit registration
    await page.click('[data-testid="register-button"]');
    
    // Verify success
    await expect(page.locator('text=Registration successful')).toBeVisible();
  });

  test('user can login successfully', async ({ page }) => {
    // Navigate to login
    await page.click('text=Login');
    
    // Fill login form
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'testpassword123');
    
    // Submit login
    await page.click('[data-testid="login-button"]');
    
    // Verify successful login
    await expect(page.locator('text=Welcome')).toBeVisible();
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('user cannot login with invalid credentials', async ({ page }) => {
    // Navigate to login
    await page.click('text=Login');
    
    // Fill login form with invalid credentials
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'wrongpassword');
    
    // Submit login
    await page.click('[data-testid="login-button"]');
    
    // Verify error message
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });

  test('user can logout successfully', async ({ page }) => {
    // First login
    await page.click('text=Login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'testpassword123');
    await page.click('[data-testid="login-button"]');
    
    // Wait for login to complete
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    
    // Logout
    await page.click('[data-testid="user-menu"]');
    await page.click('text=Logout');
    
    // Verify logout
    await expect(page.locator('text=Login')).toBeVisible();
    await expect(page.locator('[data-testid="user-menu"]')).not.toBeVisible();
  });
});