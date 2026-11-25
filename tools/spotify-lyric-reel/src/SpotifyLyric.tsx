import { useAudioData, visualizeAudio } from "@remotion/media-utils";
import { AbsoluteFill, Audio, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// A music-player lyric reel: now-playing card, synced lyrics that scroll like a streaming app's lyrics view,
// word-by-word glow on the line being sung, beat-reactive glowing bars, light leaks and floating particles.
// Generic player look (no third-party logos).

export type Word = { t: number; e: number; w: string };
export type Line = { start: number; end: number; text: string; words: Word[] };
export type Props = {
  audio: string;          // file in public/
  cover?: string;         // file in public/ (square)
  title: string;
  artist: string;
  bg: string;             // main background colour (from the cover)
  accent: string;         // glow / progress colour
  durationSec: number;
  lines: Line[];
  font?: string;
};

const W = 1080;
const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));

const Icon: React.FC<{ d: string; size?: number; fill?: string }> = ({ d, size = 44, fill = "#fff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24"><path d={d} fill={fill} /></svg>
);
const HEART = "M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 5 6.4 5c2 0 3.6 1.1 4.6 2.7C12 6.1 13.6 5 15.6 5 19 5 21.1 8.4 19.6 11.8 17.5 16.4 12 21 12 21z";
const PREV = "M6 6h2v12H6zm3.5 6L18 6v12z";
const NEXT = "M16 6h2v12h-2zM6 18l8.5-6L6 6z";
const PAUSE = "M7 5h3.5v14H7zm6.5 0H17v14h-3.5z";
const SHUFFLE = "M17 3l4 4-4 4V8h-2.6l-7 8H4v-2h2.6l7-8H17zM4 6h3.4l2.2 2.5-1.3 1.5L6.6 8H4zm11.4 8.5l1.3-1.5L17 13.4V11l4 4-4 4v-3h-2.6z";
const REPEAT = "M7 7h10v3l4-4-4-4v3H5v6h2zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2z";

const Particles: React.FC<{ t: number; accent: string; energy: number }> = ({ t, accent, energy }) => {
  const dots = Array.from({ length: 36 }, (_, i) => {
    const seed = (i * 9301 + 49297) % 233280 / 233280;
    const x = (seed * 997) % 1;
    const sp = 30 + ((i * 37) % 50);
    const y = 1920 - ((t * sp + i * 173) % 2100);
    const r = 2 + (i % 4);
    return { x: x * W, y, r, o: 0.25 + 0.35 * ((i * 13) % 7) / 7 };
  });
  return (
    <AbsoluteFill>
      {dots.map((d, i) => (
        <div key={i} style={{ position: "absolute", left: d.x, top: d.y, width: d.r * 2, height: d.r * 2, borderRadius: "50%",
          background: "#fff", opacity: d.o * (0.6 + energy), boxShadow: `0 0 ${10 + energy * 20}px ${accent}` }} />
      ))}
    </AbsoluteFill>
  );
};

export const SpotifyLyric: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const font = p.font ?? "'Noto Sans Devanagari', 'Noto Sans', sans-serif";
  const audioData = useAudioData(staticFile(p.audio));
  const bars = 40;
  const spectrum = audioData ? visualizeAudio({ fps, frame, audioData, numberOfSamples: 64, smoothing: true }) : new Array(64).fill(0);
  const bass = clamp((spectrum[0] + spectrum[1] + spectrum[2]) / 1.2);
  const energy = clamp(spectrum.slice(0, 24).reduce((a, b) => a + b, 0) / 6);

  // which line is being sung (or the last one sung)
  let cur = p.lines.findIndex((l) => t >= l.start && t < l.end);
  if (cur < 0) cur = Math.max(-1, p.lines.filter((l) => l.start <= t).length - 1);
  const intro = spring({ frame, fps, config: { damping: 18 } });

  // scroll: smoothly bring the current line to the anchor
  const LINE_GAP = 40;
  const lineH = (txt: string) => (txt.length > 22 ? 2 : 1) * 92 + LINE_GAP;
  const offsets: number[] = [];
  let acc = 0;
  for (const l of p.lines) { offsets.push(acc); acc += lineH(l.text); }
  const target = (i: number) => (i < 0 ? -200 : offsets[i]);
  let scroll = target(cur);
  if (cur >= 0) {
    const l = p.lines[cur];
    const k = spring({ frame: frame - Math.round(l.start * fps), fps, config: { damping: 20, mass: 0.6 } });
    scroll = target(cur - 1) + (target(cur) - target(cur - 1)) * k;
  }

  return (
    <AbsoluteFill style={{ background: p.bg, fontFamily: font, overflow: "hidden" }}>
      <Audio src={staticFile(p.audio)} />
      {/* blurred cover wash + moving light leaks */}
      {p.cover ? (
        <Img src={staticFile(p.cover)} style={{ position: "absolute", left: -300, top: -200, width: 1680, height: 1680, objectFit: "cover",
          filter: "blur(90px) saturate(1.5) brightness(0.8)", opacity: 0.32, transform: `scale(${1.05 + 0.04 * Math.sin(t * 0.4)}) rotate(${t * 2}deg)` }} />
      ) : null}
      <AbsoluteFill style={{ background: `radial-gradient(circle at ${50 + 30 * Math.sin(t * 0.5)}% ${30 + 20 * Math.cos(t * 0.37)}%, ${p.accent}55 0%, transparent 45%),
        radial-gradient(circle at ${40 - 25 * Math.cos(t * 0.3)}% ${80 + 10 * Math.sin(t * 0.6)}%, #ffffff22 0%, transparent 40%),
        linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0.2) 40%, rgba(0,0,0,0.65) 100%)` }} />
      <Particles t={t} accent={p.accent} energy={energy} />

      {/* now-playing card */}
      <div style={{ position: "absolute", left: 70, right: 70, top: 150, opacity: intro, transform: `translateY(${(1 - intro) * 40}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 36 }}>
          <div style={{ width: 230, height: 230, borderRadius: 22, overflow: "hidden", flexShrink: 0, background: "#222",
            transform: `scale(${1 + bass * 0.05})`, boxShadow: `0 0 ${30 + bass * 60}px ${p.accent}aa, 0 20px 40px rgba(0,0,0,0.5)` }}>
            {p.cover ? <Img src={staticFile(p.cover)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ color: "#fff", fontSize: 54, fontWeight: 800, lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              textShadow: `0 0 18px ${p.accent}88` }}>{p.title}</div>
            <div style={{ color: "rgba(255,255,255,0.75)", fontSize: 36, fontWeight: 500, marginTop: 6 }}>{p.artist}</div>
          </div>
          <div style={{ transform: `scale(${1 + bass * 0.15})`, filter: `drop-shadow(0 0 ${8 + bass * 14}px ${p.accent})` }}>
            <Icon d={HEART} size={56} fill={p.accent} />
          </div>
        </div>
        {/* progress */}
        <div style={{ marginTop: 40, height: 10, borderRadius: 6, background: "rgba(255,255,255,0.25)" }}>
          <div style={{ width: `${clamp(t / p.durationSec) * 100}%`, height: "100%", borderRadius: 6, background: "#fff", position: "relative",
            boxShadow: `0 0 16px ${p.accent}` }}>
            <div style={{ position: "absolute", right: -11, top: -7, width: 24, height: 24, borderRadius: "50%", background: "#fff", boxShadow: `0 0 18px ${p.accent}` }} />
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", color: "rgba(255,255,255,0.75)", fontSize: 28, marginTop: 12, fontFamily: "sans-serif" }}>
          <span>{fmt(t)}</span><span>-{fmt(Math.max(0, p.durationSec - t))}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, padding: "0 20px" }}>
          <Icon d={SHUFFLE} size={44} fill={p.accent} />
          <Icon d={PREV} size={64} />
          <div style={{ width: 120, height: 120, borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: `0 0 ${20 + bass * 40}px ${p.accent}`, transform: `scale(${1 + bass * 0.06})` }}>
            <Icon d={PAUSE} size={60} fill="#111" />
          </div>
          <Icon d={NEXT} size={64} />
          <Icon d={REPEAT} size={44} />
        </div>
      </div>

      {/* lyrics */}
      <div style={{ position: "absolute", left: 70, right: 70, top: 760, height: 700, overflow: "hidden",
        WebkitMaskImage: "linear-gradient(180deg, transparent 0%, #000 12%, #000 82%, transparent 100%)" }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 120 - scroll }}>
          {p.lines.map((l, i) => {
            const active = i === cur && t < l.end + 0.15;
            const past = i < cur || (i === cur && !active);
            const op = active ? 1 : past ? 0.55 : 0.32;
            return (
              <div key={i} style={{ fontSize: 76, fontWeight: 800, lineHeight: 1.28, marginBottom: LINE_GAP, minHeight: lineH(l.text) - LINE_GAP,
                transform: `scale(${active ? 1 : 0.97})`, transformOrigin: "left center", opacity: op,
                color: active ? "rgba(255,255,255,0.45)" : past ? "#fff" : "rgba(0,0,0,0.55)" }}>
                {active
                  ? l.words.map((w, j) => {
                      const k = clamp((t - w.t) / Math.max(0.08, w.e - w.t));
                      const lit = t >= w.t;
                      return (
                        <span key={j} style={{ color: lit ? "#fff" : "rgba(255,255,255,0.45)", display: "inline-block", marginRight: 18,
                          transform: `translateY(${lit ? -4 * (1 - k) : 0}px) scale(${lit ? 1 + 0.06 * (1 - k) : 1})`,
                          textShadow: lit ? `0 0 ${18 + 24 * (1 - k) + bass * 16}px ${p.accent}, 0 0 ${40 + bass * 30}px ${p.accent}aa, 0 0 6px #fff` : "none" }}>{w.w}</span>
                      );
                    })
                  : l.text}
              </div>
            );
          })}
        </div>
      </div>

      {/* glowing spectrum bars (kept above the caption area) */}
      <div style={{ position: "absolute", left: 70, right: 70, top: 1480, height: 110, display: "flex", alignItems: "flex-end", gap: 8 }}>
        {Array.from({ length: bars }).map((_, i) => {
          const v = spectrum[Math.floor((i / bars) * 40)] ?? 0;
          const h = 12 + Math.min(98, Math.sqrt(v) * 190);
          return <div key={i} style={{ flex: 1, height: h, borderRadius: 6, background: `linear-gradient(180deg, #fff, ${p.accent})`,
            boxShadow: `0 0 ${8 + v * 30}px ${p.accent}`, opacity: 0.85 }} />;
        })}
      </div>
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: interpolate(t, [0, 0.4, p.durationSec - 0.8, p.durationSec], [1, 0, 0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }} />
    </AbsoluteFill>
  );
};
