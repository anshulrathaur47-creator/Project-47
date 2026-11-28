import React from "react";
import { continueRender, delayRender, staticFile } from "remotion";

// ------------------------------------------------------------------ theme
export type ThemeName = "cream" | "dark";
export type Theme = {
  name: ThemeName; bg: string; ink: string; sub: string; card: string; border: string; shadow: string; tint: string;
  accent: string; accent2: string; green: string; red: string; glow: string; handleInk: string; cursor: string; cursorEdge: string;
};
export const THEMES: Record<ThemeName, Theme> = {
  cream: {
    name: "cream", bg: "#f0ede7", ink: "#1d2433", sub: "#727782", card: "#ffffff", border: "rgba(20,20,30,0.07)",
    shadow: "0 34px 70px rgba(60,40,20,0.16), 0 8px 18px rgba(60,40,20,0.08)", tint: "#f6f2ec",
    accent: "#e05a28", accent2: "#c23a18", green: "#2fb456", red: "#e04848", glow: "#e05a28", handleInk: "rgba(30,36,51,0.38)", cursor: "#1d2433", cursorEdge: "#ffffff",
  },
  dark: {
    name: "dark", bg: "#040404", ink: "#f2f2f2", sub: "#9aa0a8", card: "rgba(30,32,35,0.9)", border: "rgba(255,255,255,0.09)",
    shadow: "0 34px 80px rgba(0,0,0,0.7)", tint: "rgba(255,255,255,0.05)",
    accent: "#f2bc26", accent2: "#e2362e", green: "#34d26a", red: "#ef4a4a", glow: "#19e619", handleInk: "rgba(255,255,255,0.38)", cursor: "#ffffff", cursorEdge: "#111111",
  },
};
export const withAccent = (t: Theme, accent?: string, accent2?: string): Theme => (accent ? { ...t, accent, accent2: accent2 ?? t.accent2 } : t);

// ------------------------------------------------------------------ fonts
export const SANS = "'UIPoppins', sans-serif";
export const SERIF = "'UIPlayfair', serif";
export const MONO = "'UIMono', monospace";
const FACES = `
@font-face { font-family: 'UIPoppins'; font-weight: 500; src: url('${staticFile("fonts/Poppins-Medium.ttf")}'); }
@font-face { font-family: 'UIPoppins'; font-weight: 600; src: url('${staticFile("fonts/Poppins-SemiBold.ttf")}'); }
@font-face { font-family: 'UIPoppins'; font-weight: 700; src: url('${staticFile("fonts/Poppins-Bold.ttf")}'); }
@font-face { font-family: 'UIPlayfair'; font-style: italic; font-weight: 400 900; src: url('${staticFile("fonts/PlayfairDisplay-Italic-VF.ttf")}'); }
@font-face { font-family: 'UIMono'; font-weight: 100 800; src: url('${staticFile("fonts/JetBrainsMono-VF.ttf")}'); }
`;
let fontsReady: Promise<unknown> | null = null;
export const Fonts: React.FC = () => {
  const [handle] = React.useState(() => delayRender("fonts"));
  React.useEffect(() => {
    if (!fontsReady) fontsReady = Promise.all([
      document.fonts.load("500 40px UIPoppins"), document.fonts.load("600 40px UIPoppins"), document.fonts.load("700 40px UIPoppins"),
      document.fonts.load("italic 900 40px UIPlayfair"), document.fonts.load("500 40px UIMono"),
    ]);
    fontsReady.then(() => continueRender(handle), () => continueRender(handle));
  }, [handle]);
  return <style>{FACES}</style>;
};

// ------------------------------------------------------------------ easing
export const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
export const ease = (x: number) => { const t = clamp(x); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
export const easeOut = (x: number) => 1 - Math.pow(1 - clamp(x), 3);
export const back = (x: number) => { const t = clamp(x); const c = 1.7; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
export const k01 = (u: number, a: number, d = 0.35) => clamp((u - a) / d);
/** fade + rise for a build-in item */
export const pop = (u: number, at: number, d = 0.35, rise = 14): React.CSSProperties => {
  const k = easeOut(k01(u, at, d));
  return { opacity: k, transform: `translateY(${(1 - k) * rise}px)`, filter: k < 1 ? `blur(${(1 - k) * 6}px)` : undefined };
};

// ------------------------------------------------------------------ primitives
export const Panel: React.FC<{ th: Theme; w: number; h?: number; style?: React.CSSProperties; children?: React.ReactNode; dark?: boolean; radius?: number }> = ({ th, w, h, style, children, dark, radius = 30 }) => (
  <div style={{ width: w, height: h, borderRadius: radius, background: dark ? "#141821" : th.card, border: `1.5px solid ${dark ? "rgba(255,255,255,0.08)" : th.border}`,
    boxShadow: th.shadow, backdropFilter: th.name === "dark" ? "blur(14px)" : undefined, overflow: "hidden", position: "relative", ...style }}>{children}</div>
);
export const WindowBar: React.FC<{ th: Theme; title: string; dark?: boolean }> = ({ th, title, dark }) => (
  <div style={{ height: 64, display: "flex", alignItems: "center", padding: "0 26px", borderBottom: `1.5px solid ${dark || th.name === "dark" ? "rgba(255,255,255,0.07)" : "rgba(20,20,30,0.06)"}`,
    background: dark ? "#0f131a" : th.name === "dark" ? "rgba(255,255,255,0.03)" : "#f8f6f3", position: "relative" }}>
    {["#ff5f57", "#febc2e", "#28c840"].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c, marginRight: 10 }} />)}
    <div style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", padding: "6px 22px", borderRadius: 20, fontFamily: MONO, fontSize: 21, letterSpacing: 0.5,
      color: dark || th.name === "dark" ? "#9aa3b2" : "#6f7480", background: dark || th.name === "dark" ? "rgba(255,255,255,0.06)" : "#ffffff", border: `1.5px solid ${dark || th.name === "dark" ? "rgba(255,255,255,0.06)" : "rgba(20,20,30,0.08)"}` }}>{title}</div>
  </div>
);
export const Chip: React.FC<{ bg: string; fg: string; children: React.ReactNode; style?: React.CSSProperties; mono?: boolean }> = ({ bg, fg, children, style, mono }) => (
  <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 16px", borderRadius: 999, background: bg, color: fg, fontFamily: mono ? MONO : SANS, fontWeight: 700, fontSize: 20, letterSpacing: 0.6, ...style }}>{children}</div>
);
export const Check: React.FC<{ k: number; color: string; size?: number }> = ({ k, color, size = 40 }) => (
  <div style={{ width: size, height: size, borderRadius: size / 2, background: color, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${0.4 + 0.6 * back(k)})`, opacity: clamp(k * 3), flexShrink: 0 }}>
    <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5" fill="none" stroke="#fff" strokeWidth={3.4} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={30} strokeDashoffset={30 * (1 - clamp(k * 1.6 - 0.3))} /></svg>
  </div>
);
export const Cross: React.FC<{ color: string; size?: number }> = ({ color, size = 40 }) => (
  <div style={{ width: size, height: size, borderRadius: size / 2, background: color, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
    <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" stroke="#fff" strokeWidth={3.4} strokeLinecap="round" /></svg>
  </div>
);
/** generic app glyph (no third-party logos): a rounded square with a play mark */
export const AppIcon: React.FC<{ th: Theme; size?: number; glyph?: "play" | "spark" | "doc" | "key" | "folder" }> = ({ th, size = 74, glyph = "spark" }) => (
  <div style={{ width: size, height: size, borderRadius: size * 0.26, background: `linear-gradient(145deg, ${th.accent}, ${th.accent2})`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 8px 20px ${th.accent}55`, flexShrink: 0 }}>
    <svg width={size * 0.52} height={size * 0.52} viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
      {glyph === "play" ? <path d="M8 5.5v13l10.5-6.5z" fill="#fff" /> : null}
      {glyph === "spark" ? <path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3" /> : null}
      {glyph === "doc" ? <><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4M10 12h5M10 16h5" /></> : null}
      {glyph === "key" ? <><circle cx="8" cy="15" r="4" /><path d="M11 12l8-8M16 7l2 2" /></> : null}
      {glyph === "folder" ? <path d="M3 7h6l2 2h10v10H3z" /> : null}
    </svg>
  </div>
);
export const FileIcon: React.FC<{ color: string; label?: string; size?: number }> = ({ color, label = "", size = 52 }) => (
  <div style={{ width: size * 0.82, height: size, borderRadius: 8, background: color, position: "relative", flexShrink: 0, display: "flex", alignItems: "flex-end", justifyContent: "center", paddingBottom: 6, boxSizing: "border-box" }}>
    <div style={{ position: "absolute", right: 0, top: 0, width: size * 0.28, height: size * 0.28, background: "rgba(255,255,255,0.45)", borderBottomLeftRadius: 6 }} />
    <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: size * 0.22, color: "#fff" }}>{label}</span>
  </div>
);

// ------------------------------------------------------------------ cursor (card-local coordinates)
export type CursorKey = { t: number; x: number; y: number; click?: boolean };
export const Cursor: React.FC<{ th: Theme; u: number; keys: CursorKey[] }> = ({ th, u, keys }) => {
  if (!keys.length || u < keys[0].t - 0.3) return null;
  let x = keys[0].x, y = keys[0].y, ring = -1;
  for (let i = 0; i < keys.length; i++) {
    const a = keys[i], b = keys[i + 1];
    if (a.click && u >= a.t && u < a.t + 0.45) ring = (u - a.t) / 0.45;
    if (!b) { if (u >= a.t) { x = a.x; y = a.y; } break; }
    if (u >= a.t && u < b.t) { const k = ease((u - a.t) / (b.t - a.t)); x = a.x + (b.x - a.x) * k; y = a.y + (b.y - a.y) * k; break; }
  }
  const press = ring >= 0 && ring < 0.3 ? 0.86 : 1;
  const fadeIn = clamp((u - keys[0].t + 0.3) / 0.3);
  return (
    <div style={{ position: "absolute", left: x, top: y, pointerEvents: "none", zIndex: 50, opacity: fadeIn }}>
      {ring >= 0 ? <div style={{ position: "absolute", left: -30 * (0.4 + ring), top: -30 * (0.4 + ring), width: 60 * (0.4 + ring), height: 60 * (0.4 + ring), borderRadius: "50%", border: `4px solid ${th.accent}`, opacity: 1 - ring }} /> : null}
      <svg width={46} height={56} viewBox="0 0 23 28" style={{ transform: `scale(${press})`, transformOrigin: "0 0", filter: "drop-shadow(0 4px 6px rgba(0,0,0,0.3))" }}>
        <path d="M1.5 1.5v21l5.6-5.2 3.8 8.4 3.6-1.6-3.8-8.2 7.8-.4z" fill={th.cursor} stroke={th.cursorEdge} strokeWidth={1.6} strokeLinejoin="round" />
      </svg>
    </div>
  );
};

/** text typed character by character from time `at` */
export const typed = (text: string, u: number, at: number, cps = 16) => text.slice(0, Math.max(0, Math.floor((u - at) * cps)));
export const caret = (u: number) => (Math.floor(u * 2.2) % 2 === 0 ? "|" : " ");
