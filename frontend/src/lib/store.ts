import { create } from "zustand";
import type { Conversation, Message } from "./types";

interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  pendingProposalsCount: number;

  setConversations: (convs: Conversation[]) => void;
  setCurrentConversation: (conv: Conversation | null) => void;
  addConversation: (conv: Conversation) => void;
  removeConversation: (id: string) => void;
  setMessages: (msgs: Message[]) => void;
  addMessage: (msg: Message) => void;
  setIsStreaming: (v: boolean) => void;
  appendStreamContent: (token: string) => void;
  clearStreamContent: () => void;
  setPendingProposalsCount: (n: number) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  isStreaming: false,
  streamingContent: "",
  pendingProposalsCount: 0,

  setConversations: (conversations) => set({ conversations }),
  setCurrentConversation: (currentConversation) => set({ currentConversation }),
  addConversation: (conv) =>
    set((state) => ({ conversations: [conv, ...state.conversations] })),
  removeConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      currentConversation: state.currentConversation?.id === id ? null : state.currentConversation,
    })),
  setMessages: (messages) => set({ messages }),
  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  appendStreamContent: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),
  clearStreamContent: () => set({ streamingContent: "" }),
  setPendingProposalsCount: (n) => set({ pendingProposalsCount: n }),
}));
