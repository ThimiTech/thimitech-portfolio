import axios from "axios";
import { useAuth } from "../stores/auth";

const BASE_URL = "/api/";

const api = axios.create({
  baseURL: BASE_URL,
});

// Attach the access token to every request (same as Swagger's "Authorize")
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// One refresh at a time: refresh tokens rotate (the old one is blacklisted on use), so parallel 401s
// must share a single refresh call or all but the first would fail and log the user out.
let refreshing: Promise<string> | null = null;

function refreshAccess(refresh: string): Promise<string> {
  refreshing ??= axios
    .post(`${BASE_URL}token/refresh/`, { refresh })
    .then(({ data }) => {
      const { setAccess } = useAuth();
      setAccess(data.access, data.refresh);
      return data.access as string;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

// If the access token expired (401), refresh it once and retry. A second 401 (e.g. the password was
// changed, which revokes every token) ends the session.
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const refresh = localStorage.getItem("refresh_token");
    const status = error.response?.status;

    if (status === 401 && original && !original.url?.includes("token/")) {
      if (original._retry || !refresh) {
        useAuth().logout();
        return Promise.reject(error);
      }
      original._retry = true;
      try {
        const access = await refreshAccess(refresh);
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch (e) {
        // Only a rejected refresh token ends the session; a network blip, 5xx or 429 keeps it.
        const s = (e as { response?: { status?: number } })?.response?.status;
        if (s === 400 || s === 401) useAuth().logout();
      }
    }
    return Promise.reject(error);
  }
);

export default api;