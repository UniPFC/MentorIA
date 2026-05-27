import { test as setup, expect } from '@playwright/test';

// Define onde o token e os cookies serão armazenados
const authFile = 'playwright/.auth/user.json';

setup('Autenticar usuário do sistema', async ({ page }) => {
  const email = process.env.SYSTEM_USER_EMAIL || 'system@techstein.ai';
  const password = process.env.SYSTEM_USER_PASSWORD || 'change-this-password';

  await page.goto('/login');
  await page.getByPlaceholder('seu@email.com').fill(email);
  await page.getByPlaceholder('Mínimo 8 caracteres').fill(password);
  
  // Envia via teclado para evitar a race condition do WebKit
  await page.getByPlaceholder('Mínimo 8 caracteres').press('Enter');

  // Aguarda o roteamento acontecer com sucesso
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });

  // Salva o localStorage e os Cookies (authToken, de acordo com o seu api.ts)
  await page.context().storageState({ path: authFile });
});