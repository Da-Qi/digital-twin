"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useChatStore } from "@/lib/store";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/chat/Sidebar";
import { ChatView } from "@/components/chat/ChatView";

export default function ChatIdPage() {
  const params = useParams();
  const { setCurrentConversation, setConversations } = useChatStore();

  useEffect(() => {
    if (params.id) {
      api.conversations.get(params.id as string).then(setCurrentConversation).catch(console.error);
    }
    api.conversations.list().then(setConversations).catch(console.error);
  }, [params.id, setCurrentConversation, setConversations]);

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <Sidebar />
      <ChatView />
    </div>
  );
}
