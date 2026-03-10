class RegisterManager {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api/v1';
        this.initializeElements();
        this.attachEventListeners();
    }

    initializeElements() {
        this.form = document.getElementById('registerForm');
        this.usernameInput = document.getElementById('username');
        this.emailInput = document.getElementById('email');
        this.passwordInput = document.getElementById('password');
        this.confirmPasswordInput = document.getElementById('confirmPassword');
        this.togglePasswordBtn = document.getElementById('togglePassword');
        this.toggleConfirmPasswordBtn = document.getElementById('toggleConfirmPassword');
        this.registerBtn = document.getElementById('registerBtn');
        this.registerSpinner = document.getElementById('registerSpinner');
        this.usernameError = document.getElementById('usernameError');
        this.emailError = document.getElementById('emailError');
        this.passwordError = document.getElementById('passwordError');
        this.confirmPasswordError = document.getElementById('confirmPasswordError');
        this.toast = document.getElementById('toast');
        this.toastMessage = document.getElementById('toastMessage');
    }

    attachEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleRegister(e));
        
        // Toggle password visibility
        this.togglePasswordBtn.addEventListener('click', () => this.toggleVisibility(this.passwordInput, this.togglePasswordBtn));
        this.toggleConfirmPasswordBtn.addEventListener('click', () => this.toggleVisibility(this.confirmPasswordInput, this.toggleConfirmPasswordBtn));
        
        // Real-time validation
        this.usernameInput.addEventListener('blur', () => this.validateUsername());
        this.usernameInput.addEventListener('input', () => this.clearFieldError('username'));

        this.emailInput.addEventListener('blur', () => this.validateEmail());
        this.emailInput.addEventListener('input', () => this.clearFieldError('email'));
        
        this.passwordInput.addEventListener('blur', () => this.validatePassword());
        this.passwordInput.addEventListener('input', () => this.clearFieldError('password'));

        this.confirmPasswordInput.addEventListener('blur', () => this.validateConfirmPassword());
        this.confirmPasswordInput.addEventListener('input', () => this.clearFieldError('confirmPassword'));
    }

    toggleVisibility(input, btn) {
        const type = input.type === 'password' ? 'text' : 'password';
        input.type = type;
        
        const icon = btn.querySelector('i');
        icon.className = type === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash';
    }

    validateUsername() {
        const username = this.usernameInput.value.trim();
        if (!username) {
            this.showFieldError('username', 'Nome de usuário é obrigatório');
            return false;
        }
        if (username.length < 3) {
            this.showFieldError('username', 'Mínimo de 3 caracteres');
            return false;
        }
        this.clearFieldError('username');
        return true;
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

    validateConfirmPassword() {
        const confirmPassword = this.confirmPasswordInput.value;
        const password = this.passwordInput.value;

        if (confirmPassword !== password) {
            this.showFieldError('confirmPassword', 'As senhas não coincidem');
            return false;
        }
        this.clearFieldError('confirmPassword');
        return true;
    }

    showFieldError(field, message) {
        let input, errorElement;
        if (field === 'username') { input = this.usernameInput; errorElement = this.usernameError; }
        else if (field === 'email') { input = this.emailInput; errorElement = this.emailError; }
        else if (field === 'password') { input = this.passwordInput; errorElement = this.passwordError; }
        else if (field === 'confirmPassword') { input = this.confirmPasswordInput; errorElement = this.confirmPasswordError; }
        
        input.classList.add('error');
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }

    clearFieldError(field) {
        let input, errorElement;
        if (field === 'username') { input = this.usernameInput; errorElement = this.usernameError; }
        else if (field === 'email') { input = this.emailInput; errorElement = this.emailError; }
        else if (field === 'password') { input = this.passwordInput; errorElement = this.passwordError; }
        else if (field === 'confirmPassword') { input = this.confirmPasswordInput; errorElement = this.confirmPasswordError; }
        
        input.classList.remove('error');
        errorElement.classList.remove('show');
    }

    async handleRegister(e) {
        e.preventDefault();
        
        const isUsernameValid = this.validateUsername();
        const isEmailValid = this.validateEmail();
        const isPasswordValid = this.validatePassword();
        const isConfirmPasswordValid = this.validateConfirmPassword();
        
        if (!isUsernameValid || !isEmailValid || !isPasswordValid || !isConfirmPasswordValid) {
            this.showToast('Por favor, corrija os erros no formulário', 'error');
            return;
        }
        
        const formData = {
            username: this.usernameInput.value.trim(),
            email: this.emailInput.value.trim(),
            password: this.passwordInput.value
        };
        
        await this.performRegister(formData);
    }

    async performRegister(formData) {
        try {
            this.setLoadingState(true);
            
            const response = await fetch(`${this.apiBaseUrl}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (response.ok) {
                this.showToast('Cadastro realizado com sucesso! Redirecionando...', 'success');
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 2000);
            } else {
                this.showToast(data.detail || 'Erro ao realizar cadastro', 'error');
            }
        } catch (error) {
            console.error('Register error:', error);
            this.showToast('Erro de conexão. Tente novamente.', 'error');
        } finally {
            this.setLoadingState(false);
        }
    }

    setLoadingState(loading) {
        if (loading) {
            this.registerBtn.classList.add('loading');
            this.registerBtn.disabled = true;
            this.usernameInput.disabled = true;
            this.emailInput.disabled = true;
            this.passwordInput.disabled = true;
            this.confirmPasswordInput.disabled = true;
        } else {
            this.registerBtn.classList.remove('loading');
            this.registerBtn.disabled = false;
            this.usernameInput.disabled = false;
            this.emailInput.disabled = false;
            this.passwordInput.disabled = false;
            this.confirmPasswordInput.disabled = false;
        }
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
}

// Add shake animation if not exists (reused from styles.css usually, but ensuring inline style for JS logic if needed)
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    .shake { animation: shake 0.5s ease-in-out; }
`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', () => {
    new RegisterManager();
});
