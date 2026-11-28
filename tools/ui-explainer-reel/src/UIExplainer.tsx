import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame } from "remotion";
import { CardSpec, CardView, Cue, cardEvents } from "./cards";
import { Fonts, MONO, SANS, SERIF, THEMES, Theme, ThemeName, clamp, ease, easeOut, withAccent } from "./ui";

// "ui-explainer" reel engine: a voice-over over animated UI cards, word-by-word Hinglish captions with boxed serif key words,
// and a dashed-arrow camera move between cards (no hard cuts). Everything is driven by the spec passed as input props.
export type Word = { t: string; s: number; e: number; k?: boolean };
export type Phrase = { zone: "top" | "bottom"; words: Word[] };
export type Scene = { start: number; tag?: string; card: CardSpec };
export type Spec = {
  theme: ThemeName; accent?: string; accent2?: string; handle: string; duration: number;
  vo?: string; music?: number; terms?: string; phrases: Phrase[]; scenes: Scene[];
};

const FPS = 30;
const CX = 540, CY = 1000;           // where the active card sits on screen
const STEP_X = 1900;                 // world distance between cards
const TOP_ZONE_BOTTOM = 540, BOTTOM_ZONE_TOP = 1405;
const MOVE = 0.55;                   // camera move length (s), ending 0.12 s after the new scene starts
const worldPos = (k: number): [number, number] => [k * STEP_X, k === 0 ? 0 : k % 2 ? -300 : 200];

// ------------------------------------------------------------------ background
const Flower: React.FC<{ x: number; y: number; r: number; color: string; rot: number; blur: number }> = ({ x, y, r, color, rot, blur }) => (
  <svg width={r * 2} height={r * 2} viewBox="-100 -100 200 200" style={{ position: "absolute", left: x - r, top: y - r, filter: `blur(${blur}px)`, transform: `rotate(${rot}deg)` }}>
    {Array.from({ length: 10 }, (_, i) => <ellipse key={i} cx={0} cy={-52} rx={9} ry={46} fill={color} opacity={0.7} transform={`rotate(${i * 36})`} />)}
    <circle r={20} fill={color} />
  </svg>
);
const Background: React.FC<{ th: Theme; camX: number; camY: number }> = ({ th, camX, camY }) => {
  if (th.name === "dark") return (
    <AbsoluteFill style={{ background: th.bg }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 85% 42% at ${50 + Math.sin(camX / 2600) * 6}% 102%, ${th.glow}f0 0%, ${th.glow}55 38%, rgba(0,0,0,0) 72%)` }} />
    </AbsoluteFill>
  );
  const px = -camX * 0.05, py = -camY * 0.05;
  return (
    <AbsoluteFill style={{ background: th.bg }}>
      <Flower x={1000 + (px % 400)} y={110 + py} r={240} color={th.accent} rot={camX * 0.004} blur={11} />
      <Flower x={40 + ((px * 0.7) % 300)} y={1760 + py} r={260} color={th.accent} rot={20 - camX * 0.003} blur={12} />
      <Flower x={1110 + ((px * 1.2) % 500)} y={1180 + py * 0.6} r={150} color={th.accent} rot={8} blur={14} />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ captions
const KeyWord: React.FC<{ th: Theme; w: Word; t: number }> = ({ th, w, t }) => {
  const k = easeOut((t - (w.s - 0.04)) / 0.2);
  const box = clamp((t - (w.s + 0.12)) / 0.16);
  const hs = 14;
  const handle = (pos: React.CSSProperties) => <div style={{ position: "absolute", width: hs, height: hs, background: th.name === "dark" ? "#000" : th.bg, border: `3px solid ${th.accent}`, ...pos }} />;
  return (
    <span style={{ position: "relative", display: "inline-block", padding: "0 16px", opacity: clamp(k), filter: k < 1 ? `blur(${(1 - clamp(k)) * 8}px)` : undefined, transform: `translateY(${(1 - clamp(k)) * 12}px)` }}>
      <span style={{ position: "absolute", inset: "8px 4px 2px", borderRadius: 14, background: th.name === "dark" ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.85)", opacity: 1 - box, boxShadow: "0 6px 16px rgba(0,0,0,0.06)" }} />
      <span style={{ position: "relative", fontFamily: SERIF, fontStyle: "italic", fontWeight: 900, fontSize: 108, lineHeight: 1.18, letterSpacing: -1,
        background: `linear-gradient(175deg, ${th.accent} 20%, ${th.accent2} 95%)`, WebkitBackgroundClip: "text", color: "transparent" }}>{w.t}</span>
      <span style={{ position: "absolute", inset: "10px 2px 4px", border: `3px solid ${th.accent}`, opacity: box, clipPath: `inset(0 ${100 - box * 100}% 0 0)` }}>
        {box > 0.6 ? <>{handle({ left: -hs / 2 - 1, top: -hs / 2 - 1 })}{handle({ right: -hs / 2 - 1, top: -hs / 2 - 1 })}{handle({ left: -hs / 2 - 1, bottom: -hs / 2 - 1 })}{handle({ right: -hs / 2 - 1, bottom: -hs / 2 - 1 })}</> : null}
      </span>
    </span>
  );
};
const PhraseView: React.FC<{ th: Theme; p: Phrase; t: number; end: number }> = ({ th, p, t, end }) => {
  const out = clamp((t - (end - 0.25)) / 0.25);
  const style: React.CSSProperties = p.zone === "top"
    ? { position: "absolute", left: 50, right: 50, bottom: 1920 - TOP_ZONE_BOTTOM, display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "baseline", columnGap: 20 }
    : { position: "absolute", left: 50, right: 50, top: BOTTOM_ZONE_TOP, display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "baseline", columnGap: 20 };
  return (
    <div style={{ ...style, opacity: 1 - out, filter: out > 0 ? `blur(${out * 10}px)` : undefined, transform: `translateY(${-out * 24}px)` }}>
      {p.words.map((w, i) => {
        if (w.k) return <KeyWord key={i} th={th} w={w} t={t} />;
        const k = clamp(easeOut((t - (w.s - 0.04)) / 0.18));
        return <span key={i} style={{ fontFamily: SANS, fontWeight: 600, fontSize: 50, letterSpacing: 3, color: th.ink, opacity: k, filter: k < 1 ? `blur(${(1 - k) * 8}px)` : undefined, transform: `translateY(${(1 - k) * 10}px)`, display: "inline-block", lineHeight: 1.5 }}>{w.t}</span>;
      })}
    </div>
  );
};

// ------------------------------------------------------------------ dashed arrow between two cards (world space)
const Arrow: React.FC<{ th: Theme; from: [number, number]; to: [number, number]; k: number }> = ({ th, from, to, k }) => {
  if (k <= 0) return null;
  const [x0, y0] = from, [x1, y1] = to;
  const mx = (x0 + x1) / 2, my = (y0 + y1) / 2 + (y1 > y0 ? -140 : 140);
  const N = 40, n = Math.max(2, Math.round(N * clamp(k)));
  const pts: string[] = []; let ex = x0, ey = y0, px = x0, py = y0;
  for (let i = 0; i < n; i++) { const s = i / (N - 1); const a = (1 - s) * (1 - s), b = 2 * (1 - s) * s, c = s * s; px = ex; py = ey; ex = a * x0 + b * mx + c * x1; ey = a * y0 + b * my + c * y1; pts.push(`${ex},${ey}`); }
  const ang = Math.atan2(ey - py, ex - px) * 180 / Math.PI;
  const minX = Math.min(x0, x1, mx) - 40, minY = Math.min(y0, y1, my) - 40;
  return (
    <svg style={{ position: "absolute", left: minX, top: minY, overflow: "visible" }} width={1} height={1}>
      <g transform={`translate(${-minX},${-minY})`}>
        <polyline points={pts.join(" ")} fill="none" stroke={th.accent} strokeWidth={6} strokeDasharray="16 16" strokeLinecap="round" opacity={0.85} />
        <path d="M-22,-14 L4,0 L-22,14" transform={`translate(${ex},${ey}) rotate(${ang})`} fill="none" stroke={th.accent} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" opacity={0.9} />
      </g>
    </svg>
  );
};

// ------------------------------------------------------------------ the reel
export const UIExplainer: React.FC<Spec> = (spec) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const th = withAccent(THEMES[spec.theme], spec.accent, spec.accent2);
  const S = spec.scenes;
  // active scene and camera
  let k = 0; while (k + 1 < S.length && t >= S[k + 1].start - MOVE + 0.12) k++;
  const next = S[k + 1];
  let camX = worldPos(k)[0], camY = worldPos(k)[1];
  const prevIdx = k > 0 && t < S[k].start + 0.12 ? k - 1 : -1;
  let move = 1;
  if (prevIdx >= 0) { move = ease((t - (S[k].start - MOVE + 0.12)) / MOVE); const a = worldPos(prevIdx), b = worldPos(k); camX = a[0] + (b[0] - a[0]) * move; camY = a[1] + (b[1] - a[1]) * move; }
  const sceneEnd = next ? next.start : spec.duration;
  const local = clamp((t - S[k].start) / Math.max(0.5, sceneEnd - S[k].start));
  const zoom = 1 + 0.035 * local;
  // cards to draw: the previous (during the move), the active one, and the next (it appears as the camera leaves)
  const draw = [k - 1, k, k + 1].filter((i) => i >= 0 && i < S.length);
  const cardU = (i: number) => t - (S[i].start - 0.2);
  // phrases: each lasts until the next phrase in its zone, or until its scene ends
  const sceneOf = (time: number) => { let i = 0; while (i + 1 < S.length && time >= S[i + 1].start - 0.05) i++; return i; };
  const phraseEnd = (pi: number) => {
    const p = spec.phrases[pi]; const s0 = p.words[0].s; const si = sceneOf(s0);
    let end = si + 1 < S.length ? S[si + 1].start - MOVE + 0.12 : spec.duration;
    for (let j = pi + 1; j < spec.phrases.length; j++) if (spec.phrases[j].zone === p.zone) { end = Math.min(end, spec.phrases[j].words[0].s - 0.02); break; }
    return end;
  };
  // sound cues
  const cues: Cue[] = [];
  S.forEach((sc, i) => {
    if (i > 0) cues.push({ at: sc.start - MOVE + 0.05, sfx: "whoosh", vol: 0.28 });
    const dur = (S[i + 1]?.start ?? spec.duration) - sc.start;
    cardEvents(sc.card, dur).forEach((c) => cues.push({ ...c, at: sc.start - 0.2 + c.at }));
  });
  const sfxFile: Record<Cue["sfx"], string> = { click: "sfx/click.wav", pop: "sfx/pop.wav", ding: "sfx/ding.wav", typing: "sfx/typing.wav", whoosh: "sfx/whoosh-soft.wav" };
  return (
    <AbsoluteFill style={{ background: th.bg, overflow: "hidden" }}>
      <Fonts />
      <Background th={th} camX={camX} camY={camY} />
      {/* the world: cards and arrows, moved by the camera */}
      <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: `${CX}px ${CY}px` }}>
        <div style={{ position: "absolute", left: CX - camX, top: CY - camY }}>
          {draw.map((i) => {
            if (i === 0) return null;
            const a = worldPos(i - 1), b = worldPos(i);
            const ak = clamp((t - (S[i].start - MOVE - 0.05)) / (MOVE * 0.85));
            return <Arrow key={"ar" + i} th={th} from={[a[0] + 560, a[1] + (b[1] > a[1] ? 160 : -160)]} to={[b[0] - 600, b[1] + (b[1] > a[1] ? -80 : 80)]} k={ak} />;
          })}
          {draw.map((i) => {
            const u = cardU(i);
            if (u < -0.05) return null;
            const [x, y] = worldPos(i);
            const leaving = i < k || (i === prevIdx);
            const blur = i === prevIdx ? move * 7 : i < k ? 7 : 0;
            const tilt = i === prevIdx ? move * -6 : 0;
            const dur = (S[i + 1]?.start ?? spec.duration) - S[i].start;
            return (
              <div key={"c" + i} style={{ position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) perspective(1600px) rotateY(${tilt}deg)`, filter: blur > 0.2 ? `blur(${blur}px)` : undefined, opacity: leaving ? 1 - 0.4 * move : 1 }}>
                {S[i].tag ? <div style={{ display: "flex", justifyContent: "center", marginBottom: 22, opacity: clamp(u / 0.3) }}><div style={{ padding: "8px 22px", borderRadius: 999, background: th.name === "dark" ? "#f2f2f2" : "#1d2433", color: th.name === "dark" ? "#111" : "#fff", fontFamily: MONO, fontWeight: 700, fontSize: 21, letterSpacing: 2 }}>{S[i].tag}</div></div> : null}
                <CardView th={th} u={u} dur={dur + 0.2} c={S[i].card} />
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      {/* captions */}
      {spec.phrases.map((p, i) => {
        const s0 = p.words[0].s - 0.05; const end = phraseEnd(i);
        if (t < s0 || t >= end) return null;
        return <PhraseView key={"p" + i} th={th} p={p} t={t} end={end} />;
      })}
      {spec.terms ? <div style={{ position: "absolute", left: 80, right: 80, bottom: 190, textAlign: "center", fontFamily: SANS, fontWeight: 500, fontSize: 22, color: th.handleInk }}>{spec.terms}</div> : null}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 118, textAlign: "center", fontFamily: SANS, fontWeight: 500, fontSize: 30, letterSpacing: 1, color: th.handleInk }}>{spec.handle}</div>
      {/* audio */}
      {spec.vo ? <Audio src={staticFile(spec.vo)} /> : null}
      <Audio src={staticFile("music/bed.mp3")} volume={spec.music ?? 0.07} loop />
      {cues.map((c, i) => (
        <Sequence key={"sfx" + i} from={Math.max(0, Math.round(c.at * FPS))} durationInFrames={c.dur ? Math.max(1, Math.round(c.dur * FPS)) : undefined}>
          <Audio src={staticFile(sfxFile[c.sfx])} volume={c.vol ?? 0.3} loop={c.sfx === "typing"} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

// a small built-in example so the studio opens with something (real reels pass their own spec as props)
export const DEMO: Spec = {
  theme: "cream", handle: "@yourhandle", duration: 6,
  phrases: [{ zone: "top", words: [{ t: "Claude", s: 0.3, e: 0.6 }, { t: "se", s: 0.6, e: 0.8 }, { t: "Reels", s: 0.8, e: 1.3, k: true }, { t: "banao", s: 1.3, e: 1.8 }] }],
  scenes: [{ start: 0, card: { type: "big", kicker: "DEMO", big: "3D", sub: "ui-explainer engine" } }],
};
