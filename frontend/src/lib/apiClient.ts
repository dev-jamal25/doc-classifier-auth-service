const TOKEN_KEY = "doc-classifier.token";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string): void => { localStorage.setItem(TOKEN_KEY, token); };
export const clearToken = (): void => { localStorage.removeItem(TOKEN_KEY); };

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string>) };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(path, { ...init, headers });
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await apiFetch(path);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export async function apiUpload(path: string, file: File): Promise<Response> {
  const token = getToken();
  const form = new FormData();
  form.append("file", file);
  // Do NOT set Content-Type manually — browser sets it with the correct multipart boundary.
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(path, { method: "POST", headers, body: form });
}
