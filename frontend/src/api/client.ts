/**
 * Centralized API client for communicating with FastAPI backend.
 */

const BASE_URL = "";

export class APIError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.data = data;
  }
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    let responseData: any;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      responseData = await response.json();
    } else {
      responseData = await response.text();
    }

    if (!response.ok) {
      const errorMessage =
        (responseData && typeof responseData === "object" && responseData.detail) ||
        (responseData && typeof responseData === "object" && responseData.message) ||
        `HTTP ${response.status}: ${response.statusText}`;
      throw new APIError(errorMessage, response.status, responseData);
    }

    return responseData as T;
  } catch (error: any) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(
      error.message || "Failed to connect to backend service.",
      0,
      error
    );
  }
}
