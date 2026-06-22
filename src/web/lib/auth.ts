import Cookies from 'js-cookie';
import api from './api';

export interface User {
  id?: string;
  username?: string;
  email: string;
  name?: string;
  level?: string;
  token_budget?: number;
  max_token_budget?: number;
  remaining_tokens?: number;
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

const persistentCookieOptions = { expires: 30, sameSite: 'lax' as const };
const sessionCookieOptions = { sameSite: 'lax' as const };

export const authService = {
  async login(email: string, password: string, rememberMe: boolean = false): Promise<LoginResponse> {
    try {
      const response = await api.post<LoginResponse>('/auth/login', {
        email,
        password,
      });

      const token = response.data.access_token;
      const refreshToken = response.data.refresh_token;
      const cookieOptions = rememberMe ? persistentCookieOptions : sessionCookieOptions;

      Cookies.set('authToken', token, cookieOptions);
      Cookies.set('refreshToken', refreshToken, cookieOptions);

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

      const response = await api.post<RegisterResponse>('/auth/register', {
        email,
        password,
        username: finalUsername,
      });

      const loginResponse = await api.post<LoginResponse>('/auth/login', {
        email,
        password,
      });

      Cookies.set('authToken', loginResponse.data.access_token, sessionCookieOptions);
      Cookies.set('refreshToken', loginResponse.data.refresh_token, sessionCookieOptions);
      localStorage.setItem('user', JSON.stringify(response.data));

      return response.data;
    } catch (error) {
      console.error('Register error:', error);
      throw error;
    }
  },

  async verifyToken(): Promise<boolean> {
    try {
      const token = Cookies.get('authToken');
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
      await api.post('/auth/logout', {});
    } catch (error) {
      console.error('Logout API error:', error);
    } finally {
      localStorage.removeItem('user');
      Cookies.remove('authToken');
      Cookies.remove('refreshToken');
    }
  },

  getToken(): string | null {
    return Cookies.get('authToken') || null;
  },

  getUser(): User | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  setUser(user: User): void {
    localStorage.setItem('user', JSON.stringify(user));
  },
};
