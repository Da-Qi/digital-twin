"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { C } from "@/lib/theme";

export function ChatInput({ onSend, disabled }: { onSend: (content: string) => void; disabled?: boolean }) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div style={{ display: "flex", gap: 6, maxWidth: 640, margin: "0 auto", alignItems: "flex-end" }}>
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={() => {
          const el = textareaRef.current;
          if (el) { el.style.height = "auto"; el.style.height = Math.min(el.scrollHeight, 160) + "px"; }
        }}
        placeholder="发一条消息…"
        rows={1}
        disabled={disabled}
        style={{
          flex: 1, padding: "8px 12px", borderRadius: 8, fontSize: 14, lineHeight: 1.5,
          border: "0.5px solid " + C.border, resize: "none", outline: "none",
          fontFamily: "inherit", background: C.bg, color: C.text,
        }}
      />
      <button
        onClick={handleSend}
        disabled={!input.trim() || disabled}
        style={{
          padding: "8px 14px", borderRadius: 8, fontSize: 13, fontWeight: 500,
          border: "none", cursor: "pointer",
          background: !input.trim() || disabled ? C.bgSec : "#1a1a1a",
          color: !input.trim() || disabled ? C.textTer : "#fff",
        }}
      >
        发送
      </button>
    </div>
  );
}
