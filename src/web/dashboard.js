class DashboardManager {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api/v1';
        this.initializeElements();
        this.attachEventListeners();
        this.checkAuthentication();
        this.loadUserData();
        this.loadDashboardData();
    }

    initializeElements() {
        // Mobile menu
        this.mobileMenuToggle = document.getElementById('mobileMenuToggle');
        this.sidebar = document.getElementById('sidebar');
        
        // User info
        this.userAvatar = document.getElementById('userAvatar');
        this.userName = document.getElementById('userName');
        this.userEmail = document.getElementById('userEmail');
        
        // Stats
        this.totalChats = document.getElementById('totalChats');
        this.totalMessages = document.getElementById('totalMessages');
        this.totalChatTypes = document.getElementById('totalChatTypes');
        this.totalChunks = document.getElementById('totalChunks');
        
        // Recent chats
        this.recentChats = document.getElementById('recentChats');
        
        // Buttons
        this.refreshBtn = document.getElementById('refreshBtn');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.logoutBtn = document.getElementById('logoutBtn');
        
        // Toast
        this.toast = document.getElementById('toast');
        this.toastMessage = document.getElementById('toastMessage');
        
        // Navigation items
        this.navItems = document.querySelectorAll('.nav-item');
    }

    attachEventListeners() {
        // Mobile menu toggle
        this.mobileMenuToggle.addEventListener('click', () => this.toggleMobileMenu());
        
        // Navigation
        this.navItems.forEach(item => {
            item.addEventListener('click', (e) => this.handleNavigation(e));
        });
        
        // Buttons
        this.refreshBtn.addEventListener('click', () => this.refreshDashboard());
        this.newChatBtn.addEventListener('click', () => this.createNewChat());
        this.logoutBtn.addEventListener('click', () => this.logout());
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.sidebar.contains(e.target) && !this.mobileMenuToggle.contains(e.target)) {
                this.sidebar.classList.remove('open');
            }
        });
    }

    checkAuthentication() {
        const token = localStorage.getItem('authToken');
        if (!token) {
            this.showToast('Sessão expirada. Faça login novamente.', 'error');
            setTimeout(() => {
                window.location.href = '/index.html';
            }, 1500);
            return false;
        }
        return true;
    }

    loadUserData() {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            const user = JSON.parse(userStr);
            this.updateUserInfo(user);
        }
    }

    updateUserInfo(user) {
        this.userName.textContent = user.name || 'Usuário';
        this.userEmail.textContent = user.email || 'email@exemplo.com';
        
        // Create avatar initials
        const initials = user.name ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : 'U';
        this.userAvatar.textContent = initials;
    }

    async loadDashboardData() {
        try {
            this.setLoadingState(true);
            
            // Load all dashboard data in parallel
            const [chatsData, chatTypesData] = await Promise.all([
                this.loadChats(),
                this.loadChatTypes()
            ]);
            
            this.updateStats(chatsData, chatTypesData);
            this.renderRecentChats(chatsData.chats || []);
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showToast('Erro ao carregar dados do dashboard', 'error');
            this.loadMockData(); // Load mock data for demo
        } finally {
            this.setLoadingState(false);
        }
    }

    async loadChats() {
        // Mock data for demo - replace with actual API call
        await new Promise(resolve => setTimeout(resolve, 500));
        
        return {
            chats: [
                {
                    id: 1,
                    title: 'Estudo ENEM 2024',
                    chat_type_id: 1,
                    created_at: '2024-03-15T10:30:00Z',
                    updated_at: '2024-03-15T14:20:00Z',
                    message_count: 15
                },
                {
                    id: 2,
                    title: 'Matemática Básica',
                    chat_type_id: 2,
                    created_at: '2024-03-14T09:15:00Z',
                    updated_at: '2024-03-14T16:45:00Z',
                    message_count: 8
                },
                {
                    id: 3,
                    title: 'História do Brasil',
                    chat_type_id: 3,
                    created_at: '2024-03-13T13:00:00Z',
                    updated_at: '2024-03-13T15:30:00Z',
                    message_count: 12
                }
            ],
            total: 3,
            total_messages: 35
        };
        
        // Actual API call would be:
        // return await this.makeApiRequest('/chats');
    }

    async loadChatTypes() {
        // Mock data for demo
        await new Promise(resolve => setTimeout(resolve, 300));
        
        return {
            chat_types: [
                { id: 1, name: 'ENEM 2024', chunk_count: 150 },
                { id: 2, name: 'Matemática', chunk_count: 80 },
                { id: 3, name: 'História', chunk_count: 120 }
            ],
            total: 3,
            total_chunks: 350
        };
        
        // Actual API call would be:
        // return await this.makeApiRequest('/chat-types');
    }

    loadMockData() {
        const mockChatsData = {
            chats: [
                {
                    id: 1,
                    title: 'Estudo ENEM 2024',
                    chat_type_id: 1,
                    created_at: '2024-03-15T10:30:00Z',
                    updated_at: '2024-03-15T14:20:00Z',
                    message_count: 15
                },
                {
                    id: 2,
                    title: 'Matemática Básica',
                    chat_type_id: 2,
                    created_at: '2024-03-14T09:15:00Z',
                    updated_at: '2024-03-14T16:45:00Z',
                    message_count: 8
                }
            ],
            total: 2,
            total_messages: 23
        };

        const mockChatTypesData = {
            chat_types: [
                { id: 1, name: 'ENEM 2024', chunk_count: 150 },
                { id: 2, name: 'Matemática', chunk_count: 80 }
            ],
            total: 2,
            total_chunks: 230
        };

        this.updateStats(mockChatsData, mockChatTypesData);
        this.renderRecentChats(mockChatsData.chats);
    }

    updateStats(chatsData, chatTypesData) {
        // Animate numbers
        this.animateNumber(this.totalChats, chatsData.total || 0);
        this.animateNumber(this.totalMessages, chatsData.total_messages || 0);
        this.animateNumber(this.totalChatTypes, chatTypesData.total || 0);
        this.animateNumber(this.totalChunks, chatTypesData.total_chunks || 0);
    }

    animateNumber(element, target) {
        const duration = 1000;
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current).toLocaleString();
        }, 16);
    }

    renderRecentChats(chats) {
        if (!chats || chats.length === 0) {
            this.recentChats.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comments"></i>
                    <h3>Nenhum chat encontrado</h3>
                    <p>Crie seu primeiro chat para começar a usar o sistema</p>
                </div>
            `;
            return;
        }

        const chatsHtml = chats.slice(0, 5).map(chat => `
            <div class="chat-item">
                <div class="chat-info">
                    <h3>${chat.title}</h3>
                    <p>${chat.message_count || 0} mensagens • ${this.formatDate(chat.updated_at)}</p>
                </div>
                <div class="chat-actions">
                    <button class="btn btn-primary btn-sm" onclick="dashboardManager.openChat(${chat.id})">
                        <i class="fas fa-external-link-alt"></i>
                        Abrir
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="dashboardManager.deleteChat(${chat.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');

        this.recentChats.innerHTML = chatsHtml;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 1) return 'Hoje';
        if (diffDays === 2) return 'Ontem';
        if (diffDays <= 7) return `${diffDays - 1} dias atrás`;
        
        return date.toLocaleDateString('pt-BR');
    }

    toggleMobileMenu() {
        this.sidebar.classList.toggle('open');
    }

    handleNavigation(e) {
        e.preventDefault();
        const href = e.currentTarget.getAttribute('href');
        
        if (href === '#') return; // Skip logout and other special links
        
        // Remove active class from all items
        this.navItems.forEach(item => item.classList.remove('active'));
        
        // Add active class to clicked item
        e.currentTarget.classList.add('active');
        
        // Handle navigation based on href
        switch (href) {
            case '#dashboard':
                this.showSection('dashboard');
                break;
            case '#chats':
                this.showSection('chats');
                break;
            case '#upload':
                this.showSection('upload');
                break;
            case '#chat-types':
                this.showSection('chat-types');
                break;
            case '#settings':
                this.showSection('settings');
                break;
            default:
                this.showToast('Página em desenvolvimento', 'error');
        }
        
        // Close mobile menu after navigation
        this.sidebar.classList.remove('open');
    }

    showSection(section) {
        // This would typically load different content based on the section
        this.showToast(`Navegando para ${section}`, 'success');
        
        // For demo purposes, we'll just show a message
        if (section !== 'dashboard') {
            this.showToast(`Página ${section} em desenvolvimento`, 'error');
        }
    }

    async refreshDashboard() {
        this.refreshBtn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Atualizando...';
        this.refreshBtn.disabled = true;
        
        try {
            await this.loadDashboardData();
            this.showToast('Dashboard atualizado com sucesso!', 'success');
        } catch (error) {
            this.showToast('Erro ao atualizar dashboard', 'error');
        } finally {
            this.refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Atualizar';
            this.refreshBtn.disabled = false;
        }
    }

    createNewChat() {
        this.showToast('Redirecionando para criação de chat...', 'success');
        // Future: window.location.href = '/chat.html';
    }

    openChat(chatId) {
        this.showToast(`Abrindo chat ${chatId}...`, 'success');
        // Future: window.location.href = `/chat.html?id=${chatId}`;
    }

    async deleteChat(chatId) {
        if (!confirm('Tem certeza que deseja excluir este chat? Esta ação não pode ser desfeita.')) {
            return;
        }

        try {
            // Mock deletion
            await new Promise(resolve => setTimeout(resolve, 500));
            
            this.showToast('Chat excluído com sucesso!', 'success');
            await this.loadDashboardData(); // Refresh data
        } catch (error) {
            this.showToast('Erro ao excluir chat', 'error');
        }
    }

    logout() {
        if (confirm('Tem certeza que deseja sair?')) {
            localStorage.removeItem('authToken');
            localStorage.removeItem('user');
            localStorage.removeItem('rememberedEmail');
            
            this.showToast('Saindo...', 'success');
            
            setTimeout(() => {
                window.location.href = '/index.html';
            }, 1000);
        }
    }

    setLoadingState(loading) {
        // Add loading state to stats
        const statValues = document.querySelectorAll('.stat-value');
        statValues.forEach(stat => {
            if (loading) {
                stat.style.opacity = '0.5';
            } else {
                stat.style.opacity = '1';
            }
        });
    }

    showToast(message, type = 'success') {
        this.toastMessage.textContent = message;
        this.toast.className = `toast ${type}`;
        
        const icon = this.toast.querySelector('i');
        icon.className = type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
        
        setTimeout(() => {
            this.toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            this.toast.classList.remove('show');
        }, 3000);
    }

    async makeApiRequest(endpoint, options = {}) {
        const token = localStorage.getItem('authToken');
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { Authorization: `Bearer ${token}` })
            }
        };
        
        const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                this.logout();
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardManager;
}
