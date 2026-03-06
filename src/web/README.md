# Portal RAG - Frontend Web

## 📋 Visão Geral

Frontend completo para o sistema RAG Chat, desenvolvido com HTML5, CSS3 e JavaScript vanilla. O sistema oferece uma interface moderna e responsiva para interagir com a API de chat inteligente.

## 🚀 Funcionalidades Implementadas

### ✅ Tela de Login Completa
- **Design moderno** com gradientes e animações suaves
- **Validação em tempo real** de e-mail e senha
- **Toggle de visibilidade** da senha
- **Opção "Lembrar-me"** com persistência local
- **Login social** (Google e Microsoft - UI pronta)
- **Feedback visual** com toast notifications
- **Estados de loading** e animações
- **Totalmente responsivo** para mobile e desktop

### ✅ Dashboard Interativo
- **Estatísticas em tempo real** com animações
- **Lista de chats recentes** com ações rápidas
- **Navegação lateral** responsiva
- **Informações do usuário** personalizadas
- **Sistema de notificações** toast
- **Menu mobile** com hamburger
- **Atualização automática** de dados

### 🔧 Características Técnicas

#### **Validação de Formulários**
- Validação de e-mail com regex
- Validação de senha (mínimo 6 caracteres)
- Mensagens de erro contextuais
- Limpeza automática de erros
- Feedback visual em tempo real

#### **Gerenciamento de Estado**
- Autenticação com JWT (mock)
- Persistência de sessão
- Armazenamento local de preferências
- Gerenciamento de usuário
- Redirecionamento automático

#### **Design Responsivo**
- Mobile-first approach
- Breakpoints para tablet e mobile
- Menu hamburger para dispositivos móveis
- Layout adaptativo
- Touch-friendly interactions

#### **Acessibilidade**
- Semântica HTML5 correta
- ARIA labels onde necessário
- Navegação por teclado
- Contraste adequado
- Focus states visíveis

## 📁 Estrutura de Arquivos

```
src/web/
├── index.html          # Tela de login
├── dashboard.html      # Dashboard principal
├── styles.css          # Estilos globais
├── script.js           # Lógica do login
├── dashboard.js        # Lógica do dashboard
├── README.md           # Documentação
└── Dockerfile          # Configuração Docker
```

## 🎨 Design System

### **Cores**
- **Primary:** #4f46e5 (Indigo)
- **Secondary:** #06b6d4 (Cyan)
- **Success:** #10b981 (Green)
- **Error:** #ef4444 (Red)
- **Warning:** #f59e0b (Amber)

### **Tipografia**
- **Fonte:** Inter (Google Fonts)
- **Pesos:** 300, 400, 500, 600, 700
- **Hierarquia** bem definida

### **Componentes**
- Botões com múltiplos estados
- Cards com hover effects
- Formulários validados
- Modais e toasts
- Sidebar navigation

## 🔐 Credenciais de Teste

### **Login Demo**
- **Admin:** `admin@portal.com` / `admin123`
- **User:** `user@portal.com` / `user123`

## 🚀 Como Usar

### **Desenvolvimento Local**
1. Clone o repositório
2. Navegue até `src/web/`
3. Abra `index.html` no navegador
4. Use as credenciais de teste

### **Com Docker**
```bash
# Build e start dos containers
docker-compose up web

# Acesse em http://localhost:3000
```

### **Produção**
```bash
# Build da imagem
docker build -t rag-web ./src/web

# Run do container
docker run -p 3000:80 rag-web
```

## 🔌 Integração com API

### **Endpoints Configurados**
- **Base URL:** `http://localhost:8000/api/v1`
- **Auth:** `/auth/login` (mock implementado)
- **Chats:** `/chats`
- **Chat Types:** `/chat-types`
- **Upload:** `/upload`

### **Métodos Helper**
```javascript
// Fazer requisição autenticada
await dashboardManager.makeApiRequest('/chats');

// Verificar autenticação
dashboardManager.isAuthenticated();

// Obter usuário atual
dashboardManager.getCurrentUser();
```

## 📱 Responsividade

### **Breakpoints**
- **Mobile:** < 768px
- **Tablet:** 768px - 1024px
- **Desktop:** > 1024px

### **Adaptações**
- Menu hamburger no mobile
- Grid de stats responsivo
- Cards empilhados em mobile
- Textos ajustados para telas pequenas

## 🎯 Próximos Passos

### **Para Implementar**
- [ ] Página de chat completa
- [ ] Upload de planilhas
- [ ] Gestão de chat types
- [ ] Perfil do usuário
- [ ] Configurações
- [ ] Histórico de atividades

### **Melhorias**
- [ ] Dark mode
- [ ] Temas personalizáveis
- [ ] Animações avançadas
- [ ] Lazy loading
- [ ] Service Worker
- [ ] PWA capabilities

## 🔧 Customização

### **Cores e Temas**
Edite as variáveis CSS em `styles.css`:
```css
:root {
    --primary-color: #4f46e5;
    --secondary-color: #06b6d4;
    /* ... outras variáveis */
}
```

### **API Endpoints**
Altere a base URL nos arquivos JS:
```javascript
this.apiBaseUrl = 'https://sua-api.com/api/v1';
```

## 🐛 Troubleshooting

### **Problemas Comuns**
1. **CORS:** Configure a API para permitir origem do frontend
2. **Autenticação:** Verifique se o token JWT está válido
3. **Responsividade:** Teste em diferentes dispositivos
4. **Performance:** Otimize imagens e assets

### **Debug Mode**
```javascript
// Ativar logs detalhados
localStorage.setItem('debug', 'true');
```

## 📄 Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para detalhes.

---

**Desenvolvido com ❤️ para o Portal RAG**
