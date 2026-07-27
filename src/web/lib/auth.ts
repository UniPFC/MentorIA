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
  two_factor_enabled?: boolean;
  last_2fa_reminder_at?: string;
}

export interface LoginResponse {
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
  requires_2fa?: boolean;
  temp_token?: string;
}

export interface RegisterResponse {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

// Cookies are now HttpOnly and managed by the backend

export const authService = {
  async login(email: string, password: string, rememberMe: boolean = false): Promise<LoginResponse> {
    try {
      const response = await api.post<LoginResponse>('/auth/login', {
        email,
        password,
        remember_me: rememberMe,
      });

      // O backend agora injeta os cookies HttpOnly (authToken, refreshToken) na resposta automaticamente
      if (response.data.requires_2fa) {
        return response.data;
      }

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

      // O backend agora injeta os cookies HttpOnly automaticamente na resposta do login
      localStorage.setItem('user', JSON.stringify(response.data));

      return response.data;
    } catch (error) {
      console.error('Register error:', error);
      throw error;
    }
  },

  async verifyToken(): Promise<boolean> {
    try {
      // Deixa o navegador enviar o cookie automaticamente; o backend retorna se é válido

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
    }
  },

  async login2FA(tempToken: string, code: string, rememberMe: boolean = false): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/auth/login/2fa', {
      temp_token: tempToken,
      code,
      remember_me: rememberMe,
    });
    
    try {
      const userResponse = await api.get('/auth/me');
      localStorage.setItem('user', JSON.stringify(userResponse.data));
    } catch (e) {
      console.error('Error fetching user data:', e);
    }
    return response.data;
  },

  async setup2FA() {
    const response = await api.post('/auth/2fa/setup');
    return response.data;
  },

  async enable2FA(secret: string, code: string) {
    const response = await api.post('/auth/2fa/enable', { secret, code });
    return response.data;
  },

  async disable2FA(code: string) {
    const response = await api.post('/auth/2fa/disable', { code });
    return response.data;
  },

  async dismiss2FAReminder() {
    const response = await api.post('/auth/2fa/dismiss-reminder');
    return response.data;
  },

  getToken(): string | null {
    // Tokens não são mais acessíveis pelo Javascript (HttpOnly)
    return null;
  },

  getUser(): User | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  setUser(user: User): void {
    localStorage.setItem('user', JSON.stringify(user));
  },
};
