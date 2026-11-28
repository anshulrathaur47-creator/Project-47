import React from "react";
import { AppIcon, Check, Chip, Cross, Cursor, CursorKey, FileIcon, MONO, Panel, SANS, SERIF, Theme, WindowBar, back, caret, clamp, ease, easeOut, k01, pop, typed } from "./ui";

// Card specs. Every card is 900 px wide and builds in over the scene; `events` lists the SFX cues (seconds from scene start).
export type CardSpec =
  | { type: "hero"; title: string; subtitle?: string; badge?: string; window?: string; phone?: { tag?: string; title: string; sub?: string }; stat?: { value: string; label: string }; checks?: string[] }
  | { type: "compare"; title: string; bad: { t: string; s?: string }[]; good: { t: string; s?: string; chip?: string }; stamp?: string }
  | { type: "chat"; title?: string; files?: { name: string; size?: string; kind?: string }[]; prompt: string; reply?: string; typeAt?: number }
  | { type: "terminal"; title?: string; cmd: string; logs: string[]; pills?: { t: string; s?: string }[] }
  | { type: "checklist"; title: string; icon?: "doc" | "spark" | "key" | "folder" | "play"; items: string[]; footer?: string }
  | { type: "download"; file: string; size?: string; folder?: string[]; button?: string }
  | { type: "price"; plan: string; price: string; newPrice: string; per?: string; features: string[]; button?: string }
  | { type: "steps"; title?: string; steps: { t: string; s?: string }[]; timer?: string }
  | { type: "cta"; keyword: string; handle: string; reply?: { title: string; files: string[] } }
  | { type: "big"; kicker?: string; big: string; sub?: string };
export type Cue = { at: number; sfx: "click" | "pop" | "ding" | "typing" | "whoosh"; dur?: number; vol?: number };
type P<T> = { th: Theme; u: number; dur: number; c: T };
const W = 900;
const label = (th: Theme): React.CSSProperties => ({ fontFamily: MONO, fontSize: 20, letterSpacing: 2, color: th.sub, textTransform: "uppercase" });
const appear = (u: number): React.CSSProperties => { const k = easeOut(k01(u, 0, 0.45)); return { opacity: k, transform: `scale(${0.94 + 0.06 * k})` }; };

// ------------------------------------------------------------------ hero: app window, phone preview, a stat with a drawing line, checks
const Hero: React.FC<P<Extract<CardSpec, { type: "hero" }>>> = ({ th, u, c }) => {
  const line = easeOut(k01(u, 0.9, 1.1));
  return (
    <div style={appear(u)}>
      <Panel th={th} w={W} h={720}>
        <WindowBar th={th} title={c.window ?? "studio — new-reel"} />
        <div style={{ display: "flex", alignItems: "center", padding: "26px 34px 10px", gap: 22, ...pop(u, 0.15) }}>
          <AppIcon th={th} />
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 38, color: th.ink }}>{c.title}</div>
            {c.subtitle ? <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 24, color: th.sub }}>{c.subtitle}</div> : null}
          </div>
          {c.badge ? <Chip bg={`${th.accent}18`} fg={th.accent} mono style={{ border: `2px solid ${th.accent}`, fontSize: 21 }}>{c.badge}</Chip> : null}
        </div>
        <div style={{ display: "flex", gap: 24, padding: "14px 34px" }}>
          {c.phone ? (
            <div style={{ width: 310, height: 470, borderRadius: 30, background: "#141a26", boxShadow: "0 18px 36px rgba(0,0,0,0.35)", padding: 24, boxSizing: "border-box", display: "flex", flexDirection: "column", alignItems: "center", ...pop(u, 0.35) }}>
              <Chip bg={th.accent} fg="#fff" mono style={{ alignSelf: "flex-start", fontSize: 16, padding: "4px 12px" }}>{c.phone.tag ?? "LIVE PREVIEW"}</Chip>
              <div style={{ marginTop: 50, fontFamily: SANS, fontWeight: 500, fontSize: 22, color: "#9aa3b2" }}>{c.subtitle ?? ""}</div>
              <div style={{ marginTop: 12, padding: "12px 24px", border: `3px solid ${th.accent}`, borderRadius: 14, fontFamily: SANS, fontWeight: 700, fontSize: 30, color: "#fff", letterSpacing: 1 }}>{c.phone.title}</div>
              {c.phone.sub ? <div style={{ marginTop: 12, fontFamily: SANS, fontWeight: 500, fontSize: 19, color: "#c8ceda" }}>{c.phone.sub}</div> : null}
              <div style={{ marginTop: 34, display: "flex", alignItems: "center", gap: 6, height: 60 }}>
                {Array.from({ length: 18 }, (_, i) => <div key={i} style={{ width: 6, borderRadius: 3, background: i < 18 * clamp(u / 4) ? th.accent : "#4a5466", height: 14 + 40 * Math.abs(Math.sin(i * 1.7 + u * 6)) * (0.4 + 0.6 * ((i * 7) % 5) / 5) }} />)}
              </div>
            </div>
          ) : null}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 22 }}>
            {c.stat ? (
              <div style={{ background: th.name === "dark" ? th.tint : "#fff", border: `1.5px solid ${th.border}`, borderRadius: 22, padding: "22px 26px", boxShadow: "0 10px 24px rgba(0,0,0,0.06)", ...pop(u, 0.55) }}>
                <div style={label(th)}>{c.stat.label}</div>
                <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 70, color: th.ink, lineHeight: 1.15 }}>{c.stat.value}</div>
                <svg width={480} height={70} viewBox="0 0 480 70"><path d="M5 62 C120 58, 220 48, 300 34 S430 10, 475 4" fill="none" stroke={th.green} strokeWidth={5} strokeLinecap="round" strokeDasharray={520} strokeDashoffset={520 * (1 - line)} /></svg>
              </div>
            ) : null}
            {c.checks ? (
              <div style={{ background: th.name === "dark" ? th.tint : "#fff", border: `1.5px solid ${th.border}`, borderRadius: 22, padding: "20px 26px", display: "flex", flexDirection: "column", gap: 16, boxShadow: "0 10px 24px rgba(0,0,0,0.06)", ...pop(u, 0.75) }}>
                {c.checks.map((t, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 16 }}>
                    <Check k={k01(u, 1.2 + i * 0.4, 0.4)} color={th.green} size={42} />
                    <span style={{ fontFamily: SANS, fontWeight: 600, fontSize: 27, color: th.ink }}>{t}</span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </Panel>
    </div>
  );
};
const heroEvents = (c: Extract<CardSpec, { type: "hero" }>): Cue[] => (c.checks ?? []).map((_, i) => ({ at: 1.25 + i * 0.4, sfx: "pop" as const, vol: 0.3 }));

// ------------------------------------------------------------------ compare: the old way struck out, the new way lands, a stamp
const Compare: React.FC<P<Extract<CardSpec, { type: "compare" }>>> = ({ th, u, c }) => {
  const goodAt = 0.7 + c.bad.length * 0.55;
  const stampK = k01(u, goodAt + 0.6, 0.3);
  return (
    <div style={appear(u)}>
      <Panel th={th} w={W} style={{ padding: "34px 34px 40px", boxSizing: "border-box" }}>
        <div style={{ textAlign: "center", fontFamily: SANS, fontWeight: 700, fontSize: 36, color: th.ink, marginBottom: 26 }}>{c.title}</div>
        {c.bad.map((r, i) => {
          const strike = easeOut(k01(u, 0.7 + i * 0.55, 0.35));
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, padding: "22px 24px", marginBottom: 18, borderRadius: 20, background: th.name === "dark" ? "rgba(239,74,74,0.10)" : "#fdf0ef", border: `1.5px solid ${th.red}33`, ...pop(u, 0.2 + i * 0.15) }}>
              <Cross color={th.red} size={46} />
              <div style={{ position: "relative" }}>
                <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 30, color: th.name === "dark" ? "#f0d0d0" : "#8a3a3a", opacity: 1 - 0.45 * strike }}>{r.t}</div>
                {r.s ? <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 21, color: th.sub }}>{r.s}</div> : null}
                <div style={{ position: "absolute", left: 0, top: 22, height: 4, borderRadius: 2, background: th.red, width: `${strike * 100}%` }} />
              </div>
            </div>
          );
        })}
        <div style={{ display: "flex", alignItems: "center", gap: 20, padding: "24px 24px", borderRadius: 22, background: th.name === "dark" ? `${th.accent}14` : "#fff7f2", border: `3px solid ${th.accent}`, boxShadow: `0 12px 28px ${th.accent}30`, ...pop(u, goodAt, 0.4, 30) }}>
          <AppIcon th={th} size={62} />
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 31, color: th.ink }}>{c.good.t}</div>
            {c.good.s ? <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 21, color: th.accent }}>{c.good.s}</div> : null}
          </div>
          <Chip bg={th.green} fg="#fff">{c.good.chip ?? "READY ✓"}</Chip>
        </div>
        {c.stamp ? (
          <div style={{ position: "absolute", right: 40, bottom: 14, transform: `rotate(-7deg) scale(${stampK > 0 ? 1.5 - 0.5 * back(stampK) : 0})`, opacity: clamp(stampK * 4),
            padding: "10px 28px", border: `4px solid ${th.red}`, borderRadius: 12, background: th.name === "dark" ? "#1a1010" : "#fff", fontFamily: SANS, fontWeight: 700, fontSize: 34, color: th.red, letterSpacing: 2, boxShadow: "0 10px 20px rgba(0,0,0,0.12)" }}>{c.stamp}</div>
        ) : null}
      </Panel>
    </div>
  );
};
const compareEvents = (c: Extract<CardSpec, { type: "compare" }>): Cue[] => {
  const goodAt = 0.7 + c.bad.length * 0.55;
  return [...c.bad.map((_, i) => ({ at: 0.75 + i * 0.55, sfx: "click" as const, vol: 0.35 })), { at: goodAt, sfx: "pop", vol: 0.35 }, ...(c.stamp ? [{ at: goodAt + 0.62, sfx: "click" as const, vol: 0.6 }] : [])];
};

// ------------------------------------------------------------------ chat: files dropped in, a prompt typed, sent, a reply
const chatT = (c: Extract<CardSpec, { type: "chat" }>) => { const nf = (c.files ?? []).length; const typeAt = c.typeAt ?? 0.5 + nf * 0.45 + 0.2; const done = typeAt + c.prompt.length / 17; return { typeAt, done, send: done + 0.45 }; };
const Chat: React.FC<P<Extract<CardSpec, { type: "chat" }>>> = ({ th, u, c }) => {
  const { typeAt, done, send } = chatT(c);
  const sent = u >= send;
  const keys: CursorKey[] = [{ t: done - 0.5, x: 520, y: 640 }, { t: send - 0.05, x: 800, y: 585, click: true }, { t: send + 0.8, x: 780, y: 610 }];
  return (
    <div style={appear(u)}>
      <Panel th={th} w={W} h={720}>
        <WindowBar th={th} title={c.title ?? "new chat"} />
        <div style={{ padding: "30px 34px", display: "flex", flexDirection: "column", gap: 18, alignItems: "flex-end" }}>
          {(c.files ?? []).map((f, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 18, padding: "16px 22px", borderRadius: 20, background: th.name === "dark" ? th.tint : "#f7f4f0", border: `1.5px solid ${th.border}`, width: 520, ...pop(u, 0.5 + i * 0.45, 0.35, 24) }}>
              <FileIcon color={i % 2 ? "#4a7ae0" : th.accent} label={f.kind ?? (f.name.split(".").pop() ?? "").toUpperCase()} />
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 27, color: th.ink }}>{f.name}</div>
                {f.size ? <div style={{ fontFamily: MONO, fontSize: 19, color: th.sub }}>{f.size}</div> : null}
              </div>
              <Check k={k01(u, 0.7 + i * 0.45, 0.3)} color={th.green} size={34} />
            </div>
          ))}
          {sent ? <div style={{ maxWidth: 640, padding: "20px 26px", borderRadius: "26px 26px 6px 26px", background: `linear-gradient(140deg, ${th.accent}, ${th.accent2})`, color: "#fff", fontFamily: SANS, fontWeight: 600, fontSize: 28, ...pop(u, send, 0.3) }}>{c.prompt}</div> : null}
          {sent && c.reply ? (
            <div style={{ alignSelf: "flex-start", display: "flex", alignItems: "center", gap: 14, padding: "18px 24px", borderRadius: "26px 26px 26px 6px", background: th.name === "dark" ? th.tint : "#f2efea", ...pop(u, send + 0.6, 0.3) }}>
              <AppIcon th={th} size={40} />
              <span style={{ fontFamily: SANS, fontWeight: 500, fontSize: 26, color: th.ink }}>{c.reply}{".".repeat(1 + (Math.floor(u * 3) % 3))}</span>
            </div>
          ) : null}
        </div>
        <div style={{ position: "absolute", left: 34, right: 34, bottom: 34, height: 96, borderRadius: 24, border: `2.5px solid ${u > typeAt && !sent ? th.accent : th.border}`, background: th.name === "dark" ? "rgba(255,255,255,0.04)" : "#fff",
          display: "flex", alignItems: "center", padding: "0 18px 0 28px", gap: 14 }}>
          <div style={{ flex: 1, fontFamily: SANS, fontWeight: 500, fontSize: 28, color: sent ? th.sub : th.ink, whiteSpace: "nowrap", overflow: "hidden" }}>
            {sent ? "Message…" : u > typeAt ? typed(c.prompt, u, typeAt, 17) + caret(u) : "Message…"}
          </div>
          <div style={{ width: 62, height: 62, borderRadius: 18, background: u >= done ? th.accent : th.border, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width={30} height={30} viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6" stroke="#fff" strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </div>
        </div>
        <Cursor th={th} u={u} keys={keys} />
      </Panel>
    </div>
  );
};
const chatEvents = (c: Extract<CardSpec, { type: "chat" }>): Cue[] => { const { typeAt, done, send } = chatT(c);
  return [...(c.files ?? []).map((_, i) => ({ at: 0.5 + i * 0.45, sfx: "pop" as const, vol: 0.3 })), { at: typeAt, sfx: "typing", dur: done - typeAt, vol: 0.22 }, { at: send - 0.05, sfx: "click", vol: 0.5 }]; };

// ------------------------------------------------------------------ terminal: a command typed, log lines tick, pills slide in
const termT = (c: Extract<CardSpec, { type: "terminal" }>) => { const typeAt = 0.5; const done = typeAt + c.cmd.length / 16; return { typeAt, done, log0: done + 0.35 }; };
const Terminal: React.FC<P<Extract<CardSpec, { type: "terminal" }>>> = ({ th, u, c }) => {
  const { typeAt, done, log0 } = termT(c);
  const pillsAt = log0 + c.logs.length * 0.42 + 0.2;
  return (
    <div style={appear(u)}>
      <Panel th={th} w={W} dark style={{ boxShadow: "0 34px 70px rgba(0,0,0,0.4)" }}>
        <WindowBar th={th} title={c.title ?? "terminal"} dark />
        <div style={{ padding: "28px 34px 34px", fontFamily: MONO, fontSize: 28, color: "#d6dbe6", minHeight: 300 }}>
          <div style={{ display: "flex", alignItems: "center", padding: "16px 20px", borderRadius: 14, border: `2.5px solid ${u >= done ? th.green : th.accent}`, background: "rgba(255,255,255,0.03)" }}>
            <span style={{ color: th.accent, marginRight: 14 }}>&gt;</span>
            <span style={{ flex: 1 }}>{typed(c.cmd, u, typeAt, 16)}{u < done + 0.3 ? caret(u) : ""}</span>
            {u >= done ? <Check k={k01(u, done, 0.3)} color={th.green} size={36} /> : null}
          </div>
          <div style={{ marginTop: 22, display: "flex", flexDirection: "column", gap: 12 }}>
            {c.logs.map((l, i) => (
              <div key={i} style={{ fontSize: 24, color: i === c.logs.length - 1 ? th.green : "#aab2c2", ...pop(u, log0 + i * 0.42, 0.25, 8) }}>{i === c.logs.length - 1 ? "✓ " : "• "}{l}</div>
            ))}
          </div>
        </div>
      </Panel>
      {(c.pills ?? []).map((p, i) => (
        <div key={i} style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 16, padding: "18px 24px", borderRadius: 20, background: th.name === "dark" ? "#1c1f24" : "#fff", border: `1.5px solid ${th.border}`, boxShadow: th.shadow, ...pop(u, pillsAt + i * 0.4, 0.3, 26) }}>
          <Check k={k01(u, pillsAt + i * 0.4 + 0.1, 0.3)} color={th.green} size={40} />
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 27, color: th.ink }}>{p.t}</div>
            {p.s ? <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 20, color: th.sub }}>{p.s}</div> : null}
          </div>
          <Chip bg={`${th.green}22`} fg={th.green} style={{ fontSize: 17 }}>INSTALLED</Chip>
        </div>
      ))}
    </div>
  );
};
const termEvents = (c: Extract<CardSpec, { type: "terminal" }>): Cue[] => { const { typeAt, done, log0 } = termT(c); const pillsAt = log0 + c.logs.length * 0.42 + 0.2;
  return [{ at: typeAt, sfx: "typing", dur: done - typeAt, vol: 0.22 }, { at: done, sfx: "click", vol: 0.4 }, ...(c.pills ?? []).map((_, i) => ({ at: pillsAt + i * 0.4, sfx: "pop" as const, vol: 0.3 }))]; };

// ------------------------------------------------------------------ checklist: a document whose rows tick one by one across the scene
const Checklist: React.FC<P<Extract<CardSpec, { type: "checklist" }>>> = ({ th, u, dur, c }) => {
  const step = Math.min(0.75, (dur - 1.2) / Math.max(1, c.items.length));
  return (
    <div style={appear(u)}>
      <Panel th={th} w={W} style={{ padding: "32px 34px", boxSizing: "border-box" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 26, ...pop(u, 0.1) }}>
          <AppIcon th={th} glyph={c.icon ?? "doc"} size={66} />
          <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 34, color: th.ink }}>{c.title}</div>
        </div>
        {c.items.map((t, i) => {
          const at = 0.6 + i * step;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 18, padding: "18px 20px", marginBottom: 12, borderRadius: 18, background: u >= at ? (th.name === "dark" ? `${th.green}12` : "#f1faf3") : th.name === "dark" ? th.tint : "#f8f6f3", ...pop(u, 0.25 + i * 0.08) }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: th.name === "dark" ? "rgba(255,255,255,0.08)" : "#ece8e2", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontWeight: 700, fontSize: 21, color: th.sub }}>{String(i + 1).padStart(2, "0")}</div>
              <span style={{ flex: 1, fontFamily: SANS, fontWeight: 600, fontSize: 28, color: th.ink }}>{t}</span>
              <Check k={k01(u, at, 0.35)} color={th.green} size={40} />
            </div>
          );
        })}
        {c.footer ? <div style={{ marginTop: 14, textAlign: "center", ...pop(u, 0.6 + c.items.length * step) }}><Chip bg={`${th.green}20`} fg={th.green} style={{ fontSize: 22 }}>{c.footer}</Chip></div> : null}
      </Panel>
    </div>
  );
};
const checklistEvents = (c: Extract<CardSpec, { type: "checklist" }>, dur: number): Cue[] => { const step = Math.min(0.75, (dur - 1.2) / Math.max(1, c.items.length)); return c.items.map((_, i) => ({ at: 0.6 + i * step, sfx: "pop" as const, vol: 0.3 })); };

// ------------------------------------------------------------------ download: a progress bar fills, the button turns green, the folder opens
const Download: React.FC<P<Extract<CardSpec, { type: "download" }>>> = ({ th, u, c }) => {
  const prog = ease(k01(u, 0.5, 1.4));
  const done = u > 2.0;
  const keys: CursorKey[] = [{ t: 0.1, x: 600, y: 330 }, { t: 0.45, x: 760, y: 130, click: true }, { t: 2.1, x: 720, y: 200 }];
  return (
    <div style={appear(u)}>
      <Panel th={th} w={W} style={{ padding: "30px 34px", boxSizing: "border-box" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <FileIcon color={th.accent} label="MP4" size={70} />
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 31, color: th.ink }}>{c.file}</div>
            <div style={{ fontFamily: MONO, fontSize: 20, color: th.sub }}>{done ? "complete" : `${Math.round(prog * 100)}%`}{c.size ? ` · ${c.size}` : ""}</div>
          </div>
          <div style={{ padding: "14px 26px", borderRadius: 16, background: done ? th.green : th.accent, color: "#fff", fontFamily: SANS, fontWeight: 700, fontSize: 24 }}>{done ? "Ready ✓" : c.button ?? "Render"}</div>
        </div>
        <div style={{ marginTop: 22, height: 14, borderRadius: 7, background: th.name === "dark" ? "rgba(255,255,255,0.08)" : "#ece8e2", overflow: "hidden" }}>
          <div style={{ width: `${prog * 100}%`, height: "100%", borderRadius: 7, background: done ? th.green : th.accent }} />
        </div>
        <Cursor th={th} u={u} keys={keys} />
      </Panel>
      {c.folder ? (
        <Panel th={th} w={W} style={{ marginTop: 22, padding: "26px 30px", boxSizing: "border-box", ...pop(u, 2.2, 0.4, 30) }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 18 }}>
            <AppIcon th={th} glyph="folder" size={52} />
            <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 28, color: th.ink }}>{c.file.replace(/\.[a-z0-9]+$/i, "")}/</span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 14 }}>
            {c.folder.map((f, i) => (
              <div key={i} style={{ width: 405, display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderRadius: 14, background: th.name === "dark" ? th.tint : "#f8f6f3", ...pop(u, 2.5 + i * 0.18, 0.25, 10) }}>
                <Check k={k01(u, 2.6 + i * 0.18, 0.3)} color={th.green} size={30} />
                <span style={{ fontFamily: MONO, fontSize: 22, color: th.ink }}>{f}</span>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}
    </div>
  );
};
const downloadEvents = (c: Extract<CardSpec, { type: "download" }>): Cue[] => [{ at: 0.45, sfx: "click", vol: 0.5 }, { at: 2.0, sfx: "ding", vol: 0.3 }, ...(c.folder ? [{ at: 2.2, sfx: "pop" as const, vol: 0.3 }] : [])];

// ------------------------------------------------------------------ price: the old price is struck through and the new one lands
const Price: React.FC<P<Extract<CardSpec, { type: "price" }>>> = ({ th, u, c }) => {
  const strike = easeOut(k01(u, 1.0, 0.35));
  const k = k01(u, 1.35, 0.35);
  const keys: CursorKey[] = [{ t: 0.3, x: 640, y: 420 }, { t: 0.95, x: 330, y: 230, click: true }, { t: 1.8, x: 420, y: 300 }];
  return (
    <div style={appear(u)}>
      <Panel th={th} w={W} style={{ padding: "34px 40px", boxSizing: "border-box" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 34, color: th.ink }}>{c.plan}</span>
          <Chip bg={`${th.accent}22`} fg={th.accent} mono style={{ fontSize: 18 }}>MOST POPULAR</Chip>
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 26, margin: "26px 0 20px" }}>
          <div style={{ position: "relative", fontFamily: SANS, fontWeight: 700, fontSize: 118, color: strike > 0.5 ? th.sub : th.ink, lineHeight: 1 }}>
            {c.price}
            <div style={{ position: "absolute", left: -8, top: "52%", height: 9, borderRadius: 5, background: th.red, width: `calc(${strike * 100}% + 16px)`, transform: "rotate(-6deg)" }} />
          </div>
          {c.per ? <span style={{ fontFamily: SANS, fontWeight: 500, fontSize: 30, color: th.sub }}>{c.per}</span> : null}
          <div style={{ marginLeft: "auto", fontFamily: SANS, fontWeight: 700, fontSize: 96, color: th.green, transform: `scale(${k > 0 ? 0.6 + 0.4 * back(k) : 0})`, opacity: clamp(k * 3) }}>{c.newPrice}</div>
        </div>
        {c.features.map((f, i) => <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, margin: "12px 0", fontFamily: SANS, fontWeight: 500, fontSize: 27, color: th.ink, ...pop(u, 0.3 + i * 0.12) }}><span style={{ color: th.green, fontWeight: 700 }}>✓</span>{f}</div>)}
        {c.button ? <div style={{ marginTop: 22, padding: "20px", textAlign: "center", borderRadius: 18, background: k > 0.5 ? th.green : th.accent, color: "#fff", fontFamily: SANS, fontWeight: 700, fontSize: 28 }}>{c.button}</div> : null}
        <Cursor th={th} u={u} keys={keys} />
      </Panel>
    </div>
  );
};
const priceEvents = (): Cue[] => [{ at: 0.95, sfx: "click", vol: 0.5 }, { at: 1.35, sfx: "pop", vol: 0.45 }];

// ------------------------------------------------------------------ steps: numbered rows light up in turn, with an optional timer ring
const Steps: React.FC<P<Extract<CardSpec, { type: "steps" }>>> = ({ th, u, dur, c }) => {
  const step = Math.min(0.9, (dur - 1.0) / Math.max(1, c.steps.length));
  return (
    <div style={appear(u)}>
      <Panel th={th} w={W} style={{ padding: "32px 34px", boxSizing: "border-box" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 22 }}>
          <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 32, color: th.ink }}>{c.title ?? `Sirf ${c.steps.length} steps`}</span>
          {c.timer ? (
            <div style={{ position: "relative", width: 130, height: 130 }}>
              <svg width={130} height={130} viewBox="0 0 130 130"><circle cx={65} cy={65} r={56} stroke={th.name === "dark" ? "#333" : "#eee"} strokeWidth={9} fill="none" />
                <circle cx={65} cy={65} r={56} stroke={th.red} strokeWidth={9} fill="none" strokeLinecap="round" strokeDasharray={352} strokeDashoffset={352 * clamp(u / dur)} transform="rotate(-90 65 65)" /></svg>
              <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontWeight: 700, fontSize: 32, color: th.ink }}>{c.timer}</div>
            </div>
          ) : null}
        </div>
        {c.steps.map((s, i) => {
          const on = u >= 0.5 + i * step;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, padding: "20px 22px", marginBottom: 14, borderRadius: 20, border: `2.5px solid ${on ? th.accent : th.border}`, background: on ? (th.name === "dark" ? `${th.accent}12` : "#fff7f2") : "transparent", ...pop(u, 0.2 + i * 0.1) }}>
              <div style={{ width: 54, height: 54, borderRadius: 27, background: on ? th.accent : th.border, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: SANS, fontWeight: 700, fontSize: 26 }}>{i + 1}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 29, color: th.ink }}>{s.t}</div>
                {s.s ? <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 21, color: th.sub }}>{s.s}</div> : null}
              </div>
            </div>
          );
        })}
      </Panel>
    </div>
  );
};
const stepsEvents = (c: Extract<CardSpec, { type: "steps" }>, dur: number): Cue[] => { const step = Math.min(0.9, (dur - 1.0) / Math.max(1, c.steps.length)); return c.steps.map((_, i) => ({ at: 0.5 + i * step, sfx: "pop" as const, vol: 0.3 })); };

// ------------------------------------------------------------------ cta: the keyword button, a comment box typing it, the auto-reply card
const ctaT = (c: Extract<CardSpec, { type: "cta" }>) => { const typeAt = 0.9; const done = typeAt + c.keyword.length / 6; return { typeAt, done, post: done + 0.35 }; };
const Cta: React.FC<P<Extract<CardSpec, { type: "cta" }>>> = ({ th, u, c }) => {
  const { typeAt, done, post } = ctaT(c);
  const btn = k01(u, 0.1, 0.45);
  const posted = u >= post;
  const keys: CursorKey[] = [{ t: done - 0.4, x: 520, y: 470 }, { t: post - 0.05, x: 790, y: 410, click: true }, { t: post + 0.9, x: 760, y: 470 }];
  return (
    <div style={{ width: W, display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
      <div style={{ padding: "26px 90px", borderRadius: 26, background: `linear-gradient(150deg, ${th.accent}, ${th.accent2})`, color: "#fff", fontFamily: SANS, fontWeight: 700, fontSize: 96, letterSpacing: 4,
        boxShadow: `0 24px 50px ${th.accent}55`, transform: `scale(${0.5 + 0.5 * back(btn)})`, opacity: clamp(btn * 3) }}>{c.keyword}</div>
      <div style={{ ...pop(u, 0.3), fontFamily: MONO, fontSize: 22, letterSpacing: 4, color: th.sub, margin: "18px 0 26px" }}>COMMENT NOW</div>
      <Panel th={th} w={W} style={{ padding: "24px 26px", boxSizing: "border-box", ...pop(u, 0.5, 0.35, 20) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ width: 62, height: 62, borderRadius: 31, background: `conic-gradient(${th.accent}, ${th.accent2}, ${th.accent})`, padding: 4, boxSizing: "border-box" }}><div style={{ width: "100%", height: "100%", borderRadius: "50%", background: th.name === "dark" ? "#222" : "#f2efea" }} /></div>
          <div style={{ flex: 1, height: 70, borderRadius: 35, border: `2.5px solid ${u > typeAt && !posted ? th.accent : th.border}`, display: "flex", alignItems: "center", padding: "0 28px", fontFamily: SANS, fontWeight: 600, fontSize: 30, color: th.ink }}>
            {posted ? <span style={{ color: th.sub }}>Add a comment…</span> : u > typeAt ? typed(c.keyword, u, typeAt, 6) + caret(u) : <span style={{ color: th.sub }}>Add a comment…</span>}
          </div>
          <div style={{ padding: "14px 24px", borderRadius: 16, background: posted ? th.green : u >= done ? th.accent : th.border, color: "#fff", fontFamily: SANS, fontWeight: 700, fontSize: 24 }}>{posted ? "Sent ✓" : "Post"}</div>
        </div>
        {posted ? (
          <div style={{ marginTop: 20, display: "flex", gap: 16, alignItems: "flex-start", padding: "18px 20px", borderRadius: 20, background: th.name === "dark" ? th.tint : "#f8f6f3", ...pop(u, post + 0.4, 0.35, 16) }}>
            <AppIcon th={th} size={52} />
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 25, color: th.ink }}>{c.handle} <span style={{ fontWeight: 500, color: th.sub, fontSize: 21 }}>· sent you a message</span></div>
              {c.reply ? <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 23, color: th.sub, margin: "4px 0 10px" }}>{c.reply.title}</div> : null}
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>{(c.reply?.files ?? []).map((f, i) => <Chip key={i} bg={th.name === "dark" ? "rgba(255,255,255,0.08)" : "#fff"} fg={th.ink} style={{ border: `1.5px solid ${th.border}`, fontWeight: 600, fontSize: 19, ...pop(u, post + 0.7 + i * 0.2, 0.3, 8) }}><FileIcon color={i % 2 ? "#4a7ae0" : th.accent} size={26} />{f}</Chip>)}</div>
            </div>
          </div>
        ) : null}
        <Cursor th={th} u={u} keys={keys} />
      </Panel>
    </div>
  );
};
const ctaEvents = (c: Extract<CardSpec, { type: "cta" }>): Cue[] => { const { typeAt, done, post } = ctaT(c); return [{ at: 0.12, sfx: "pop", vol: 0.45 }, { at: typeAt, sfx: "typing", dur: done - typeAt, vol: 0.22 }, { at: post - 0.05, sfx: "click", vol: 0.5 }, { at: post + 0.4, sfx: "ding", vol: 0.35 }]; };

// ------------------------------------------------------------------ big: one huge statement
const Big: React.FC<P<Extract<CardSpec, { type: "big" }>>> = ({ th, u, c }) => {
  const k = k01(u, 0.15, 0.4);
  return (
    <div style={{ width: W, textAlign: "center" }}>
      {c.kicker ? <div style={{ ...pop(u, 0), fontFamily: MONO, fontSize: 26, letterSpacing: 5, color: th.sub }}>{c.kicker}</div> : null}
      <div style={{ fontFamily: SERIF, fontStyle: "italic", fontWeight: 900, fontSize: 230, lineHeight: 1.05, background: `linear-gradient(170deg, ${th.accent}, ${th.accent2})`, WebkitBackgroundClip: "text", color: "transparent", transform: `scale(${0.6 + 0.4 * back(k)})`, opacity: clamp(k * 3) }}>{c.big}</div>
      {c.sub ? <div style={{ ...pop(u, 0.5), fontFamily: SANS, fontWeight: 600, fontSize: 40, color: th.ink }}>{c.sub}</div> : null}
    </div>
  );
};

export const CardView: React.FC<{ th: Theme; u: number; dur: number; c: CardSpec }> = ({ th, u, dur, c }) => {
  switch (c.type) {
    case "hero": return <Hero th={th} u={u} dur={dur} c={c} />;
    case "compare": return <Compare th={th} u={u} dur={dur} c={c} />;
    case "chat": return <Chat th={th} u={u} dur={dur} c={c} />;
    case "terminal": return <Terminal th={th} u={u} dur={dur} c={c} />;
    case "checklist": return <Checklist th={th} u={u} dur={dur} c={c} />;
    case "download": return <Download th={th} u={u} dur={dur} c={c} />;
    case "price": return <Price th={th} u={u} dur={dur} c={c} />;
    case "steps": return <Steps th={th} u={u} dur={dur} c={c} />;
    case "cta": return <Cta th={th} u={u} dur={dur} c={c} />;
    case "big": return <Big th={th} u={u} dur={dur} c={c} />;
  }
};
export const cardEvents = (c: CardSpec, dur: number): Cue[] => {
  switch (c.type) {
    case "hero": return heroEvents(c);
    case "compare": return compareEvents(c);
    case "chat": return chatEvents(c);
    case "terminal": return termEvents(c);
    case "checklist": return checklistEvents(c, dur);
    case "download": return downloadEvents(c);
    case "price": return priceEvents();
    case "steps": return stepsEvents(c, dur);
    case "cta": return ctaEvents(c);
    case "big": return [{ at: 0.15, sfx: "pop", vol: 0.45 }];
  }
};
