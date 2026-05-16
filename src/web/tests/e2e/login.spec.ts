import { test, expect } from '@playwright/test';

test.describe('Fluxo de Autenticação', () => {
  test('Deve realizar login com sucesso e ir para o Dashboard', async ({ page }) => {
    // 1. O robô acessa a página de login
    await page.goto('http://localhost:3000/login');

    // 2. O robô procura os campos na tela como um humano faria e digita as credenciais
    await page.getByPlaceholder('seu@email.com').fill('tayto.moonstar@gmail.com'); 
    await page.getByPlaceholder('Mínimo 8 caracteres').fill('Huguinho***');

    // 3. O robô clica no botão de submit
    // IMPORTANTE: Troque 'Entrar' pelo texto exato que está escrito no seu botão de Login
    await page.getByRole('button', { name: 'Entrar' }).click();

    // 4. A ASSERÇÃO (O momento da verdade)
    // O robô espera que, após o clique, a URL mude para o dashboard
    await expect(page).toHaveURL('http://localhost:3000/dashboard');
    
    // Opcional: Verificar se algum elemento específico do dashboard carregou
    await expect(page.locator('text=Bem-vindo ao MentorIA')).toBeVisible();
  });
});