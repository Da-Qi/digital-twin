"use client";

import { useState } from "react";
import { MessageSquare, User, BookOpen, FileText, Settings } from "lucide-react";
import Link from "next/link";
import { useChatStore } from "@/lib/store";
import { api } from "@/lib/api";
import { C } from "@/lib/theme";

export function Sidebar() {
  const { conversations, setConversations, setCurrentConversation, currentConversation, pendingProposalsCount } =
    useChatStore();
  const [collapsed, setCollapsed] = useState(false);

  const handleNewChat = async () => {
    try {
      const conv = await api.conversations.create("New conversation");
      setConversations([conv, ...conversations]);
      setCurrentConversation(conv);
      window.history.pushState(null, "", `/chat/${conv.id}`);
    } catch (err) {
      console.error("Failed to create conversation:", err);
    }
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      width: collapsed ? 56 : 220,
      borderRight: "0.5px solid " + C.border,
      background: C.bg,
      transition: "width .2s",
      flexShrink: 0,
    }}>
      {/* New chat button */}
      <div style={{ padding: 12, borderBottom: "0.5px solid " + C.borderLight }}>
        <button
          onClick={handleNewChat}
          style={{
            display: "flex", alignItems: "center", gap: 6,
            width: "100%", padding: "6px 10px",
            borderRadius: 6, border: "0.5px solid " + C.border,
            fontSize: 12, cursor: "pointer",
            background: C.bg, color: C.textSec,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          {!collapsed && <span>新建对话</span>}
        </button>
      </div>

      {/* Conversations */}
      {!collapsed && (
        <div style={{ flex: 1, overflow: "auto", padding: "6px 8px" }}>
          <div style={{ padding: "8px 10px 4px", fontSize: 10, fontWeight: 600, color: C.textTer, letterSpacing: "0.5px" }}>
            历史对话
          </div>
          {conversations.length === 0 ? (
            <div style={{ padding: "12px 10px", fontSize: 12, color: C.textTer, textAlign: "center" }}>
              暂无对话
            </div>
          ) : (
            conversations.slice(0, 20).map((conv) => (
              <div
                key={conv.id}
                style={{ position: "relative" }}
                onMouseEnter={(e) => { const btn = e.currentTarget.querySelector('.sidebar-delete-btn') as HTMLElement; if (btn) btn.style.opacity = '1'; }}
                onMouseLeave={(e) => { const btn = e.currentTarget.querySelector('.sidebar-delete-btn') as HTMLElement; if (btn) btn.style.opacity = '0'; }}
              >
                <button
                  onClick={() => {
                    setCurrentConversation(conv);
                    window.history.pushState(null, "", `/chat/${conv.id}`);
                  }}
                  style={{
                    display: "flex", alignItems: "center", gap: 6,
                    width: "100%", padding: "6px 10px",
                    borderRadius: 6, textAlign: "left", cursor: "pointer",
                    fontSize: 12, border: "none", paddingRight: 28,
                    background: currentConversation?.id === conv.id ? C.accentBg : "transparent",
                    color: currentConversation?.id === conv.id ? C.accent : C.textSec,
                  }}
                >
                  <MessageSquare size={12} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {conv.title || `对话 ${conv.created_at?.slice(0, 10)}`}
                  </span>
                </button>
                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    try {
                      await api.conversations.delete(conv.id);
                      useChatStore.getState().removeConversation(conv.id);
                    } catch (err) { console.error("Delete failed:", err); }
                  }}
                  title="删除对话"
                  style={{
                    position: "absolute", right: 4, top: "50%", transform: "translateY(-50%)",
                    padding: 3, border: "none", background: "transparent", cursor: "pointer",
                    color: C.textTer, opacity: 0, borderRadius: 4,
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.opacity = "1"}
                  onMouseLeave={(e) => e.currentTarget.style.opacity = "0"}
                  onFocus={(e) => e.currentTarget.style.opacity = "1"}
                  onBlur={(e) => e.currentTarget.style.opacity = "0"}
                  className="sidebar-delete-btn"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* Bottom nav */}
      <div style={{ padding: 6, borderTop: "0.5px solid " + C.borderLight }}>
        {[
          { href: "/chat", icon: MessageSquare, label: "对话" },
          { href: "/personality", icon: User, label: "人格", badge: pendingProposalsCount },
          { href: "/knowledge", icon: BookOpen, label: "知识" },
          { href: "/documents", icon: FileText, label: "文档" },
          { href: "/settings", icon: Settings, label: "设置" },
        ].map(({ href, icon: Icon, label, badge }) => (
          <Link
            key={href}
            href={href}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 10px", borderRadius: 6,
              fontSize: 12, textDecoration: "none",
              color: C.textSec,
            }}
          >
            <Icon size={14} />
            {!collapsed && (
              <span style={{ flex: 1 }}>{label}</span>
            )}
            {badge ? (
              <span style={{ background: C.accent, color: "#fff", fontSize: 10, padding: "1px 5px", borderRadius: 8 }}>{badge}</span>
            ) : null}
          </Link>
        ))}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        style={{
          padding: "6px 10px", fontSize: 10, color: C.textTer,
          border: "none", borderTop: "0.5px solid " + C.borderLight,
          background: "transparent", cursor: "pointer",
        }}
      >
        {collapsed ? "→" : "←"}
      </button>
    </div>
  );
}
