class LoginManager {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api/v1';
        this.initializeElements();
        this.attachEventListeners();
        this.checkRememberedUser();
        this.checkIfAlreadyLoggedIn();
    }

    async checkIfAlreadyLoggedIn() {
        const token = localStorage.getItem('authToken');
        if (token) {
            try {
                // Verify token validity
                const response = await fetch(`${this.apiBaseUrl}/auth/verify-token`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.valid) {
                        window.location.href = '/dashboard.html';
                    }
                }
            } catch (error) {
                // Token invalid or API error, stay on login page
                console.log('Session check failed, staying on login page');
                localStorage.removeItem('authToken'); // Cleanup invalid token
            }
        }
    }

    initializeElements() {
        this.form = document.getElementById('loginForm');
        this.emailInput = document.getElementById('email');
        this.passwordInput = document.getElementById('password');
        this.togglePasswordBtn = document.getElementById('togglePassword');
        this.rememberMeCheckbox = document.getElementById('rememberMe');
        this.loginBtn = document.getElementById('loginBtn');
        this.loginSpinner = document.getElementById('loginSpinner');
        this.emailError = document.getElementById('emailError');
        this.passwordError = document.getElementById('passwordError');
        this.toast = document.getElementById('toast');
        this.toastMessage = document.getElementById('toastMessage');
        this.signupLink = document.getElementById('signupLink');
        this.forgotPasswordLink = document.querySelector('.forgot-password');
        this.googleBtn = document.querySelector('.google-btn');
        this.microsoftBtn = document.querySelector('.microsoft-btn');
    }

    attachEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleLogin(e));
        
        // Toggle password visibility
        this.togglePasswordBtn.addEventListener('click', () => this.togglePasswordVisibility());
        
        // Real-time validation
        this.emailInput.addEventListener('blur', () => this.validateEmail());
        this.emailInput.addEventListener('input', () => this.clearFieldError('email'));
        
        this.passwordInput.addEventListener('blur', () => this.validatePassword());
        this.passwordInput.addEventListener('input', () => this.clearFieldError('password'));
        
        // Social login buttons
        this.googleBtn.addEventListener('click', () => this.handleSocialLogin('google'));
        this.microsoftBtn.addEventListener('click', () => this.handleSocialLogin('microsoft'));
        
        // Other links
        this.forgotPasswordLink.addEventListener('click', (e) => this.handleForgotPassword(e));
        
        // Remember me functionality
        this.rememberMeCheckbox.addEventListener('change', () => this.handleRememberMe());
    }

    validateEmail() {
        const email = this.emailInput.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!email) {
            this.showFieldError('email', 'O e-mail é obrigatório');
            return false;
        }
        
        if (!emailRegex.test(email)) {
            this.showFieldError('email', 'Digite um e-mail válido');
            return false;
        }
        
        this.clearFieldError('email');
        return true;
    }

    validatePassword() {
        const password = this.passwordInput.value;
        
        if (!password) {
            this.showFieldError('password', 'A senha é obrigatória');
            return false;
        }
        
        if (password.length < 6) {
            this.showFieldError('password', 'A senha deve ter pelo menos 6 caracteres');
            return false;
        }
        
        this.clearFieldError('password');
        return true;
    }

    showFieldError(field, message) {
        const input = field === 'email' ? this.emailInput : this.passwordInput;
        const errorElement = field === 'email' ? this.emailError : this.passwordError;
        
        input.classList.add('error');
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }

    clearFieldError(field) {
        const input = field === 'email' ? this.emailInput : this.passwordInput;
        const errorElement = field === 'email' ? this.emailError : this.passwordError;
        
        input.classList.remove('error');
        errorElement.classList.remove('show');
    }

    async handleLogin(e) {
        e.preventDefault();
        
        // Validate all fields
        const isEmailValid = this.validateEmail();
        const isPasswordValid = this.validatePassword();
        
        if (!isEmailValid || !isPasswordValid) {
            this.showToast('Por favor, corrija os erros no formulário', 'error');
            return;
        }
        
        const formData = {
            email: this.emailInput.value.trim(),
            password: this.passwordInput.value,
            remember_me: this.rememberMeCheckbox.checked
        };
        
        await this.performLogin(formData);
    }

    async performLogin(formData) {
        try {
            this.setLoadingState(true);
            
            const response = await fetch(`${this.apiBaseUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: formData.email,
                    password: formData.password
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Fetch user details after successful login
                const userResponse = await fetch(`${this.apiBaseUrl}/auth/me`, {
                    headers: {
                        'Authorization': `Bearer ${data.access_token}`
                    }
                });
                
                if (userResponse.ok) {
                    const userData = await userResponse.json();
                    this.handleSuccessfulLogin({
                        token: data.access_token,
                        user: userData
                    });
                } else {
                    this.handleLoginError('Erro ao obter dados do usuário.');
                }
            } else {
                this.handleLoginError(data.detail || 'E-mail ou senha incorretos');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.handleLoginError('Erro de conexão. Verifique se a API está rodando.');
        } finally {
            this.setLoadingState(false);
        }
    }

    async mockApiCall(formData) {
        // Deprecated - using real API
        return { success: false, error: 'Deprecated' };
    }

    handleSuccessfulLogin(data) {
        // Store authentication data
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        if (this.rememberMeCheckbox.checked) {
            localStorage.setItem('rememberedEmail', this.emailInput.value);
        } else {
            localStorage.removeItem('rememberedEmail');
        }
        
        this.showToast('Login realizado com sucesso!', 'success');
        
        // Redirect to dashboard after delay
        setTimeout(() => {
            window.location.href = '/dashboard.html';
        }, 1500);
    }

    handleLoginError(error) {
        this.showToast(error, 'error');
        
        // Add shake animation to form
        this.form.classList.add('shake');
        setTimeout(() => {
            this.form.classList.remove('shake');
        }, 500);
    }

    setLoadingState(loading) {
        if (loading) {
            this.loginBtn.classList.add('loading');
            this.loginBtn.disabled = true;
            this.emailInput.disabled = true;
            this.passwordInput.disabled = true;
        } else {
            this.loginBtn.classList.remove('loading');
            this.loginBtn.disabled = false;
            this.emailInput.disabled = false;
            this.passwordInput.disabled = false;
        }
    }

    togglePasswordVisibility() {
        const type = this.passwordInput.type === 'password' ? 'text' : 'password';
        this.passwordInput.type = type;
        
        const icon = this.togglePasswordBtn.querySelector('i');
        icon.className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
    }

    handleRememberMe() {
        if (!this.rememberMeCheckbox.checked) {
            localStorage.removeItem('rememberedEmail');
        }
    }

    checkRememberedUser() {
        const rememberedEmail = localStorage.getItem('rememberedEmail');
        if (rememberedEmail) {
            this.emailInput.value = rememberedEmail;
            this.rememberMeCheckbox.checked = true;
        }
    }

    handleSocialLogin(provider) {
        this.showToast(`Login com ${provider} em desenvolvimento`, 'error');
        
        // Future implementation for OAuth
        // window.location.href = `${this.apiBaseUrl}/auth/${provider}`;
    }

    handleSignup(e) {
        e.preventDefault();
        this.showToast('Recuperação de senha em desenvolvimento', 'error');
        
        // Future implementation
        // window.location.href = '/forgot-password.html';
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

    // Utility methods for future API integration
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
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    logout() {
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
    }

    isAuthenticated() {
        return !!localStorage.getItem('authToken');
    }

    getCurrentUser() {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    }
}

// Add shake animation
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    
    .shake {
        animation: shake 0.5s ease-in-out;
    }
`;
document.head.appendChild(style);

// Initialize the login manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.loginManager = new LoginManager();
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LoginManager;
}
