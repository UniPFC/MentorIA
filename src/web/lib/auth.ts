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
      
      if (rememberMe) {
        Cookies.set('authToken', token, { expires: 30 });
        localStorage.setItem('authToken', token);
      } else {
        Cookies.set('authToken', token);
        localStorage.setItem('authToken', token);
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
      // 1. Registrar usuário
      const response = await api.post<RegisterResponse>('/auth/register', {
        email,
        password,
        username: username || email.split('@')[0],
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

  logout(): void {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    Cookies.remove('authToken');
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
