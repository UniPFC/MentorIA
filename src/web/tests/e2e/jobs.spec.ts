import { test, expect } from '@playwright/test';

test.describe('Módulo de Histórico de Uploads - Jobs', () => {
  test('Deve renderizar a tabela de jobs com os status simulados via Mock', async ({ page }) => {
    
    // 1. INTERCEPTAÇÃO: Quando o Next.js chamar a rota de listagem de jobs, injetamos um cenário controlado
    await page.route('**/api/v1/upload/jobs/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: "job-01-sucesso",
            filename: "relatorio_financeiro_2025.csv",
            status: "completed", // Correspondente a Concluído
            created_at: "2026-05-27T14:30:00Z",
            error_message: null
          },
          {
            id: "job-02-falha",
            filename: "dados_corrompidos.xlsx",
            status: "failed", // Correspondente a Falhou
            created_at: "2026-05-27T15:00:00Z",
            error_message: "Formato de arquivo inválido ou estrutura corrompida"
          }
        ])
      });
    });

    // 2. Navegação direta para a rota de histórico (graças ao storageState global ele já abre logado)
    await page.goto('/dashboard/jobs');

    // 3. ASSERÇÕES VISUAIS DE COMPONENTES (O que o seu líder exigiu)
    // Valida se o título da página ou cabeçalho da tabela está visível
    const tableHeader = page.locator('text=Histórico de Uploads').or(page.locator('text=Arquivo'));
    await expect(tableHeader.first()).toBeVisible({ timeout: 5000 });

    // Verifica se os nomes dos arquivos fictícios injetados pelo Mock foram renderizados na tabela
    await expect(page.locator('text=relatorio_financeiro_2025.csv')).toBeVisible();
    await expect(page.locator('text=dados_corrompidos.xlsx')).toBeVisible();

    // Valida se as strings de status mapeadas pelo frontend aparecem associadas aos elementos
    // O Next.js provavelmente converte 'completed' para 'Concluído' ou exibe uma badge equivalente
    const statusSuccess = page.locator('text=concluído').or(page.locator('text=completed')).first();
    const statusFailed = page.locator('text=falhou').or(page.locator('text=failed')).first();
    
    await expect(statusSuccess).toBeVisible();
    await expect(statusFailed).toBeVisible();
  });
});