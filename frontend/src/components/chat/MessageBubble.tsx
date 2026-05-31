"use client";

import { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "@/lib/types";
import { api } from "@/lib/api";
import { C } from "@/lib/theme";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isStreaming = message.id === "streaming";
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<"up" | "down" | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleFeedback = async (type: "up" | "down") => {
    setFeedbackGiven(type);
    if (type === "down") {
      setShowFeedback(true);
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
    try { await api.feedback.submit({ target_message_id: message.id, feedback_type: type === "up" ? "rating" : "correction" }); }
    catch {}
  };

  const handleSubmitCorrection = async () => {
    const text = feedbackText.trim();
    if (!text || submitting) return;
    setSubmitting(true);
    try {
      await api.feedback.submit({ target_message_id: message.id, feedback_type: "correction", user_input: text });
      setFeedbackText("");
      setShowFeedback(false);
    } catch (err) { console.error("Feedback submit failed:", err); }
    finally { setSubmitting(false); }
  };

  const handleCancelCorrection = () => {
    setFeedbackText("");
    setShowFeedback(false);
  };

  return (
    <div style={{ display: "flex", gap: 10, flexDirection: isUser ? "row-reverse" : "row", alignItems: "flex-start" }}>
      {/* Avatar */}
      <div style={{
        width: 28, height: 28, borderRadius: 6, flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 11, fontWeight: 500,
        background: isUser ? "#1a1a1a" : C.bgSec,
        color: isUser ? "#fff" : C.textTer,
        border: isUser ? "none" : "0.5px solid " + C.border,
      }}>
        {isUser ? "U" : "A"}
      </div>

      {/* Bubble */}
      <div style={{ maxWidth: "80%", display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start" }}>
        <div style={{
          padding: "8px 14px",
          borderRadius: 10,
          fontSize: 14,
          lineHeight: 1.6,
          wordBreak: "break-word",
          overflow: "hidden",
          background: isUser ? "#1a1a1a" : C.bgSec,
          color: isUser ? "#fff" : C.text,
          border: isUser ? "none" : "0.5px solid " + C.border,
        }}>
          {isUser ? (
            <p style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{message.content}</p>
          ) : (
            <div style={{ margin: 0 }}>
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p style={{ margin: 0, lineHeight: 1.6 }}>{children}</p>,
                  ul: ({ children }) => <ul style={{ margin: "4px 0", paddingLeft: 20 }}>{children}</ul>,
                  ol: ({ children }) => <ol style={{ margin: "4px 0", paddingLeft: 20 }}>{children}</ol>,
                  li: ({ children }) => <li style={{ margin: "1px 0" }}>{children}</li>,
                  pre: ({ children }) => (
                    <pre style={{ margin: "6px 0", padding: 10, borderRadius: 6, background: "#f0f0f0", overflow: "auto", fontSize: 12, lineHeight: 1.4 }}>{children}</pre>
                  ),
                  code: ({ children }) => (
                    <code style={{ fontSize: 12, padding: "1px 4px", borderRadius: 4, background: "#f0f0f0", wordBreak: "break-word" }}>{children}</code>
                  ),
                  strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                  a: ({ href, children }) => <a href={href} style={{ color: "#534AB7" }}>{children}</a>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Feedback */}
        {!isUser && !isStreaming && (
          <div style={{ display: "flex", gap: 2, marginTop: 4, paddingLeft: 2 }}>
            <button onClick={() => handleFeedback("up")} style={{ padding: 2, border: "none", background: "transparent", cursor: "pointer", color: feedbackGiven === "up" ? "#22c55e" : C.textTer }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
            </button>
            <button onClick={() => handleFeedback("down")} style={{ padding: 2, border: "none", background: "transparent", cursor: "pointer", color: feedbackGiven === "down" ? "#ef4444" : C.textTer }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10zM17 2h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"/></svg>
            </button>
          </div>
        )}
        {showFeedback && (
          <div style={{ width: "100%", marginTop: 6 }}>
            <textarea
              ref={textareaRef}
              placeholder="分身应该怎么回答？"
              rows={2}
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              style={{
                width: "100%", padding: "6px 10px",
                fontSize: 12, borderRadius: 6,
                border: "0.5px solid " + C.border, resize: "none",
                outline: "none", fontFamily: "inherit", boxSizing: "border-box",
              }}
            />
            <div style={{ display: "flex", gap: 4, marginTop: 4, justifyContent: "flex-end" }}>
              <button
                onClick={handleCancelCorrection}
                style={{ padding: "3px 8px", fontSize: 11, borderRadius: 4, border: "0.5px solid " + C.border, background: C.bg, cursor: "pointer", color: C.textSec }}
              >
                取消
              </button>
              <button
                onClick={handleSubmitCorrection}
                disabled={!feedbackText.trim() || submitting}
                style={{ padding: "3px 8px", fontSize: 11, borderRadius: 4, border: "none", background: !feedbackText.trim() || submitting ? C.bgSec : "#1a1a1a", cursor: "pointer", color: !feedbackText.trim() || submitting ? C.textTer : "#fff" }}
              >
                {submitting ? "提交中…" : "提交修正"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
