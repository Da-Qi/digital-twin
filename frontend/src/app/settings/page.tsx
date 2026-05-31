"use client";

import { Sidebar } from "@/components/chat/Sidebar";
import { C } from "@/lib/theme";

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div style={{ padding: "14px 16px", borderRadius: 8, background: C.bgSec, border: "0.5px solid " + C.border }}>
    <p style={{ fontSize: 11, fontWeight: 600, color: C.textTer, textTransform: "uppercase", letterSpacing: "0.5px", margin: "0 0 10px" }}>{title}</p>
    {children}
  </div>
);

const Row = ({ label, value }: { label: string; value: string }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0" }}>
    <span style={{ fontSize: 12, color: C.textSec }}>{label}</span>
    <span style={{ fontSize: 13, color: C.text }}>{value}</span>
  </div>
);

export default function SettingsPage() {
  return (
    <div style={{ display: "flex", height: "100vh", background: C.bg }}>
      <Sidebar />
      <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
        <div style={{ maxWidth: 600, margin: "0 auto" }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, color: C.text, margin: "0 0 4px" }}>设置</h1>
          <p style={{ fontSize: 13, color: C.textTer, margin: "0 0 20px" }}>配置数字分身的行为</p>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Section title="LLM 配置">
              <Row label="模型" value="deepseek-chat (默认)" />
              <Row label="温度" value="0.7" />
            </Section>

            <Section title="RAG 配置">
              <Row label="分块大小" value="800 tokens" />
              <Row label="检索数量" value="8 块" />
            </Section>

            <Section title="记忆配置">
              <Row label="自动分析" value="每 10 次对话" />
              <Row label="自动批准微调" value="已启用" />
            </Section>
          </div>
        </div>
      </div>
    </div>
  );
}
