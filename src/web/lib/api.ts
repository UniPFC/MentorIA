import axios, { AxiosInstance } from 'axios';
import Cookies from 'js-cookie';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = Cookies.get('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle errors with automatic token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = Cookies.get('refreshToken');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const newAccessToken = response.data.access_token;
        const newRefreshToken = response.data.refresh_token;

        Cookies.set('authToken', newAccessToken, { sameSite: 'lax' });
        if (newRefreshToken) {
          Cookies.set('refreshToken', newRefreshToken, { sameSite: 'lax' });
        }

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem('user');
        Cookies.remove('authToken');
        Cookies.remove('refreshToken');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Check if STT is enabled
export const checkSTTEnabled = async (): Promise<boolean> => {
  try {
    // Use base URL without /api/v1 prefix for health endpoint
    const baseURL = API_BASE_URL.replace('/api/v1', '');
    const response = await axios.get(`${baseURL}/health`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return response.headers['x-stt-enabled'] === 'true';
  } catch (error) {
    return false;
  }
};

// Transcribe audio
export const transcribeAudio = async (audioFile: File, language?: string): Promise<{ text: string; language: string; detected_language?: string; language_probability?: number }> => {
  const formData = new FormData();
  formData.append('audio', audioFile);
  if (language) {
    formData.append('language', language);
  }

  const response = await api.post('/audio/transcribe', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export default api;
