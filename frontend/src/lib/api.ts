import { useAuthStore } from "./auth-store";
import type {
  ChatResponse,
  Conversation,
  EventItem,
  Idea,
  Message,
  Reminder,
  Task,
  User,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setTokens, logout } = useAuthStore.getState();
  if (!refreshToken) return null;

  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    logout();
    return null;
  }

  const data = await response.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token as string;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  authenticated?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, authenticated = true } = options;

  const doFetch = async (token: string | null): Promise<Response> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (authenticated && token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let token = authenticated ? useAuthStore.getState().accessToken : null;
  let response = await doFetch(token);

  if (authenticated && response.status === 401) {
    token = await refreshAccessToken();
    if (token) {
      response = await doFetch(token);
    }
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail ?? detail;
    } catch {
      // sin cuerpo JSON
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  register: (email: string, password: string, fullName: string) =>
    request<User>("/auth/register", {
      method: "POST",
      body: { email, password, full_name: fullName },
      authenticated: false,
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
      authenticated: false,
    }),

  me: () => request<User>("/auth/me"),

  logout: () => {
    const { refreshToken } = useAuthStore.getState();
    if (!refreshToken) return Promise.resolve();
    return fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => undefined);
  },

  listConversations: () => request<Conversation[]>("/conversations"),
  createConversation: (title?: string) =>
    request<Conversation>("/conversations", { method: "POST", body: { title } }),
  getConversation: (id: string) => request<Conversation>(`/conversations/${id}`),
  deleteConversation: (id: string) => request<void>(`/conversations/${id}`, { method: "DELETE" }),
  listMessages: (conversationId: string) =>
    request<Message[]>(`/conversations/${conversationId}/messages`),
  sendMessage: (conversationId: string, content: string, inputType: "texto" | "audio" = "texto") =>
    request<ChatResponse>(`/conversations/${conversationId}/messages`, {
      method: "POST",
      body: { content, input_type: inputType },
    }),

  listTasks: () => request<Task[]>("/tasks"),
  listEvents: () => request<EventItem[]>("/events"),
  listReminders: () => request<Reminder[]>("/reminders"),
  listIdeas: () => request<Idea[]>("/ideas"),

  transcribeAudio: async (audioBlob: Blob): Promise<{ text: string }> => {
    const token = useAuthStore.getState().accessToken;
    const formData = new FormData();
    formData.append("file", audioBlob, "audio.webm");
    const response = await fetch(`${API_URL}/voice/transcribe`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: formData,
    });
    if (!response.ok) {
      throw new ApiError(response.status, "No se pudo transcribir el audio");
    }
    return response.json();
  },
};
