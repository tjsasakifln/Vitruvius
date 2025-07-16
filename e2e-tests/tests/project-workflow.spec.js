import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Complete Project Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.click('text=Login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'testpassword123');
    await page.click('[data-testid="login-button"]');
    
    // Wait for dashboard to load
    await expect(page.locator('text=Vitruvius Dashboard')).toBeVisible();
  });

  test('complete user journey: create project, upload IFC, view conflicts, provide feedback', async ({ page }) => {
    // Step 1: Create a new project
    await page.click('[data-testid="create-project-button"]');
    await page.fill('[data-testid="project-name-input"]', 'Test BIM Project');
    await page.fill('[data-testid="project-description-input"]', 'A test project for E2E testing');
    await page.click('[data-testid="create-project-submit"]');
    
    // Verify project creation
    await expect(page.locator('text=Test BIM Project')).toBeVisible();
    await expect(page.locator('text=Project created successfully')).toBeVisible();
    
    // Step 2: Upload IFC file
    const fileInput = page.locator('[data-testid="ifc-file-input"]');
    const testIFCPath = path.join(__dirname, '../fixtures/test-model.ifc');
    await fileInput.setInputFiles(testIFCPath);
    
    await page.click('[data-testid="upload-ifc-button"]');
    
    // Verify upload started
    await expect(page.locator('text=IFC file uploaded successfully')).toBeVisible();
    await expect(page.locator('[data-testid="processing-indicator"]')).toBeVisible();
    
    // Step 3: Wait for processing to complete
    await page.waitForSelector('[data-testid="processing-complete"]', { timeout: 60000 });
    
    // Step 4: View the 3D model
    await page.click('[data-testid="view-3d-model-button"]');
    
    // Verify 3D viewer loads
    await expect(page.locator('[data-testid="3d-viewer"]')).toBeVisible();
    await expect(page.locator('canvas')).toBeVisible();
    
    // Step 5: Check for detected conflicts
    await page.click('[data-testid="conflicts-tab"]');
    
    // Verify conflicts are displayed
    await expect(page.locator('[data-testid="conflict-list"]')).toBeVisible();
    
    // Step 6: Click on a conflict
    await page.click('[data-testid="conflict-item"]:first-child');
    
    // Verify conflict details are shown
    await expect(page.locator('[data-testid="conflict-details"]')).toBeVisible();
    await expect(page.locator('text=Recomendações do Motor de Análise Prescritiva')).toBeVisible();
    
    // Step 7: View prescriptive solutions
    await expect(page.locator('[data-testid="solution-list"]')).toBeVisible();
    
    // Step 8: Select a suggested solution
    await page.click('[data-testid="solution-radio"]:first-child');
    
    // Step 9: Provide feedback
    await page.fill('[data-testid="implementation-notes"]', 'This solution worked well for our project');
    await page.click('[data-testid="effectiveness-rating-4"]');
    
    // Submit feedback
    await page.click('[data-testid="submit-feedback-button"]');
    
    // Verify feedback submission
    await expect(page.locator('text=Feedback enviado com sucesso')).toBeVisible();
    
    // Step 10: Mark conflict as resolved
    await page.click('[data-testid="mark-resolved-button"]');
    
    // Verify conflict status update
    await expect(page.locator('[data-testid="conflict-status"]')).toContainText('Resolved');
  });

  test('user can provide custom solution feedback', async ({ page }) => {
    // Navigate to a project with conflicts
    await page.click('[data-testid="project-item"]:first-child');
    await page.click('[data-testid="view-conflicts-button"]');
    
    // Click on a conflict
    await page.click('[data-testid="conflict-item"]:first-child');
    
    // Select custom solution option
    await page.click('[data-testid="custom-solution-radio"]');
    
    // Fill custom solution description
    await page.fill(
      '[data-testid="custom-solution-description"]',
      'I implemented a custom structural modification that addresses the root cause of the conflict'
    );
    
    // Add implementation notes
    await page.fill(
      '[data-testid="implementation-notes"]',
      'Modified the beam connection details and adjusted the column position'
    );
    
    // Rate effectiveness
    await page.click('[data-testid="effectiveness-rating-5"]');
    
    // Submit feedback
    await page.click('[data-testid="submit-feedback-button"]');
    
    // Verify success
    await expect(page.locator('text=Feedback enviado com sucesso')).toBeVisible();
  });

  test('user can navigate between multiple projects', async ({ page }) => {
    // Create multiple projects
    const projectNames = ['Project A', 'Project B', 'Project C'];
    
    for (const name of projectNames) {
      await page.click('[data-testid="create-project-button"]');
      await page.fill('[data-testid="project-name-input"]', name);
      await page.click('[data-testid="create-project-submit"]');
      await expect(page.locator(`text=${name}`)).toBeVisible();
    }
    
    // Navigate between projects
    await page.click('[data-testid="project-list-button"]');
    await expect(page.locator('text=Project A')).toBeVisible();
    await expect(page.locator('text=Project B')).toBeVisible();
    await expect(page.locator('text=Project C')).toBeVisible();
    
    // Click on a specific project
    await page.click('text=Project B');
    await expect(page.locator('[data-testid="project-title"]')).toContainText('Project B');
  });

  test('user can view project statistics and analytics', async ({ page }) => {
    // Navigate to a project with processed data
    await page.click('[data-testid="project-item"]:first-child');
    
    // Click on analytics tab
    await page.click('[data-testid="analytics-tab"]');
    
    // Verify analytics components are visible
    await expect(page.locator('[data-testid="conflict-summary-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="resolution-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="time-to-resolution"]')).toBeVisible();
    
    // Verify key metrics are displayed
    await expect(page.locator('[data-testid="total-conflicts"]')).toBeVisible();
    await expect(page.locator('[data-testid="resolved-conflicts"]')).toBeVisible();
    await expect(page.locator('[data-testid="pending-conflicts"]')).toBeVisible();
  });

  test('user can export project data', async ({ page }) => {
    // Navigate to a project
    await page.click('[data-testid="project-item"]:first-child');
    
    // Click on export button
    await page.click('[data-testid="export-button"]');
    
    // Select export format
    await page.selectOption('[data-testid="export-format-select"]', 'pdf');
    
    // Configure export options
    await page.check('[data-testid="include-conflicts"]');
    await page.check('[data-testid="include-solutions"]');
    await page.check('[data-testid="include-feedback"]');
    
    // Start export
    await page.click('[data-testid="start-export-button"]');
    
    // Wait for export to complete
    await expect(page.locator('[data-testid="export-complete"]')).toBeVisible({ timeout: 30000 });
    
    // Verify download link is available
    await expect(page.locator('[data-testid="download-link"]')).toBeVisible();
  });
});