import axios from "axios";

const BASE = import.meta.env.VITE_API_BASE ?? "/";

export const api = axios.create({ baseURL: BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cbm_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !location.pathname.startsWith("/login")) {
      localStorage.removeItem("cbm_token");
      location.href = "/login";
    }
    return Promise.reject(err);
  },
);

export async function login(username: string, password: string) {
  const form = new URLSearchParams({ username, password });
  const { data } = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  localStorage.setItem("cbm_token", data.access_token);
  localStorage.setItem("cbm_role", data.role);
  localStorage.setItem("cbm_name", data.full_name ?? "");
  return data;
}

export function logout() {
  localStorage.removeItem("cbm_token");
  localStorage.removeItem("cbm_role");
  location.href = "/login";
}

export const currentRole = () => localStorage.getItem("cbm_role") ?? "viewer";
export const isAuthed = () => !!localStorage.getItem("cbm_token");
