import axios from "axios";
import { useAuth } from "../stores/auth";

const BASE_URL = `${(import.meta.env.VITE_API_URL || '/api/').replace(/\/+$/, '')}/`;

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

// Attach the access token to every request (same as Swagger's "Authorize")
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If the access token expired (401), refresh it once and retry
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const refresh = localStorage.getItem("refresh_token");

    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      refresh &&
      !original.url?.includes("token/")
    ) {
      original._retry = true;
      try {
        const { data } = await axios.post(`${BASE_URL}token/refresh/`, { refresh }, { timeout: 10000 });
        const { setAccess } = useAuth();
        setAccess(data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch {
        const { logout } = useAuth();
        logout(); // refresh token also expired -> log the user out
      }
    }
    return Promise.reject(error);
  }
);

export default api;