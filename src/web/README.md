# Frontend RAG - Next.js & React

## 🚀 Visão Geral

Frontend moderno em **Next.js 14** com **React 18** para o sistema RAG Chat. Interface responsiva com suporte a dark mode, autenticação JWT e gerenciamento de estado.

## ✨ Funcionalidades

### Autenticação
- ✅ Login com e-mail e senha
- ✅ Cadastro de novos usuários
- ✅ Verificação de token JWT
- ✅ Lembrar usuário (30 dias)
- ✅ Logout
- ✅ Proteção de rotas autenticadas

### Dashboard
- ✅ Visualização de estatísticas
- ✅ Lista de chats recentes
- ✅ Menu sidebar responsivo
- ✅ Informações do usuário
- ✅ Navegação intuitiva

### Design
- ✅ UI moderna com Tailwind CSS
- ✅ Responsivo (mobile, tablet, desktop)
- ✅ Animações suaves
- ✅ Toast notifications
- ✅ Loading states

## 🛠️ Tecnologias

- **Framework**: Next.js 14
- **UI Library**: React 18
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Autenticação**: JWT + Cookies
- **Tipagem**: TypeScript
- **Icons**: FontAwesome 6

## 📁 Estrutura de Pastas

```
src/web/
├── app/                    # App Router (Next.js 13+)
│   ├── layout.tsx         # RootLayout com imports globais
│   ├── page.tsx           # Página raiz (redireciona para login/dashboard)
│   ├── login/
│   │   └── page.tsx       # Página de login
│   ├── register/
│   │   └── page.tsx       # Página de registro
│   └── dashboard/
│       └── page.tsx       # Dashboard protegido
├── components/            # Componentes React
│   ├── LoginForm.tsx      # Formulário de login
│   ├── Toast.tsx          # Notificações
│   ├── Sidebar.tsx        # Barra lateral
│   ├── DashboardContent.tsx # Conteúdo do dashboard
│   └── ProtectedRoute.tsx # HOC para rotas protegidas
├── lib/                   # Funções utilitárias
│   ├── api.ts            # Cliente Axios com interceptadores
│   └── auth.ts           # Serviços de autenticação
├── styles/               # Estilos globais
│   └── globals.css       # CSS global + Tailwind
├── public/               # Assets estáticos
├── package.json          # Dependências
├── tsconfig.json         # Configuração TypeScript
├── tailwind.config.js    # Configuração Tailwind
├── next.config.js        # Configuração Next.js
└── Dockerfile            # Build em multi-stage

```

## 🚀 Primeiros Passos

### Desenvolvimento Local

```bash
# Instalar dependências
npm install

# Rodar servidor de desenvolvimento
npm run dev

# Build para produção
npm run build

# Rodar na produção
npm start
```

O servidor estará disponível em `http://localhost:3000`

### Com Docker

```bash
# Iniciar todos os containers
docker-compose up -d --build

# Parar containers
docker-compose down

# Ver logs
docker-compose logs -f web
```

## 🔐 Autenticação

### Fluxo de Login
1. Usuário insere e-mail e senha
2. Requisição POST para `/auth/login`
3. Token JWT retornado
4. Token armazenado em Cookie
5. User info armazenado em localStorage
6. Redirecionamento para dashboard

### Token Management
- Token armazenado em: Cookie `authToken`
- Verificação automática ao carregar páginas protegidas
- Interceptadores Axios adicionam token em todas as requisições
- Logout automático se token expirar (401)

## 📱 Responsive Design

- **Mobile**: < 768px (Menu hambúrguer, layout empilhado)
- **Tablet**: 768px - 1024px (Menu retraído, grid 2 colunas)
- **Desktop**: > 1024px (Menu fixo, layout completo)

## 🎨 Cores

As cores seguem o design system Google:

```css
--primary-color: #1a73e8
--primary-hover: #1557b0
--secondary-color: #34a853
--error-color: #ea4335
--warning-color: #fbbc04
--text-primary: #202124
--text-secondary: #5f6368
```

## 🔄 Integração com API

O cliente está configurado para conectar na API em:
`http://localhost:8000/api/v1` (em desenvolvimento)
`http://api:8000/api/v1` (em Docker)

### Endpoints Esperados

```
POST   /auth/login           - Login
POST   /auth/register        - Registro
POST   /auth/verify-token    - Verificação de token
GET    /chats               - Listar chats
GET    /chat-types          - Listar tipos de chat
POST   /chats               - Criar novo chat
```

## 📦 Dependências Principais

```json
{
  "react": "^18.2.0",
  "next": "^14.0.0",
  "axios": "^1.6.0",
  "js-cookie": "^3.0.5",
  "tailwindcss": "^3.3.0"
}
```

## 🔍 Performance

- ✅ Code splitting automático
- ✅ Image optimization
- ✅ Lazy loading de componentes
- ✅ Static generation onde possível
- ✅ Bundle size otimizado (~120KB First Load JS)

## 🚢 Deploy

O projeto está configurado para deploy em:
- Vercel (recomendado)
- Docker/Kubernetes
- Qualquer servidor Node.js

### Variáveis de Ambiente

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NODE_ENV=production
```

## 📝 Notas de Desenvolvimento

- Todos os componentes são "use client" (client-side rendering)
- Usar `next/link` para navegação entre páginas
- Usar `next/image` para otimização de imagens
- Manter componentes pequenos e reutilizáveis
- Usar TypeScript para type safety

## 🐛 Troubleshooting

### Erro de CORS
Certifique-se que a API tem CORS habilitado:
```python
# FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

### Token expirado
O usuário será automaticamente redirecionado para login se o token expirar.

### Build lento em produção
Execute `npm run build` em sua máquina antes de fazer push para verificar problemas.

## 📞 Suporte

Para erros ou dúvidas, verifique:
1. Logs do Next.js: `docker-compose logs -f web`
2. Logs da API: `docker-compose logs -f api`
3. Console do navegador (F12)

---

**Desenvolvido com ❤️ usando Next.js & React**
