import Cookies from 'js-cookie';
import api from './api';

export interface User {
  id?: string;
  username?: string;
  email: string;
  name?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterResponse {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export const authService = {
  async login(email: string, password: string, rememberMe: boolean = false): Promise<LoginResponse> {
    try {
      const response = await api.post<LoginResponse>('/auth/login', {
        email,
        password,
      });

      const token = response.data.access_token;
      const refreshToken = response.data.refresh_token;
      
      if (rememberMe) {
        Cookies.set('authToken', token, { expires: 30 });
        Cookies.set('refreshToken', refreshToken, { expires: 30 });
        localStorage.setItem('authToken', token);
        localStorage.setItem('refreshToken', refreshToken);
      } else {
        // Session cookie only — no localStorage so token is gone after browser close
        Cookies.set('authToken', token);
        Cookies.set('refreshToken', refreshToken);
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
      }

      // Buscar dados do usuário após login
      try {
        const userResponse = await api.get('/auth/me');
        localStorage.setItem('user', JSON.stringify(userResponse.data));
      } catch (e) {
        console.error('Error fetching user data:', e);
      }

      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  },

  async register(email: string, password: string, username?: string): Promise<RegisterResponse> {
    try {
      const normalizedUsername = username?.trim();
      const emailPrefix = email.split('@')[0].trim();

      const buildFallbackUsername = (): string => {
        const sanitized = emailPrefix.replace(/[^a-zA-Z0-9_]/g, '');
        let candidate = sanitized.length >= 3 ? sanitized : `${sanitized}user`;

        if (candidate.length < 3) {
          candidate = `user${Date.now().toString().slice(-4)}`;
        }

        if (candidate.toLowerCase() === 'mentoria') {
          candidate = `${candidate}_user`;
        }

        return candidate.slice(0, 50);
      };

      const finalUsername =
        normalizedUsername && normalizedUsername.length > 0
          ? normalizedUsername
          : buildFallbackUsername();

      // 1. Registrar usuário
      const response = await api.post<RegisterResponse>('/auth/register', {
        email,
        password,
        username: finalUsername,
      });

      // 2. Fazer login automaticamente após registro
      const loginResponse = await api.post<LoginResponse>('/auth/login', {
        email,
        password,
      });

      const token = loginResponse.data.access_token;
      Cookies.set('authToken', token);
      localStorage.setItem('authToken', token);
      localStorage.setItem('user', JSON.stringify(response.data));

      return response.data;
    } catch (error) {
      console.error('Register error:', error);
      throw error;
    }
  },

  async verifyToken(): Promise<boolean> {
    try {
      const token = Cookies.get('authToken') || localStorage.getItem('authToken');
      if (!token) return false;

      const response = await api.post('/auth/verify-token', {});
      return response.data.valid;
    } catch (error) {
      console.error('Token verification error:', error);
      return false;
    }
  },

  async logout(): Promise<void> {
    try {
      // Chamar endpoint de logout no backend para invalidar token no banco de dados
      await api.post('/auth/logout', {});
    } catch (error) {
      // Continuar com logout mesmo se a chamada falhar
      console.error('Logout API error:', error);
    } finally {
      // Remover tokens do frontend
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      Cookies.remove('authToken');
      Cookies.remove('refreshToken');
    }
  },

  getToken(): string | null {
    return Cookies.get('authToken') || localStorage.getItem('authToken');
  },

  getUser(): User | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  setUser(user: User): void {
    localStorage.setItem('user', JSON.stringify(user));
  },
};
