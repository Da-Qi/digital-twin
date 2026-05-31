"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Document } from "@/lib/types";
import { Sidebar } from "@/components/chat/Sidebar";
import { C } from "@/lib/theme";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => { api.documents.list().then(setDocuments).catch(console.error); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true);
    try { const doc = await api.documents.upload(file, "user"); setDocuments((prev) => [doc, ...prev]); }
    catch (err) { console.error("Upload failed:", err); }
    finally { setUploading(false); e.target.value = ""; }
  };

  const handleDelete = async (id: string) => {
    try { await api.documents.delete(id); setDocuments((prev) => prev.filter((d) => d.id !== id)); }
    catch (err) { console.error("Delete failed:", err); }
  };

  const StatusIcon = ({ doc }: { doc: Document }) => {
    const ks = doc.metadata?.knowledge_status;
    if (doc.processing_status === "failed") return <span style={{ color: "#ef4444", fontSize: 11 }}>失败</span>;
    if (doc.processing_status !== "ready") return <span style={{ color: C.textTer, fontSize: 11 }}>处理中…</span>;
    if (!ks || ks === "pending") return <span style={{ color: "#22c55e", fontSize: 11 }}>就绪</span>;
    if (ks === "processing") return <span style={{ color: "#f59e0b", fontSize: 11 }}>知识抽取中…</span>;
    if (ks === "failed") return <span style={{ color: "#ef4444", fontSize: 11 }}>知识抽取失败</span>;
    return <span style={{ color: "#22c55e", fontSize: 11 }}>就绪</span>;
  };

  return (
    <div style={{ display: "flex", height: "100vh", background: C.bg }}>
      <Sidebar />
      <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
        <div style={{ maxWidth: 600, margin: "0 auto" }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, color: C.text, margin: "0 0 4px" }}>文档</h1>
          <p style={{ fontSize: 13, color: C.textTer, margin: "0 0 20px" }}>上传文档让分身学习新知识</p>

          {/* Upload */}
          <label style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
            padding: "28px 20px", marginBottom: 20,
            border: "0.5px dashed " + C.border, borderRadius: 8, cursor: "pointer",
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C.textTer} strokeWidth={1.5}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span style={{ fontSize: 13, color: C.textSec }}>{uploading ? "上传中…" : "点击上传 PDF 或 Markdown"}</span>
            <span style={{ fontSize: 11, color: C.textTer }}>最大 50MB</span>
            <input type="file" accept=".md,.pdf,text/markdown,application/pdf" onChange={handleUpload} style={{ display: "none" }} disabled={uploading} />
          </label>

          {/* List */}
          {documents.length === 0 ? (
            <div style={{ textAlign: "center", padding: 32, fontSize: 13, color: C.textTer }}>
              还没有上传的文档
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {documents.map((doc) => (
                <div key={doc.id} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "10px 14px", borderRadius: 8, background: C.bgSec, border: "0.5px solid " + C.border,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={C.textTer} strokeWidth={1.5}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <div>
                      <p style={{ fontSize: 13, fontWeight: 500, color: C.text, margin: 0 }}>{doc.filename}</p>
                      <p style={{ fontSize: 11, color: C.textTer, margin: 0 }}>{doc.chunk_count} 块 · {(doc.char_count / 1000).toFixed(1)}K 字</p>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <StatusIcon doc={doc} />
                    <button onClick={() => handleDelete(doc.id)} style={{ padding: 4, border: "none", background: "transparent", cursor: "pointer", color: C.textTer }}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
