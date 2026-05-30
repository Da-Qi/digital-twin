"use client";

import { useEffect } from "react";
import { useChatStore } from "@/lib/store";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/chat/Sidebar";
import { ChatView } from "@/components/chat/ChatView";

export default function ChatPage() {
  const { setConversations, setPendingProposalsCount } = useChatStore();

  useEffect(() => {
    api.conversations.list().then(setConversations).catch(console.error);
    api.personality.proposals.list().then((proposals) => {
      setPendingProposalsCount(proposals?.length || 0);
    }).catch(() => {});
  }, [setConversations, setPendingProposalsCount]);

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <Sidebar />
      <ChatView />
    </div>
  );
}
