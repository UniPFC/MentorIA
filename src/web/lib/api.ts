import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token is sent automatically via HttpOnly cookie (withCredentials: true)

// Handle errors with automatic token refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      // Ignore 401s for auth routes to prevent infinite reloads on wrong passwords
      if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error);
      }
      
      if (isRefreshing) {
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject });
        })
          .then(() => {
            return api(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // O navegador enviará o cookie 'refreshToken' automaticamente
        await axios.post(`${API_BASE_URL}/auth/refresh`, {}, {
          withCredentials: true
        });

        isRefreshing = false;
        processQueue(null);

        // Retry original request with credentials
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        isRefreshing = false;
        // Refresh failed, logout user
        localStorage.removeItem('user');
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
