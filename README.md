# MentorIA- Projeto Final de Curso I

## Visão Geral

Este projeto consiste no desenvolvimento de uma aplicação de **RAG (Retrieval-Augmented Generation)** robusta e escalável, integrada a um sistema de chat inteligente. O sistema permite a ingestão de documentos, processamento vetorial e interação via chat contextualizado, utilizando modelos de Inteligência Artificial para gerar respostas precisas baseadas no conhecimento fornecido.

O projeto faz parte do **Projeto Final de Curso (PFC)** e encontra-se na **Fase 01 (7º Período)**, focada na consolidação e integração entre Frontend, Backend e Camada de Dados.

## Funcionalidades Principais

- **Autenticação e Segurança:** Sistema de login seguro com JWT (JSON Web Tokens).
- **Chat Inteligente (RAG):** Interface de chat que permite perguntas em linguagem natural, com respostas fundamentadas em documentos carregados.
- **Gestão de Documentos:** Upload e processamento de arquivos para base de conhecimento.
- **Histórico de Conversas:** Persistência de chats e mensagens.
- **Interface Responsiva:** Frontend moderno e responsivo (SPA).

## Arquitetura do Sistema

O sistema utiliza uma arquitetura de **Microsserviços Containerizados**, orquestrados via Docker Compose:

1. **Frontend (Web):** SPA desenvolvida em HTML5, CSS3 e JavaScript (Vanilla), servida via Nginx.
2. **Backend (API):** API RESTful desenvolvida com **FastAPI (Python)**.
3. **Banco de Dados Relacional:** **PostgreSQL** para dados estruturados (usuários, chats, histórico).
4. **Banco de Dados Vetorial:** **Qdrant** para armazenamento de embeddings e busca semântica.

```mermaid
graph TD
    User["Usuário"] --> Web["Frontend (Nginx)"]
    Web --> API["Backend (FastAPI)"]
    API --> DB["PostgreSQL"]
    API --> VectorDB["Qdrant"]
```

## Tecnologias Utilizadas

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, LangChain/LlamaIndex (integração RAG).
- **Frontend:** HTML5, CSS3, JavaScript, Nginx.
- **Infraestrutura:** Docker, Docker Compose.
- **IA/ML:** PyTorch, Transformers, Qdrant Client.
- **Banco de Dados:** PostgreSQL 15, Qdrant.

## Pré-requisitos

- [Docker](https://www.docker.com/get-started) e Docker Compose instalados.
- Git instalado.

## Como Executar o Projeto

1. **Clone o repositório:**

   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd MentorIA
   ```
2. **Configure as variáveis de ambiente:**
   Crie um arquivo `.env` na raiz do projeto (baseado no `.env.example`, se disponível) e configure as credenciais necessárias (chaves de API de LLMs, senhas de banco, etc.).
3. **Inicie os contêineres:**

   ```bash
   docker-compose up --build -d
   ```
4. **Acesse a aplicação:**

   - Frontend: `http://localhost:3000` (ou porta configurada).
   - API Docs (Swagger): `http://localhost:8000/docs`.

## Configurações de Ambiente (.env)

O arquivo `.env` contém configurações vitais para rodar o sistema localmente ou em produção. Algumas das variáveis de destaque para controle de segurança e testes incluem:

- **DEV_MODE (`True`/`False`):** Controla o modo de desenvolvimento global. Ativar isso não mexe na segurança diretamente, mas serve como indicativo geral.
- **SECURE_COOKIES (`True`/`False`):** Se `True`, todos os cookies de autenticação ganharão a flag `Secure` e exigirão conexão HTTPS para funcionarem. Em ambiente local com HTTP padrão, deixe como `False` para os cookies funcionarem.
- **AUTO_RUN_SEEDER (`True`/`False`):** Se `True`, popula automaticamente o banco de dados e vetores de embeddings (Qdrant) ao iniciar o backend. Deixe `False` para um startup mais veloz se o banco já estiver populado.
- **ENABLE_API_DOCS (`True`/`False`):** Ativa ou desativa a documentação do FastAPI (Swagger/ReDoc) na rota `/docs`.
- **FORCE_HTTPS (`True`/`False`):** Se `True`, o middleware forçará um redirecionamento 301 de HTTP para HTTPS em todas as requisições e adicionará o cabeçalho HSTS.
- **SKIP_PAYMENT (`True`/`False`):** Permite simular a conclusão instantânea de compras de assinatura ou recarga de créditos (ideal para testes de UI) sem passar pela validação real de um gateway.

## Estrutura do Repositório

- `/src/api`: Código fonte do Backend (FastAPI).
- `/src/web`: Código fonte do Frontend (HTML/JS/CSS).
- `/shared`: Códigos compartilhados (Modelos de banco, etc.).
- `/alembic`: Migrações de banco de dados.
- `/config`: Configurações globais e logs.
- `/docs`: Documentação do projeto.

## Autores

**Equipe Techstein**
Projeto desenvolvido para a disciplina de Projeto Final de Curso.

## Badges

![Coverage](./coverage.svg)
