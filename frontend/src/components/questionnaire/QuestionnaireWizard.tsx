"use client";

import { useState, useCallback, useEffect, useRef } from "react";

/* ─── Types ─── */

interface PairItem {
  a: string; ad: string; b: string; bd: string;
}

interface Question {
  type: "chips" | "slider" | "pairs" | "textarea";
  key: string;
  label: string;
  hint?: string;
  options?: string[];
  left?: string;
  right?: string;
  pairs?: PairItem[];
  placeholder?: string;
}

interface Step {
  id: string;
  badge: string;
  badgeColor: string;
  badgeText: string;
  title: string;
  sub: string;
  questions: Question[];
}

/* ─── Step Data ─── */

const STEPS: Step[] = [
  {
    id: "personality",
    badge: "性格基调",
    badgeColor: "#EEEDFE", badgeText: "#3C3489",
    title: "你是哪种人？",
    sub: "选择最符合你的描述，可多选。这些标签会直接写入分身的核心人格档案。",
    questions: [
      {
        type: "chips", key: "traits",
        label: "性格特质",
        hint: "挑3-6个最像你的",
        options: [
          "直接果断", "温和体贴", "逻辑理性", "感性直觉",
          "幽默爱开玩笑", "严肃认真", "好奇爱探索", "踏实务实",
          "有创造力", "独立自主", "喜欢协作", "完美主义",
        ],
      },
      {
        type: "pairs", key: "introvert",
        label: "社交能量",
        pairs: [
          { a: "独处充电型", ad: "需要独处来恢复精力，社交后需要安静", b: "社交充电型", bd: "从和人交流中获得能量，独处会无聊" },
          { a: "大局思考", ad: "先想整体框架，再考虑细节", b: "细节导向", bd: "注重细节和执行，从具体出发" },
        ],
      },
    ],
  },
  {
    id: "voice",
    badge: "表达风格",
    badgeColor: "#E1F5EE", badgeText: "#085041",
    title: "你怎么说话？",
    sub: "语气是分身最难复制、也最关键的部分。",
    questions: [
      {
        type: "slider", key: "formal",
        label: "正式程度",
        left: "随意口语", right: "严谨正式",
        hint: "平时和朋友说话 vs 写工作邮件之间的感觉",
      },
      {
        type: "slider", key: "verbose",
        label: "表达密度",
        left: "简洁精炼", right: "详细展开",
        hint: "倾向于用一句话说完，还是喜欢多说背景和原因",
      },
      {
        type: "chips", key: "voice_habits",
        label: "口头习惯",
        hint: "你说话时常有哪些特征",
        options: [
          "爱用比喻和类比", "经常反问", "喜欢举例子",
          "说话带点反讽", "习惯先说结论", "爱加'但是'转折",
          "喜欢列清单", "说话很直白", "会用脏话或口头禅",
          "喜欢加免责声明",
        ],
      },
      {
        type: "textarea", key: "sample",
        label: "写一段最像你的话",
        hint: "比如你最近发的一条朋友圈、给朋友的消息、或者你会怎么解释一件事。这是分身学习你语气最直接的素材。",
        placeholder: "随便写，越自然越好…",
      },
    ],
  },
  {
    id: "values",
    badge: "价值观与决策",
    badgeColor: "#FAEEDA", badgeText: "#633806",
    title: "你怎么做判断？",
    sub: "分身遇到两难问题时，需要知道你的取舍逻辑。",
    questions: [
      {
        type: "pairs", key: "decisions",
        label: "决策风格",
        pairs: [
          { a: "快速行动", ad: "宁可先做再调整，不怕出错", b: "深思熟虑", bd: "想清楚再动，不喜欢返工" },
          { a: "数据优先", ad: "用数字和证据说服自己", b: "直觉优先", bd: "相信感觉和经验判断" },
          { a: "坚守原则", ad: "有底线，不轻易妥协", b: "灵活变通", bd: "实用主义，根据情况调整" },
        ],
      },
      {
        type: "chips", key: "values",
        label: "核心价值观",
        hint: "最重要的3-5个",
        options: [
          "自由独立", "家庭", "成就感", "财富安全", "诚实正直",
          "创造力", "影响力", "学习成长", "健康", "公平正义",
          "友情", "冒险",
        ],
      },
      {
        type: "textarea", key: "regret",
        label: "你最不后悔的一个决定",
        hint: "不用完整故事，一两句说清楚就行。这能帮分身理解你真正看重什么。",
        placeholder: "做了某件事，或者放弃了某件事…",
      },
    ],
  },
  {
    id: "knowledge",
    badge: "知识与专长",
    badgeColor: "#FAECE7", badgeText: "#712B13",
    title: "你擅长什么、关心什么？",
    sub: "分身需要知道你的知识版图，才能在对应领域真正替代你思考。",
    questions: [
      {
        type: "textarea", key: "expertise",
        label: "你的专业领域",
        hint: "工作、学习、或花了大量时间钻研的领域。写得越具体越好。",
        placeholder: "比如：做了8年产品经理，专注B2B SaaS；学了3年钢琴，会一点乐理…",
      },
      {
        type: "chips", key: "interests",
        label: "长期关注的话题",
        hint: "不限于工作，个人爱好也算",
        options: [
          "科技与AI", "投资理财", "心理学", "哲学", "设计", "写作",
          "音乐", "游戏", "健身运动", "历史", "政治经济", "科学",
          "美食", "旅行", "电影", "创业",
        ],
      },
      {
        type: "textarea", key: "opinions",
        label: "你有强烈看法的一件事",
        hint: "任何领域都行——行业现状、人生道理、某个观点。分身需要知道你的'不寻常立场'，才不会说模板化的话。",
        placeholder: "我一直觉得……",
      },
    ],
  },
  {
    id: "limits",
    badge: "边界与禁区",
    badgeColor: "#FCEBEB", badgeText: "#791F1F",
    title: "分身不能做什么？",
    sub: "设置边界和红线，避免分身在敏感场景里给出你不认可的回答。",
    questions: [
      {
        type: "chips", key: "avoid_topics",
        label: "不希望分身涉及的话题",
        hint: "遇到这些话题时，分身应该回避或转移",
        options: [
          "家庭私事", "财务细节", "健康隐私", "政治立场",
          "宗教信仰", "过去的感情", "工作内部信息", "某些人际关系",
        ],
      },
      {
        type: "pairs", key: "limits",
        label: "分身的处理方式",
        pairs: [
          { a: "遇到不确定就说不知道", ad: "宁可承认局限，不乱猜测", b: "尽力推断给出答案", bd: "基于已有信息做出最合理判断" },
          { a: "保持中立立场", ad: "不主动表达强烈观点", b: "表达我的真实立场", bd: "直接说出我会怎么看这件事" },
        ],
      },
      {
        type: "textarea", key: "extra",
        label: "其他补充",
        hint: "有什么上面没覆盖到、但你认为分身必须知道的事情？",
        placeholder: "比如：我最近经历了某件事，我在意某种表达方式，我希望分身在某些场合特别谨慎…",
      },
    ],
  },
];

/* ─── CSS Variables 模拟 ─── */

const COLORS = {
  "color-text-primary": "#1a1a1a",
  "color-text-secondary": "#666",
  "color-text-tertiary": "#999",
  "color-border-primary": "#888",
  "color-border-secondary": "#ddd",
  "color-border-tertiary": "#eee",
  "color-background-primary": "#fff",
  "color-background-secondary": "#f7f7f7",
};

/* ─── Main ─── */

export function QuestionnaireWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 初始化 data
  useEffect(() => {
    setData((prev) => {
      if (Object.keys(prev).length) return prev;
      const init: Record<string, any> = {};
      STEPS.forEach((s) => { init[s.id] = {}; });
      return init;
    });
  }, []);

  const toggleChip = useCallback((sectionId: string, key: string, val: string) => {
    setData((prev) => {
      const sec = { ...(prev[sectionId] || {}) };
      const arr: string[] = [...(sec[key] || [])];
      const i = arr.indexOf(val);
      if (i >= 0) arr.splice(i, 1);
      else arr.push(val);
      sec[key] = arr;
      return { ...prev, [sectionId]: sec };
    });
  }, []);

  const selectPair = useCallback((sectionId: string, key: string, val: string) => {
    setData((prev) => {
      const sec = { ...(prev[sectionId] || {}) };
      sec[key] = val;
      return { ...prev, [sectionId]: sec };
    });
  }, []);

  const updateField = useCallback((sectionId: string, key: string, val: any) => {
    setData((prev) => {
      const sec = { ...(prev[sectionId] || {}) };
      sec[key] = val;
      return { ...prev, [sectionId]: sec };
    });
  }, []);

  const go = useCallback((idx: number) => {
    setStep(idx);
    if (containerRef.current) containerRef.current.scrollTop = 0;
  }, []);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const payload = {
        personality: data.personality || {},
        voice: data.voice || {},
        values: data.values || {},
        knowledge: data.knowledge || {},
        limits: data.limits || {},
      };
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/questionnaire/submit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      setResult(await res.json());
    } catch (err) {
      console.error("submit error", err);
    } finally {
      setSubmitting(false);
    }
  };

  const s = STEPS[step];
  const pct = Math.round(((step + 1) / STEPS.length) * 100);

  if (result) {
    return <ResultsView data={data} onComplete={onComplete} />;
  }

  return (
    <div ref={containerRef} style={{ background: COLORS["color-background-primary"], minHeight: "100vh", padding: "0.5rem 0 2rem" }}>
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "0 1rem" }}>
        {/* Progress bar */}
        <div style={{ height: 4, background: COLORS["color-border-tertiary"], borderRadius: 2, marginBottom: "1.5rem" }}>
          <div style={{ height: 4, background: "#7F77DD", borderRadius: 2, width: pct + "%", transition: "width .4s ease" }} />
        </div>

        {/* Step nav */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", gap: 6 }}>
            {STEPS.map((_, i) => (
              <div
                key={i}
                style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: i === step ? "#7F77DD" : i < step ? "#AFA9EC" : COLORS["color-border-secondary"],
                  transition: "background .2s",
                }}
              />
            ))}
          </div>
          <div style={{ fontSize: 13, color: COLORS["color-text-tertiary"] }}>
            {step + 1} / {STEPS.length}
          </div>
        </div>

        {/* Step content */}
        <div>
          {/* Badge */}
          <div
            style={{
              display: "inline-block", fontSize: 12, fontWeight: 500,
              padding: "3px 10px", borderRadius: 20, marginBottom: 12,
              background: s.badgeColor, color: s.badgeText,
            }}
          >
            {s.badge}
          </div>

          <h2 style={{ fontSize: 18, fontWeight: 500, color: COLORS["color-text-primary"], margin: "0 0 4px" }}>
            {s.title}
          </h2>
          <p style={{ fontSize: 13, color: COLORS["color-text-secondary"], margin: "0 0 1.5rem", lineHeight: 1.5 }}>
            {s.sub}
          </p>

          {s.questions.map((q) => (
            <QuestionField
              key={`${s.id}-${q.key}`}
              question={q}
              sectionId={s.id}
              data={data[s.id] || {}}
              onUpdate={updateField}
              onToggleChip={toggleChip}
              onSelectPair={selectPair}
            />
          ))}
        </div>

        {/* Navigation */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: "1.5rem" }}>
          {step > 0 && (
            <button
              onClick={() => go(step - 1)}
              style={{
                padding: "7px 18px", borderRadius: 6,
                border: "0.5px solid " + COLORS["color-border-secondary"],
                fontSize: 14, cursor: "pointer",
                background: COLORS["color-background-primary"],
                color: COLORS["color-text-primary"],
              }}
            >
              上一步
            </button>
          )}
          {step < STEPS.length - 1 ? (
            <button
              onClick={() => go(step + 1)}
              style={{
                padding: "7px 18px", borderRadius: 6,
                border: "0.5px solid #534AB7",
                fontSize: 14, cursor: "pointer",
                background: "#534AB7", color: "#fff",
              }}
            >
              下一步
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              style={{
                padding: "7px 18px", borderRadius: 6,
                border: "0.5px solid #534AB7",
                fontSize: 14, cursor: "pointer",
                background: "#534AB7", color: "#fff",
                opacity: submitting ? 0.6 : 1,
              }}
            >
              {submitting ? "生成中…" : "生成人格档案 ↗"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Question Fields ─── */

function QuestionField({
  question: q,
  sectionId,
  data,
  onUpdate,
  onToggleChip,
  onSelectPair,
}: {
  question: Question;
  sectionId: string;
  data: Record<string, any>;
  onUpdate: (sid: string, key: string, val: any) => void;
  onToggleChip: (sid: string, key: string, val: string) => void;
  onSelectPair: (sid: string, key: string, val: string) => void;
}) {
  if (q.type === "chips") {
    const selected: string[] = data[q.key] || [];
    return (
      <div style={{ padding: "1.5rem 0 2rem" }}>
        <p style={{ fontSize: 16, fontWeight: 500, color: COLORS["color-text-primary"], margin: 0 }}>{q.label}</p>
        {q.hint && <p style={{ fontSize: 13, color: COLORS["color-text-secondary"], margin: "4px 0 14px", lineHeight: 1.5 }}>{q.hint}</p>}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 4 }}>
          {(q.options || []).map((opt) => {
            const on = selected.includes(opt);
            return (
              <div
                key={opt}
                onClick={() => onToggleChip(sectionId, q.key, opt)}
                style={{
                  padding: "6px 14px", borderRadius: 20,
                  border: on ? "0.5px solid #534AB7" : "0.5px solid " + COLORS["color-border-secondary"],
                  fontSize: 13, cursor: "pointer",
                  color: on ? "#3C3489" : COLORS["color-text-secondary"],
                  background: on ? "#EEEDFE" : COLORS["color-background-primary"],
                  transition: "all .15s",
                }}
              >
                {opt}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (q.type === "slider") {
    const val = data[q.key] !== undefined ? data[q.key] : 50;
    return (
      <div style={{ padding: "1.5rem 0 2rem" }}>
        <p style={{ fontSize: 16, fontWeight: 500, color: COLORS["color-text-primary"], margin: 0 }}>{q.label}</p>
        {q.hint && <p style={{ fontSize: 13, color: COLORS["color-text-secondary"], margin: "4px 0 14px", lineHeight: 1.5 }}>{q.hint}</p>}
        <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "6px 0 10px" }}>
          <span style={{ fontSize: 12, color: COLORS["color-text-tertiary"], minWidth: 52 }}>{q.left}</span>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={val}
            onChange={(e) => onUpdate(sectionId, q.key, parseInt(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ fontSize: 12, color: COLORS["color-text-tertiary"], minWidth: 52, textAlign: "right" }}>{q.right}</span>
        </div>
      </div>
    );
  }

  if (q.type === "pairs") {
    return (
      <div style={{ padding: "1.5rem 0 2rem" }}>
        <p style={{ fontSize: 16, fontWeight: 500, color: COLORS["color-text-primary"], margin: 0 }}>{q.label}</p>
        {(q.pairs || []).map((pair, i) => {
          const pairKey = `${q.key}${i}`;
          const selected = data[pairKey];
          return (
            <div key={pairKey} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
              {[
                { val: "a", label: pair.a, desc: pair.ad },
                { val: "b", label: pair.b, desc: pair.bd },
              ].map((opt) => {
                const on = selected === opt.val;
                return (
                  <div
                    key={opt.val}
                    onClick={() => onSelectPair(sectionId, pairKey, opt.val)}
                    style={{
                      border: on ? "0.5px solid #534AB7" : "0.5px solid " + COLORS["color-border-secondary"],
                      borderRadius: 6,
                      padding: "12px 14px",
                      cursor: "pointer",
                      background: on ? "#EEEDFE" : "transparent",
                      transition: "all .15s",
                    }}
                  >
                    <p style={{ fontSize: 13, fontWeight: 500, color: on ? "#3C3489" : COLORS["color-text-primary"], margin: "0 0 3px" }}>
                      {opt.label}
                    </p>
                    <p style={{ fontSize: 12, color: on ? "#534AB7" : COLORS["color-text-secondary"], margin: 0, lineHeight: 1.4 }}>
                      {opt.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    );
  }

  if (q.type === "textarea") {
    return (
      <div style={{ padding: "1.5rem 0 2rem" }}>
        <p style={{ fontSize: 16, fontWeight: 500, color: COLORS["color-text-primary"], margin: 0 }}>{q.label}</p>
        {q.hint && <p style={{ fontSize: 13, color: COLORS["color-text-secondary"], margin: "4px 0 14px", lineHeight: 1.5 }}>{q.hint}</p>}
        <textarea
          value={data[q.key] || ""}
          onChange={(e) => onUpdate(sectionId, q.key, e.target.value)}
          placeholder={q.placeholder}
          rows={3}
          style={{
            width: "100%",
            border: "0.5px solid " + COLORS["color-border-secondary"],
            borderRadius: 6,
            padding: "10px 12px",
            fontSize: 14,
            color: COLORS["color-text-primary"],
            background: COLORS["color-background-primary"],
            resize: "vertical",
            minHeight: 72,
            lineHeight: 1.6,
            fontFamily: "inherit",
            outline: "none",
            boxSizing: "border-box",
          }}
          onFocus={(e) => e.target.style.borderColor = "#7F77DD"}
          onBlur={(e) => e.target.style.borderColor = COLORS["color-border-secondary"]}
        />
      </div>
    );
  }

  return null;
}

/* ─── Results View ─── */

function ResultsView({ data, onComplete }: { data: Record<string, any>; onComplete: () => void }) {
  const p = data.personality || {};
  const v = data.voice || {};
  const d = data.values || {};
  const k = data.knowledge || {};
  const l = data.limits || {};

  const formalVal = v.formal !== undefined ? v.formal : 50;
  const verbVal = v.verbose !== undefined ? v.verbose : 50;
  const formalLabel = formalVal < 35 ? "偏口语随意" : formalVal > 65 ? "偏正式严谨" : "中等正式度";
  const verbLabel = verbVal < 35 ? "简洁精炼" : verbVal > 65 ? "喜欢详细展开" : "表达适中";

  const dec0 = d.decisions0 === "a" ? "快速行动" : d.decisions0 === "b" ? "深思熟虑" : "未设定";
  const dec1 = d.decisions1 === "a" ? "数据优先" : d.decisions1 === "b" ? "直觉优先" : "未设定";
  const dec2 = d.decisions2 === "a" ? "坚守原则" : d.decisions2 === "b" ? "灵活变通" : "未设定";
  const soc = p.introvert0 === "a" ? "独处充电型" : p.introvert0 === "b" ? "社交充电型" : "未设定";
  const think = p.introvert1 === "a" ? "大局思考" : p.introvert1 === "b" ? "细节导向" : "未设定";
  const unc = l.limits0 === "a" ? "遇到不确定时说不知道" : l.limits0 === "b" ? "尽力推断给答案" : "未设定";
  const stance = l.limits1 === "a" ? "保持中立" : l.limits1 === "b" ? "表达真实立场" : "未设定";

  const tags = (arr: string[] | undefined) =>
    arr && arr.length
      ? arr.map((t) => (
          <span key={t} style={{ display: "inline-block", fontSize: 12, padding: "2px 10px", borderRadius: 20, background: "#EEEDFE", color: "#3C3489", margin: "2px 3px 2px 0" }}>
            {t}
          </span>
        ))
      : <span style={{ color: COLORS["color-text-tertiary"], fontSize: 13 }}>未填写</span>;

  const txt = (t: string | undefined) =>
    t && t.trim()
      ? <p style={{ fontSize: 14, color: COLORS["color-text-primary"], lineHeight: 1.6, margin: 0, whiteSpace: "pre-wrap" }}>{t.trim()}</p>
      : <p style={{ fontSize: 14, color: COLORS["color-text-tertiary"], margin: 0 }}>未填写</p>;

  return (
    <div style={{ background: COLORS["color-background-primary"], minHeight: "100vh", padding: "0.5rem 0 2rem" }}>
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "0 1rem" }}>
        <div style={{ height: 4, background: COLORS["color-border-tertiary"], borderRadius: 2, marginBottom: "1.5rem" }}>
          <div style={{ height: 4, background: "#7F77DD", borderRadius: 2, width: "100%", transition: "width .4s ease" }} />
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", gap: 6 }}>
            {STEPS.map((_, i) => (
              <div key={i} style={{ width: 8, height: 8, borderRadius: "50%", background: "#AFA9EC" }} />
            ))}
          </div>
          <div style={{ fontSize: 13, color: COLORS["color-text-tertiary"] }}>完成</div>
        </div>

        <div style={{ marginBottom: "1.5rem" }}>
          <div style={{ display: "inline-block", fontSize: 12, fontWeight: 500, padding: "3px 10px", borderRadius: 20, marginBottom: 12, background: "#E1F5EE", color: "#085041" }}>
            采集完成
          </div>
          <h2 style={{ fontSize: 18, fontWeight: 500, color: COLORS["color-text-primary"], margin: "0 0 4px" }}>人格档案初稿</h2>
          <p style={{ fontSize: 13, color: COLORS["color-text-secondary"], margin: "0 0 1.5rem", lineHeight: 1.5 }}>
            以下内容将作为你数字分身的初始 System Prompt。点击"导入分身"生成完整 Prompt 代码。
          </p>
        </div>

        {/* 性格特质 */}
        <div style={{ background: COLORS["color-background-secondary"], borderRadius: 8, padding: "1.25rem 1.5rem", marginBottom: "1rem" }}>
          <p style={{ fontSize: 12, color: COLORS["color-text-tertiary"], margin: "0 0 6px" }}>性格特质</p>
          <div>{tags(p.traits)}</div>
          <div style={{ marginTop: 8, fontSize: 13, color: COLORS["color-text-secondary"] }}>{soc} · {think}</div>
        </div>

        {/* 表达风格 */}
        <div style={{ background: COLORS["color-background-secondary"], borderRadius: 8, padding: "1.25rem 1.5rem", marginBottom: "1rem" }}>
          <p style={{ fontSize: 12, color: COLORS["color-text-tertiary"], margin: "0 0 6px" }}>表达风格</p>
          <div style={{ fontSize: 13, color: COLORS["color-text-primary"], marginBottom: 6 }}>{formalLabel} · {verbLabel}</div>
          <div>{tags(v.voice_habits)}</div>
          {v.sample && (
            <div style={{ marginTop: 10, borderLeft: "2px solid #AFA9EC", paddingLeft: 10, fontSize: 13, color: COLORS["color-text-secondary"], lineHeight: 1.6, fontStyle: "italic" }}>
              {v.sample}
            </div>
          )}
        </div>

        {/* 决策风格 */}
        <div style={{ background: COLORS["color-background-secondary"], borderRadius: 8, padding: "1.25rem 1.5rem", marginBottom: "1rem" }}>
          <p style={{ fontSize: 12, color: COLORS["color-text-tertiary"], margin: "0 0 6px" }}>决策风格</p>
          <div style={{ fontSize: 13, color: COLORS["color-text-primary"] }}>{dec0} · {dec1} · {dec2}</div>
          <div style={{ marginTop: 8 }}>{tags(d.values)}</div>
          {d.regret && (
            <div style={{ marginTop: 8, fontSize: 13, color: COLORS["color-text-secondary"], lineHeight: 1.5 }}>{d.regret}</div>
          )}
        </div>

        {/* 专长与关注领域 */}
        <div style={{ background: COLORS["color-background-secondary"], borderRadius: 8, padding: "1.25rem 1.5rem", marginBottom: "1rem" }}>
          <p style={{ fontSize: 12, color: COLORS["color-text-tertiary"], margin: "0 0 6px" }}>专长与关注领域</p>
          {txt(k.expertise)}
          <div style={{ marginTop: 8 }}>{tags(k.interests)}</div>
          {k.opinions && (
            <div style={{ marginTop: 8, borderLeft: "2px solid #F0997B", paddingLeft: 10, fontSize: 13, color: COLORS["color-text-secondary"], lineHeight: 1.6 }}>
              {k.opinions}
            </div>
          )}
        </div>

        {/* 边界设定 */}
        <div style={{ background: COLORS["color-background-secondary"], borderRadius: 8, padding: "1.25rem 1.5rem", marginBottom: "1rem" }}>
          <p style={{ fontSize: 12, color: COLORS["color-text-tertiary"], margin: "0 0 6px" }}>边界设定</p>
          <div style={{ fontSize: 13, color: COLORS["color-text-primary"], marginBottom: 6 }}>{unc} · {stance}</div>
          <div>{tags(l.avoid_topics)}</div>
          {l.extra && (
            <div style={{ marginTop: 8, fontSize: 13, color: COLORS["color-text-secondary"] }}>{l.extra}</div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: "1.5rem" }}>
          <button
            onClick={onComplete}
            style={{
              padding: "7px 18px", borderRadius: 6,
              border: "0.5px solid #534AB7",
              fontSize: 14, cursor: "pointer",
              background: "#534AB7", color: "#fff",
            }}
          >
            开始使用数字分身 →
          </button>
        </div>
      </div>
    </div>
  );
}
