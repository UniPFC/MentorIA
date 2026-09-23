# Guia de Deploy Efemero Seguro (MentorIA)

Este guia documenta o funcionamento da pipeline de CI/CD para o TCC, que provisiona a infraestrutura do MentorIA na nuvem (AWS) de forma automatizada, segura e com **custo zero quando inativa**.

## Como funciona o Deploy Efemero?

1. **Gatilho:** O deploy acontece quando voce cria uma **Tag** no GitHub comecando com `v` (ex: `v1.0.0`). O GitHub Actions roda todos os testes e, se passarem, chama a AWS. O Deploy so prossegue se a Tag pertencer a branch `main`.
2. **Seguranca Zero-Knowledge:** Nenhuma variavel de ambiente ou segredo e exposta no script de inicializacao da AWS (`user-data`). O GitHub Actions cria uma chave SSH temporaria, abre uma conexao criptografada com a maquina, envia os arquivos via `rsync/scp` junto com o `.env` gerado dinamicamente e destroi a chave em seguida. Nada fica gravado em logs!
3. **Criacao:** A pipeline pede para a AWS criar uma maquina virtual (`t3a.large` com Ubuntu 24.04), instala o Docker e sobe os containers do zero.
4. **Kill Switch:** No instante do boot, um cronometro regressivo de 12 horas e acionado (`shutdown -h +720`).
5. **Custo Zero:** A maquina e configurada na AWS com `--instance-initiated-shutdown-behavior terminate`. A AWS **destroi fisicamente a maquina virtual e apaga o disco**, zerando custos.

> **Importante:** Como a maquina e destruida, voce deve usar o painel Admin para enviar o seu `.zip` com o backup da planilha sempre que for apresentar o TCC.

## O que voce precisa configurar no GitHub (Secrets)

Va no seu repositorio no GitHub: **Settings > Secrets and variables > Actions** e cadastre TODAS as variaveis abaixo. Elas serao automaticamente mapeadas para o seu `.env`.

### 1. Credenciais da AWS (Para criar a maquina)
- `AWS_ACCESS_KEY_ID`: Sua chave de acesso da AWS (IAM User com permissao EC2 completa).
- `AWS_SECRET_ACCESS_KEY`: O segredo da sua chave AWS.
- `AWS_REGION`: A regiao onde a maquina vai nascer (ex: `us-east-1`).

### 2. Segredos da Aplicacao (Cruciais no .env)
- `APP_SECRET_KEY`: String longa para assinar tokens JWT (Minimo 32 caracteres).
- `APP_SYSTEM_EMAIL`: O e-mail que voce usara para logar no sistema como Admin.
- `APP_SYSTEM_PASSWORD`: A senha que voce usara para logar no sistema como Admin.
- `APP_ADMIN_SLUG`: O caminho secreto do seu painel admin (ex: `meu-admin-secreto`).
- `APP_BACKUP_PASSPHRASE`: A senha usada para criptografar/descriptografar os zips de backup do sistema.

### 3. Configuracoes de Inteligencia Artificial (LLM & Embeddings)
- `APP_LLM_PROVIDER`: O provedor que voce usara na apresentacao para o chat (ex: `openai`, `gemini`).
- `APP_LLM_MODEL`: O modelo do chat (ex: `gpt-4o-mini`, `gemini-1.5-flash`).
- `APP_EMBEDDING_PROVIDER`: O provedor dos embeddings. O padrao e `remote` (para usar chaves da OpenAI/Gemini).
- `APP_EMBEDDING_REMOTE_MODEL`: O modelo de embeddings. O padrao e `text-embedding-3-small`.
- `APP_EMBEDDING_DIMENSION`: A dimensao vetorial. O padrao e `1536` para OpenAI.
- `APP_OPENAI_API_KEY`: Sua chave da OpenAI (se usar `openai`).
- `APP_GEMINI_API_KEY`: Sua chave do Google (se usar `gemini`).

### 4. Configuracoes de Email (SMTP)
Se quiser testar a recuperacao de senha e exclusao de conta na apresentacao, adicione:
- `APP_SMTP_SERVER`: Servidor SMTP (ex: `smtp.gmail.com`).
- `APP_SMTP_PORT`: Porta (ex: `587`).
- `APP_SMTP_USERNAME`: Email de disparo.
- `APP_SMTP_PASSWORD`: Senha do email (ou App Password).
- `APP_FROM_EMAIL`: Remetente visivel.

*Nota: Senhas de banco de dados (Postgres, Qdrant) e tokens internos sao gerados automaticamente e aleatoriamente pela pipeline a cada deploy para garantir seguranca maxima! Nao e preciso cadastra-las no Github.*

## Observacao sobre Pagamentos
O sistema esta configurado com `DEV_MODE=False` (Seguranca de producao) mas com `SKIP_PAYMENT=True`. Isso significa que, na apresentacao do TCC, **os usuarios podem dar upgrade de nivel livremente pela interface sem barra-los no gateway de pagamento (Pagar.me)**. A API aceitara o upgrade imediatamente.

## Como rodar

1. Garanta que voce esta na branch `main` e cometa tudo.
2. Crie uma Tag e envie para o GitHub:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. Acompanhe a aba **Actions** no seu GitHub.
4. Pegue o **IP Publico** nos logs finais do job de Deploy.
5. Acesse `http://<IP>/admin/<SEU_ADMIN_SLUG>`, faca upload do backup e apresente seu TCC!
