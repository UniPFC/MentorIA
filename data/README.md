# Auto-Ingestion Data Folder

Qualquer arquivo de planilha (.xlsx, .csv) adicionado a esta pasta será detectado automaticamente pela API no momento da inicialização.
Cada arquivo se tornará um **Public Chat Type** (Base de Conhecimento Pública) disponível para todos os usuários.

## Como funciona

1.  **Nomenclatura do Arquivo**: O nome do arquivo determina o título e a descrição do Chat Type.
    *   **Formato**: `Titulo --- Descricao.xlsx`
    *   **Exemplo**: `Finance 2024 --- Relatorio Financeiro Q1.xlsx`
        *   **Nome do Chat**: "Finance 2024"
        *   **Descrição**: "Relatorio Financeiro Q1"
    *   **Fallback**: Se você não utilizar `---`, o nome do arquivo será o título e uma descrição padrão será gerada.
        *   `RH-Politicas.csv` -> **"Rh Politicas"**

2.  **Criação Automática**:  
    *   Se um Chat Type com este nome não existir, ele é criado automaticamente no banco de dados.
    *   A coleção vetorial no **Qdrant** é criada e dimensionada corretamente.
    *   O conteúdo do arquivo é ingerido (linhas viram chunks e geram embeddings).

3.  **Atualizações**:
    *   Se o Chat Type já existir, o arquivo é ignorado para evitar duplicação de dados.
    *   Para forçar atualização de uma base: Delete o Chat Type pela API ou Dashboard Frontend e reinicie a API. O sistema irá reler e ingerir o arquivo do zero.

## Formatos Suportados

*   `.xlsx` (Excel)
*   `.xls` (Excel Legado)
*   `.csv` (Valores Separados por Vírgula)

**Colunas Obrigatórias:** O script espera essencialmente a primeira coluna como `question` (pergunta/título) e a segunda como `answer` (resposta/conteúdo).

---

## 🧹 Ferramenta de Análise e Limpeza (analyze_spreadsheet.py)

Muitas vezes, bases de conhecimento extraídas de PDFs ou fontes sujas podem conter caracteres inválidos, lixos de formatação, "cid:" ou letras soltas no final das alternativas. Para garantir a qualidade do RAG, utilize o script `analyze_spreadsheet.py` **antes** de subir a API para ingestão.

### Como usar

O script analisa a planilha e gera um relatório Markdown detalhando todos os problemas encontrados em cada linha.

**Uso básico (Apenas Análise):**
```bash
python data/analyze_spreadsheet.py "data/NOME_DO_ARQUIVO.xlsx"
```
Isso criará (ou substituirá) um arquivo chamado `relatorio_planilha.md` na pasta `data/` com o diagnóstico completo.

**Uso com Correção Automática:**
Se você quiser que o script tente limpar problemas conhecidos automaticamente (como letras soltas " A.", " B." perdidas no fim das respostas devido a erros de extração OCR), adicione a flag `--clean`:

```bash
python data/analyze_spreadsheet.py "data/NOME_DO_ARQUIVO.xlsx" --clean
```
Neste modo, além de gerar o relatório `relatorio_planilha.md`, o script **sobrescreverá** a planilha original com as linhas corrigidas. Após isso, você pode iniciar o Backend com segurança para uma ingestão de alta qualidade.
