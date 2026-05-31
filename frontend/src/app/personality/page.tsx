"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PersonalityProfile } from "@/lib/types";
import { Sidebar } from "@/components/chat/Sidebar";
import { C } from "@/lib/theme";

export default function PersonalityPage() {
  const [profile, setProfile] = useState<PersonalityProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.personality.current().then(setProfile).catch(() => setProfile(null)).finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ display: "flex", height: "100vh", background: C.bg }}>
      <Sidebar />
      <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
        <div style={{ maxWidth: 600, margin: "0 auto" }}>
          {/* Header */}
          <div style={{ marginBottom: 24 }}>
            <h1 style={{ fontSize: 20, fontWeight: 600, color: C.text, margin: "0 0 4px" }}>人格档案</h1>
            <p style={{ fontSize: 13, color: C.textTer, margin: 0 }}>数字分身当前的人格模型</p>
          </div>

          {loading ? (
            <p style={{ fontSize: 13, color: C.textTer, textAlign: "center", padding: 40 }}>加载中…</p>
          ) : !profile ? (
            <div style={{ textAlign: "center", padding: 40 }}>
              <p style={{ fontSize: 13, color: C.textTer }}>还没有人格档案。开始聊天来构建分身的人格。</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* Version info */}
              <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12, color: C.textSec, marginBottom: 4 }}>
                <span style={{ padding: "2px 6px", borderRadius: 4, background: C.bgSec, border: "0.5px solid " + C.border, fontSize: 11 }}>v{profile.version}</span>
                <span>激活于 {profile.activated_at?.slice(0, 10) || "N/A"}</span>
                <button
                  onClick={async () => {
                    await api.personality.analyze();
                    setProfile(await api.personality.current());
                  }}
                  style={{ marginLeft: "auto", padding: "4px 10px", fontSize: 12, borderRadius: 6, border: "0.5px solid " + C.border, background: C.bg, cursor: "pointer", color: C.textSec }}
                >
                  分析
                </button>
              </div>

              {/* Traits */}
              {profile.traits.map((trait) => (
                <div key={trait.id} style={{ padding: "12px 16px", borderRadius: 8, background: C.bgSec, border: "0.5px solid " + C.border }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 500, color: C.textTer, textTransform: "uppercase", letterSpacing: "0.3px" }}>{trait.category}</span>
                    <span style={{ fontSize: 11, color: C.textTer }}>{(trait.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: C.text }}>{trait.trait_name}</span>
                    <span style={{ fontSize: 12, color: C.accent }}>
                      {typeof trait.value === "object" ? JSON.stringify(trait.value).slice(0, 50) : String(trait.value)}
                    </span>
                  </div>
                  <div style={{ marginTop: 8, height: 3, borderRadius: 2, background: C.borderLight, overflow: "hidden" }}>
                    <div style={{ height: "100%", borderRadius: 2, background: C.accent, width: `${trait.confidence * 100}%` }} />
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
