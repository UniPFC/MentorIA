# Guia de Deploy e Apresentação do MentorIA

Este documento orienta a equipe e os avaliadores sobre como disponibilizar o **MentorIA** para testes e para a banca avaliadora do TCC. O projeto oferece duas estratégias de execução:

1. **Método 1: Cloudflare Tunnel (Recomendado para a Apresentação do TCC)** — Rápido, custo zero absoluto, sem necessidade de nuvem paga e com segurança reforçada.
2. **Método 2: Deploy Efêmero Automatizado (CI/CD via GitHub Actions)** — Provisionamento sob demanda em nuvem com autodestruição.

---

## 🚀 Método 1: Apresentação com Cloudflare Tunnel (Recomendado)

O **Cloudflare Tunnel** permite expor a aplicação rodando localmente no seu computador para a internet através de um link público criptografado com **HTTPS** (ex: `https://palavras-aleatorias.trycloudflare.com`), permitindo que professores e membros da banca acessem o MentorIA em seus próprios celulares, tablets ou notebooks.

### 🛡️ Por que o Cloudflare Tunnel é 100% Seguro?

Uma dúvida comum ao rodar um servidor na máquina pessoal é o risco de invasão. O Cloudflare Tunnel foi projetado especificamente para eliminar todos os riscos dos métodos antigos:

1. **Zero Port Forwarding (Sem abrir portas no modem):**
   - Nos métodos tradicionais e perigosos, era necessário abrir portas no roteador de casa, expondo o IP residencial para a internet.
   - O Cloudflare Tunnel **NÃO abre nenhuma porta no seu roteador**. O executável cria uma conexão segura de **dentro para fora** (*outbound*) diretamente para os servidores da Cloudflare, da mesma forma que seu navegador faz quando acessa um site seguro.
   - O endereço IP da sua casa **nunca é divulgado**. Quem acessa o link só enxerga a infraestrutura da Cloudflare.

2. **Isolamento Total em Contêiner Docker:**
   - O túnel encaminha requisições exclusivamente para a porta `3000` (`http://localhost:3000`).
   - Nessa porta está rodando apenas o contêiner do Next.js do MentorIA, que é um ambiente totalmente isolado (*sandbox*) do sistema operacional.
   - Visitantes **não têm acesso** aos seus arquivos pessoais, pastas do Windows, prompt de comando ou outros dispositivos da sua rede local.

3. **Escudo de Proteção da Cloudflare (WAF & Anti-DDoS):**
   - Todo o tráfego passa primeiro pela rede mundial da Cloudflare, que filtra varreduras maliciosas, ataques de negação de serviço (DDoS) e bots antes que qualquer requisição chegue ao seu computador.

4. **Controle Total e Desligamento Instantâneo:**
   - O túnel só funciona **enquanto a janela do terminal estiver aberta**.
   - No momento em que você apertar `Ctrl + C` no terminal, o túnel é destruído no mesmo segundo e o link deixa de existir imediatamente.

---

### 📋 Passo a Passo para Apresentar via Cloudflare Tunnel

#### Passo 1: Subir os Contêineres do MentorIA
Na raiz do projeto, abra o terminal e inicialize os serviços:
```bash
docker compose up -d
```
*(Aguarde alguns segundos e confirme se a aplicação está acessível em `http://localhost:3000` no seu navegador)*.

#### Passo 2: Baixar o executável do Cloudflare Tunnel (se necessário)
O executável oficial portátil `cloudflared.exe` já pode ser baixado diretamente pelo terminal na raiz do projeto (e já está protegido no `.gitignore`). Caso você ou outro integrante do grupo esteja em uma máquina nova, basta executar o comando abaixo:

**No Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe"
```

*(Ou via Prompt de Comando / cmd com curl):*
```cmd
curl.exe -L -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
```

**No Linux (Ubuntu/Debian):**
```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb
```

**No macOS:**
```bash
brew install cloudflared
```

---

#### Passo 3: Executar o Cloudflare Tunnel
Em uma janela do PowerShell ou terminal na pasta do projeto, execute:

```powershell
.\cloudflared.exe tunnel --url http://localhost:3000
```
*(No Linux ou macOS: `cloudflared tunnel --url http://localhost:3000`)*

---

#### Passo 4: Obter o Link Público
Após alguns segundos, o Cloudflare exibirá no terminal um quadro com a URL pública segura:

```text
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://seunome-aleatorio.trycloudflare.com                                               |
+--------------------------------------------------------------------------------------------+
```

* Copie a URL `https://...trycloudflare.com`.
* Envie para os membros da banca ou abra no seu próprio celular. O MentorIA estará completamente funcional (chat em tempo real, login, cadastro e validação de slug administrativo).

---

#### Passo 5: Encerrar após a Apresentação
Ao finalizar a demonstração do TCC:
1. Vá até a janela do terminal onde o `cloudflared` está rodando.
2. Pressione `Ctrl + C`.
3. O link é desativado imediatamente na Cloudflare.
4. *(Opcional)* Para pausar os contêineres locais: `docker compose down`.

---

## ☁️ Método 2: Deploy Efêmero Automatizado em Nuvem (CI/CD)

Caso a equipe prefira provisionar uma máquina virtual dedicada na nuvem via GitHub Actions:

### Como funciona o Ciclo Efêmero:
1. **Gatilho:** O deploy é acionado automaticamente ao criar e enviar uma **Tag** no Git começando com `v` (ex: `v1.0.4`) pertencente à branch `main`.
2. **Pipeline de Testes:** O GitHub Actions executa toda a suíte de testes unitários e de integração antes de qualquer ação em nuvem.
3. **Provisionamento e Autodestruição:** A pipeline provisiona uma máquina virtual com Docker, copia os arquivos via SSH seguro e agenda a autodestruição da máquina (12 horas limite) para **garantir custo zero quando inativa**.
4. **Destruição Manual sob Demanda:** É possível acionar o workflow manual na aba **Actions** do GitHub a qualquer momento para destruir as instâncias imediatamente após os testes.

---

### 🔐 Variáveis de Ambiente e Segredos (GitHub Secrets)

Para o deploy automatizado via CI/CD, os seguintes segredos devem ser configurados em **Settings > Secrets and variables > Actions**:

#### 1. Segredos da Aplicação (Mapeados para o `.env`)
* `APP_SECRET_KEY`: String aleatória para assinatura de tokens JWT (mínimo de 32 caracteres).
* `APP_SYSTEM_EMAIL`: E-mail de login do Administrador do sistema.
* `APP_SYSTEM_PASSWORD`: Senha de login do Administrador.
* `APP_ADMIN_SLUG`: Slug secreto para o painel administrativo (ex: `meu-admin-secreto`).
* `APP_BACKUP_PASSPHRASE`: Frase secreta para encriptar e desencriptar os backups do sistema.
* `APP_PASSWORD_PEPPER`: String secreta utilizada como pepper adicional para hash de senhas.
* `APP_ENCRYPTION_SALT`: String utilizada como salt de criptografia interna.

#### 2. Provedores de Inteligência Artificial
* `APP_LLM_PROVIDER`: Provedor do modelo de linguagem (`gemini` ou `openai`).
* `APP_LLM_MODEL`: Modelo a ser utilizado (ex: `gemini-1.5-flash`, `gemini-1.5-pro` ou `gpt-4o-mini`).
* `APP_GEMINI_API_KEY`: Chave de API do Google AI Studio (se utilizar `gemini`).
* `APP_OPENAI_API_KEY`: Chave de API da OpenAI (se utilizar `openai`).
* `APP_EMBEDDING_PROVIDER`: Provedor de embeddings (`remote`).
* `APP_EMBEDDING_REMOTE_MODEL`: Modelo de embedding (padrão: `text-embedding-3-small`).
* `APP_EMBEDDING_DIMENSION`: Dimensão vetorial (padrão: `1536`).

#### 3. Notificações e E-mail (SMTP)
* `APP_SMTP_SERVER`: Servidor SMTP (ex: `smtp.gmail.com`).
* `APP_SMTP_PORT`: Porta (ex: `587`).
* `APP_SMTP_USERNAME`: E-mail de envio.
* `APP_SMTP_PASSWORD`: Senha de aplicativo da conta de e-mail.
* `APP_FROM_EMAIL`: Nome e e-mail exibidos ao destinatário.

> **Nota:** As senhas dos bancos de dados (PostgreSQL e Qdrant) e chaves internas são geradas aleatoriamente pela pipeline a cada novo deploy para assegurar isolamento e segurança máxima.
