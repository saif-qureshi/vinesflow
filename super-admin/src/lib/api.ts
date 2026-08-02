import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";

import { useSessionStore } from "@/stores/session";
import type { AccessToken, ApiEnvelope } from "@/types";

const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8005/api/v1";

function unwrap<T>(response: AxiosResponse<T>): AxiosResponse<T> {
  const body = response.data;
  if (body && typeof body === "object" && "success" in body && "data" in body) {
    response.data = (body as unknown as ApiEnvelope<T>).data as T;
  }
  return response;
}

export const api = axios.create({ baseURL, withCredentials: true });

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useSessionStore.getState().accessToken;
  if (token) {
    const headers = AxiosHeaders.from(config.headers);
    headers.set("Authorization", `Bearer ${token}`);
    config.headers = headers;
  }
  return config;
});

const refreshClient = axios.create({ baseURL, withCredentials: true });
let refreshing: Promise<string | null> | null = null;

export async function requestAccessToken(): Promise<string | null> {
  try {
    const response = await refreshClient.post<ApiEnvelope<AccessToken>>(
      "/super-admin/auth/refresh",
    );
    const token = response.data.data?.access_token ?? null;
    useSessionStore.getState().setAccessToken(token);
    return token;
  } catch {
    useSessionStore.getState().clear();
    return null;
  }
}

api.interceptors.response.use(
  (response) => unwrap(response),
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;
    const url = original?.url ?? "";
    const isAuthCall = url.includes("/auth/login") || url.includes("/auth/refresh");
    if (error.response?.status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true;
      refreshing = refreshing ?? requestAccessToken();
      const token = await refreshing;
      refreshing = null;
      if (token) {
        const headers = AxiosHeaders.from(original.headers);
        headers.set("Authorization", `Bearer ${token}`);
        original.headers = headers;
        return api(original);
      }
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export function apiErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(error)) {
    const envelope = error.response?.data as ApiEnvelope<unknown> | undefined;
    const apiError = envelope?.error;
    if (apiError?.details?.[0]?.msg) return apiError.details[0].msg;
    if (apiError?.message) return apiError.message;
  }
  return fallback;
}
