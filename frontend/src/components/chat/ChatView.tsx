"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/lib/store";
import { api } from "@/lib/api";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { ErrorBoundary } from "./ErrorBoundary";
import { C } from "@/lib/theme";
import type { Message } from "@/lib/types";

export function ChatView() {
  const {
    currentConversation, messages, setMessages, addMessage,
    setIsStreaming, clearStreamContent, isStreaming, streamingContent,
  } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (currentConversation) {
      api.conversations.messages.list(currentConversation.id).then(setMessages).catch(console.error);
    } else {
      setMessages([]);
    }
  }, [currentConversation?.id, setMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = async (content: string) => {
    if (!currentConversation || !content.trim() || isStreaming) return;

    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`, conversation_id: currentConversation.id,
      role: "user", content, token_count: 0, correction_flag: false, created_at: new Date().toISOString(),
    };
    addMessage(tempUserMsg);
    setIsStreaming(true);
    clearStreamContent();

    try {
      const response = await api.conversations.messages.sendStream(currentConversation.id, content);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No reader");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data) {
              try { const p = JSON.parse(data); if (p.token) useChatStore.getState().appendStreamContent(p.token); }
              catch { useChatStore.getState().appendStreamContent(data); }
            }
          }
        }
      }
    } catch (err) { console.error("Stream error:", err); }
    finally {
      clearStreamContent();
      setIsStreaming(false);
      // Use fresh state to avoid stale closure if user switched conversation during streaming
      const conv = useChatStore.getState().currentConversation;
      if (conv) {
        try {
          const msgs = await api.conversations.messages.list(conv.id);
          setMessages(msgs);
        } catch (err) { console.error("Failed to reload messages:", err); }
      }
    }
  };

  // Empty state
  if (!currentConversation) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: C.bg }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: C.bgSec, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px", fontSize: 18 }}>◇</div>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: C.text, margin: "0 0 4px" }}>数字分身</h2>
          <p style={{ fontSize: 13, color: C.textTer, maxWidth: 300, lineHeight: 1.5, margin: 0 }}>
            开始对话，聊得越多分身越了解你。
          </p>
        </div>
      </div>
    );
  }

  const allMessages = streamingContent
    ? [...messages, { id: "streaming", conversation_id: currentConversation!.id, role: "assistant" as const, content: streamingContent, token_count: 0, correction_flag: false, created_at: new Date().toISOString() }]
    : messages;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", background: C.bg }}>
      {/* Header */}
      <div style={{ padding: "10px 16px", borderBottom: "0.5px solid " + C.borderLight }}>
        <h2 style={{ fontSize: 13, fontWeight: 500, color: C.text, margin: 0 }}>{currentConversation.title || "对话"}</h2>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: "auto", padding: "16px 16px 8px" }}>
        <ErrorBoundary>
          <MessageList messages={allMessages} />
        </ErrorBoundary>
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{ padding: "10px 16px 14px", borderTop: "0.5px solid " + C.borderLight }}>
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
