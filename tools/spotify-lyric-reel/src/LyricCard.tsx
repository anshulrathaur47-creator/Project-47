import { useAudioData, visualizeAudio } from "@remotion/media-utils";
import { AbsoluteFill, Audio, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { Props } from "./SpotifyLyric";

// "Lyrics card" look: a coloured lyrics panel (pink by default) floating in 3D on a dark stage, slowly drifting.
// Small cover + title + artist at the top, big bold lines; the line being sung is white with a soft bloom on each
// word as it lands, the lines ahead are dark and translucent, and the far lines melt into blur.

const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));

export const LyricCard: React.FC<Props & { cardColor?: string }> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const card = p.cardColor ?? "#d9497c";
  const font = p.font ?? "Inter, 'Noto Sans Devanagari', sans-serif";
  const audioData = useAudioData(staticFile(p.audio));
  const spec = audioData ? visualizeAudio({ fps, frame, audioData, numberOfSamples: 32, smoothing: true }) : new Array(32).fill(0);
  const bass = clamp((spec[0] + spec[1] + spec[2]) / 1.2);

  let cur = p.lines.findIndex((l) => t >= l.start && t < l.end);
  if (cur < 0) cur = Math.max(-1, p.lines.filter((l) => l.start <= t).length - 1);

  // line heights (2 rows for long lines) and a springy scroll that keeps the current line near the top
  const GAP = 30, ROW = 86;
  const rows = (s: string) => Math.max(1, Math.ceil(s.length / 20));   // ~20 chars per row at 70px
  const offs: number[] = [];
  let acc = 0;
  for (const l of p.lines) { offs.push(acc); acc += rows(l.text) * ROW + GAP; }
  const at = (i: number) => (i < 0 ? -40 : offs[i]);
  let scroll = at(cur);
  if (cur >= 0) {
    const k = spring({ frame: frame - Math.round(p.lines[cur].start * fps), fps, config: { damping: 22, mass: 0.7 } });
    scroll = at(cur - 1) + (at(cur) - at(cur - 1)) * k;
  }

  // the card drifts in 3D: slow sway plus a tiny kick on the bass
  const intro = spring({ frame, fps, config: { damping: 16, mass: 1.2 } });
  const rx = 14 + 3 * Math.sin(t * 0.35) - bass * 1.5;
  const ry = -16 + 5 * Math.sin(t * 0.22 + 1) ;
  const rz = -4 + 1.5 * Math.sin(t * 0.3);
  const sheen = 30 + 40 * Math.sin(t * 0.4);

  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, #2a1420 0%, #0b0709 60%, #050405 100%)", overflow: "hidden" }}>
      <Audio src={staticFile(p.audio)} volume={p.volume ?? 1} />
      {/* coloured spill of the card on the dark stage */}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 46%, ${card}${Math.round(40 + bass * 50).toString(16).padStart(2, "0")} 0%, transparent 55%)` }} />
      <AbsoluteFill style={{ perspective: 1500, perspectiveOrigin: "50% 40%" }}>
        <div style={{ position: "absolute", left: 90, top: 400, width: 900, height: 1060, borderRadius: 34, overflow: "hidden",
          background: `linear-gradient(160deg, ${card} 0%, ${card} 55%, color-mix(in srgb, ${card} 70%, #000) 100%)`,
          transform: `translateY(${(1 - intro) * 120}px) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz}deg) scale(${0.92 + 0.08 * intro})`,
          boxShadow: `0 60px 120px rgba(0,0,0,0.6), 0 0 ${80 + bass * 80}px ${card}66`, fontFamily: font, opacity: intro }}>
          {/* header */}
          <div style={{ position: "absolute", left: 60, top: 54, right: 60, display: "flex", alignItems: "center", gap: 22 }}>
            <div style={{ width: 84, height: 84, borderRadius: 10, overflow: "hidden", background: "#0004", flexShrink: 0 }}>
              {p.cover ? <Img src={staticFile(p.cover)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: "#fff", fontWeight: 800, fontSize: 36, lineHeight: 1.2 }}>{p.title}</div>
              <div style={{ color: "rgba(255,255,255,0.78)", fontWeight: 500, fontSize: 26 }}>{p.artist}</div>
            </div>
            {/* generic "more" dots, no third-party logo */}
            <div style={{ display: "flex", gap: 7 }}>
              {[0, 1, 2].map((i) => <div key={i} style={{ width: 9, height: 9, borderRadius: "50%", background: "rgba(255,255,255,0.8)" }} />)}
            </div>
          </div>
          {/* lyrics */}
          <div style={{ position: "absolute", left: 60, right: 60, top: 190, bottom: 0, overflow: "hidden",
            WebkitMaskImage: "linear-gradient(180deg, #000 0%, #000 62%, transparent 100%)" }}>
            <div style={{ position: "absolute", left: 0, right: 0, top: 30 - scroll }}>
              {p.lines.map((l, i) => {
                const active = i === cur && t < l.end + 0.2;
                const past = i < cur || (i === cur && !active);
                const dist = i - cur;
                const blur = dist >= 2 ? Math.min(6, (dist - 1) * 2.2) : 0;
                return (
                  <div key={i} style={{ fontSize: 70, fontWeight: 800, lineHeight: `${ROW}px`, marginBottom: GAP, letterSpacing: -1,
                    height: rows(l.text) * ROW, filter: blur ? `blur(${blur}px)` : undefined,
                    color: active ? "#fff" : past ? "rgba(255,255,255,0.72)" : "rgba(70,10,30,0.62)" }}>
                    {active
                      ? l.words.map((w, j) => {
                          const lit = t >= w.t;
                          const k = clamp((t - w.t) / Math.max(0.1, w.e - w.t));
                          const bloom = lit ? 1 - k * 0.6 : 0;
                          return (
                            <span key={j} style={{ display: "inline-block", marginRight: 20,
                              color: lit ? "#fff" : "rgba(255,255,255,0.55)",
                              textShadow: lit ? `0 0 ${10 + 26 * bloom}px rgba(255,255,255,${0.55 + 0.4 * bloom}), 0 0 ${30 + bass * 20}px rgba(255,230,240,0.5)` : "none" }}>
                              {w.w}
                            </span>
                          );
                        })
                      : l.text}
                  </div>
                );
              })}
            </div>
          </div>
          {/* moving sheen across the card surface */}
          <div style={{ position: "absolute", inset: 0, pointerEvents: "none",
            background: `linear-gradient(115deg, transparent ${sheen - 18}%, rgba(255,255,255,0.16) ${sheen}%, transparent ${sheen + 18}%)` }} />
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: p.noFade ? 0 : interpolate(t, [0, 0.35, p.durationSec - 0.7, p.durationSec], [1, 0, 0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }} />
    </AbsoluteFill>
  );
};
