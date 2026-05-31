"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/chat/Sidebar";
import { C } from "@/lib/theme";

const TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  concept: { bg: "#EEEDFE", text: "#534AB7" },
  skill: { bg: "#E1F5EE", text: "#085041" },
  technology: { bg: "#FAEEDA", text: "#633806" },
  person: { bg: "#FAECE7", text: "#712B13" },
  domain: { bg: "#FCEBEB", text: "#791F1F" },
  project: { bg: "#E8F4F8", text: "#065986" },
};

export default function KnowledgePage() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.knowledge.graph().then((data) => setNodes(data.nodes || [])).catch(() => setNodes([])).finally(() => setLoading(false));
  }, []);

  const typeColor = (type: string) => TYPE_COLORS[type] || { bg: C.bgSec, text: C.textSec };

  return (
    <div style={{ display: "flex", height: "100vh", background: C.bg }}>
      <Sidebar />
      <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
        <div style={{ maxWidth: 600, margin: "0 auto" }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, color: C.text, margin: "0 0 4px" }}>知识图谱</h1>
          <p style={{ fontSize: 13, color: C.textTer, margin: "0 0 20px" }}>分身从对话和文档中学到的知识</p>

          {loading ? (
            <p style={{ fontSize: 13, color: C.textTer, textAlign: "center", padding: 40 }}>加载中…</p>
          ) : nodes.length === 0 ? (
            <div style={{ textAlign: "center", padding: 40 }}>
              <p style={{ fontSize: 13, color: C.textTer }}>还没有知识。和分身聊天、上传文档来构建知识库。</p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {nodes.sort((a, b) => b.confidence - a.confidence).map((node) => {
                const c = typeColor(node.node_type);
                return (
                  <div key={node.id} style={{
                    padding: "12px 14px", borderRadius: 8, background: C.bgSec, border: "0.5px solid " + C.border,
                  }}>
                    <span style={{ display: "inline-block", padding: "1px 6px", borderRadius: 4, fontSize: 10, fontWeight: 500, background: c.bg, color: c.text, marginBottom: 4 }}>
                      {node.node_type}
                    </span>
                    <p style={{ fontSize: 13, fontWeight: 500, color: C.text, margin: "2px 0" }}>{node.label}</p>
                    {node.description && <p style={{ fontSize: 11, color: C.textTer, margin: "2px 0 0", lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.description}</p>}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
