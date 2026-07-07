export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "";
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem("taskflow_access_token");
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const base = getApiBase();
  if (!base) {
    throw new ApiError("NEXT_PUBLIC_API_URL is not configured", 0);
  }

  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${base}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    throw new ApiError("Unauthorized", 401);
  }

  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = undefined;
    }
    throw new ApiError(`Request failed (${response.status})`, response.status, body);
  }

  return (await response.json()) as T;
}

export async function fetchHealth(): Promise<{ status: string; version: string }> {
  return apiFetch("/health");
}
