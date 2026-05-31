"use client";

import type { Message } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";
import { C } from "@/lib/theme";

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
