const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Conversations
  conversations: {
    list: () => request<import("./types").Conversation[]>("/conversations"),
    create: (title?: string) =>
      request<import("./types").Conversation>("/conversations", {
        method: "POST",
        body: JSON.stringify({ title }),
      }),
    get: (id: string) => request<import("./types").Conversation>(`/conversations/${id}`),
    delete: (id: string) => request<void>(`/conversations/${id}`, { method: "DELETE" }),
    messages: {
      list: (convId: string) => request<import("./types").Message[]>(`/conversations/${convId}/messages`),
      send: (convId: string, content: string, stream = true) =>
        request<import("./types").Message>(`/conversations/${convId}/messages`, {
          method: "POST",
          body: JSON.stringify({ content, stream }),
        }),
      sendStream: (convId: string, content: string) => {
        const url = `${API_BASE}/conversations/${convId}/messages`;
        return fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, stream: true }),
        });
      },
    },
  },

  // Documents
  documents: {
    list: async (page = 1, size = 20) => {
      const res = await request<{items: import("./types").Document[]; total: number; page: number; size: number}>(`/documents?page=${page}&size=${size}`);
      return res.items;
    },
    upload: async (file: File, authorship = "unknown", title?: string) => {
      const form = new FormData();
      form.append("file", file);
      form.append("authorship", authorship);
      if (title) form.append("title", title);
      const res = await fetch(`${API_BASE}/documents/upload`, { method: "POST", body: form });
      if (!res.ok) throw new ApiError(res.status, await res.text());
      return res.json() as Promise<import("./types").Document>;
    },
    delete: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  },

  // Personality
  personality: {
    current: () => request<import("./types").PersonalityProfile>("/personality/current"),
    analyze: () => request<any>("/personality/analyze", { method: "POST" }),
    proposals: {
      list: () => request<any[]>("/personality/proposals/pending"),
      approve: (id: string) => request<any>(`/personality/proposals/${id}/approve`, { method: "POST" }),
      reject: (id: string) => request<any>(`/personality/proposals/${id}/reject`, { method: "POST" }),
    },
  },

  // Feedback
  feedback: {
    submit: (data: {
      target_message_id: string;
      feedback_type: string;
      classification?: string;
      user_input?: string;
      extracted_correction?: any;
    }) => request<import("./types").Feedback>("/feedback", { method: "POST", body: JSON.stringify(data) }),
  },

  // Knowledge
  knowledge: {
    graph: (nodeType?: string) => request<any>(`/knowledge/graph${nodeType ? `?node_type=${nodeType}` : ""}`),
    search: (q: string) => request<any[]>(`/knowledge/search?q=${encodeURIComponent(q)}`),
  },
};
