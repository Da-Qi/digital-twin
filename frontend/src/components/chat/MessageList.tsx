"use client";

import type { Message } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";

const C = { text: "#1a1a1a", textSec: "#666", textTer: "#999", border: "#ddd", bg: "#fff", bgSec: "#f7f7f7" };

export function MessageList({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
        <p style={{ fontSize: 13, color: C.textTer }}>发送一条消息开始对话</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", display: "flex", flexDirection: "column", gap: 16 }}>
      {messages.map((msg, i) => (
        <MessageBubble key={msg.id || i} message={msg} />
      ))}
    </div>
  );
}
