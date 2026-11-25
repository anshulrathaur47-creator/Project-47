import { AbsoluteFill, Audio, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { LyricCard } from "./LyricCard";
import { Props, SpotifyLyric } from "./SpotifyLyric";
import caps from "./captions.json";
import demo from "../public/props.json";

// Tutorial reel: "Claude se Spotify-theme lyrical reel kaise banaye" (Hindi AI voice-over, Hinglish captions).
const FPS = 30;
export const TUTORIAL_SEC = 31.0;
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
type Cap = { start: number; end: number; words: { t: number; e: number; w: string }[] };
const CAPS = caps as Cap[];
const D = demo as unknown as Props;
const SCENES = [0, 4.35, 6.8, 10.3, 15.8, 19.7, 23.7, 26.2, TUTORIAL_SEC];
const PINK = "#d9497c";
const BG = "#0d0b10";

// demo embedded as a phone screen (scaled 1080x1920 composition)
const Phone: React.FC<{ scale: number; x: number; y: number; children: React.ReactNode; glow?: string; rot?: number }> = ({ scale, x, y, children, glow, rot = 0 }) => (
  <div style={{ position: "absolute", left: x, top: y, width: 1080 * scale + 24, height: 1920 * scale + 24, borderRadius: 48 * scale + 12,
    background: "#111", padding: 12, boxShadow: `0 30px 80px rgba(0,0,0,0.6)${glow ? `, 0 0 60px ${glow}` : ""}`, transform: `rotate(${rot}deg)` }}>
    <div style={{ width: 1080 * scale, height: 1920 * scale, borderRadius: 40 * scale, overflow: "hidden", position: "relative" }}>
      <div style={{ width: 1080, height: 1920, transform: `scale(${scale})`, transformOrigin: "0 0" }}>{children}</div>
    </div>
  </div>
);

const Captions: React.FC<{ t: number }> = ({ t }) => {
  const line = CAPS.find((c) => t >= c.start - 0.1 && t < c.end + 0.15);
  if (!line) return null;
  // show the current chunk of up to 3 words
  const i = Math.max(0, line.words.filter((w) => w.t <= t).length - 1);
  const c0 = Math.floor(i / 3) * 3;
  const chunk = line.words.slice(c0, c0 + 3);
  const pop = spring({ frame: Math.round((t - chunk[0].t) * FPS), fps: FPS, config: { damping: 12, mass: 0.5 } });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: t >= SCENES[5] && t < SCENES[6] ? 1610 : 1240, display: "flex", justifyContent: "center" }}>
      <div style={{ background: "#fff", borderRadius: 22, padding: "14px 30px", transform: `scale(${0.85 + 0.15 * pop}) rotate(-1.5deg)`,
        boxShadow: "0 10px 30px rgba(0,0,0,0.45)", fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 70, color: "#111", letterSpacing: -1.5 }}>
        {chunk.map((w, k) => {
          const on = t >= w.t && t < w.e + 0.05;
          return <span key={k} style={{ marginRight: k < chunk.length - 1 ? 18 : 0, color: on ? PINK : "#111" }}>{w.w}</span>;
        })}
      </div>
    </div>
  );
};

const Chat: React.FC<{ t: number }> = ({ t }) => {
  const k1 = spring({ frame: Math.round((t - 0.2) * FPS), fps: FPS, config: { damping: 14 } });
  const k2 = spring({ frame: Math.round((t - 1.2) * FPS), fps: FPS, config: { damping: 14 } });
  const k3 = spring({ frame: Math.round((t - 2.4) * FPS), fps: FPS, config: { damping: 14 } });
  const bubble = (k: number, me: boolean, child: React.ReactNode, top: number) => (
    <div style={{ position: "absolute", top, [me ? "right" : "left"]: 70, maxWidth: 760, opacity: k, transform: `translateY(${(1 - k) * 40}px) scale(${0.9 + 0.1 * k})`,
      transformOrigin: me ? "right" : "left", background: me ? "#2c2730" : "#f4efe8", color: me ? "#fff" : "#1a1714", borderRadius: 34,
      padding: "26px 34px", fontSize: 42, fontFamily: "Inter, sans-serif", lineHeight: 1.35, boxShadow: "0 12px 30px rgba(0,0,0,0.35)" }}>{child}</div>
  );
  return (
    <AbsoluteFill style={{ background: "linear-gradient(180deg, #1b1520, #0d0b10)" }}>
      <div style={{ position: "absolute", top: 150, left: 0, right: 0, textAlign: "center", color: "#e8c9a8", fontFamily: "Inter, sans-serif", fontWeight: 700, fontSize: 40 }}>
        ✳ Chat with Claude
      </div>
      {bubble(k1, true, <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
        <div style={{ width: 86, height: 86, borderRadius: 18, background: PINK, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 48 }}>♪</div>
        <div><div style={{ fontWeight: 800 }}>mera_gaana.mp3</div><div style={{ fontSize: 30, opacity: 0.7 }}>Audio · 0:21</div></div></div>, 300)}
      {bubble(k2, true, <div><div style={{ fontWeight: 800, marginBottom: 8 }}>Lyrics:</div>Kisi gaadi ke sheeshe par jami dhool par…<br />Main uska aur mera naam likha karta hoon…</div>, 470)}
      {bubble(k3, true, <span>Spotify theme mein <b>pink lyrical reel</b> bana do ✨</span>, 760)}
    </AbsoluteFill>
  );
};

const Timeline: React.FC<{ t: number }> = ({ t }) => {
  const words = ["Kisi", "gaadi", "ke", "sheeshe", "par", "jami", "dhool", "par"];
  const times = ["0:00.4", "0:00.9", "0:01.2", "0:01.4", "0:01.9", "0:02.1", "0:02.5", "0:02.8"];
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, #2a1420, #0b0709)" }}>
      <div style={{ position: "absolute", top: 220, left: 0, right: 0, textAlign: "center", color: "#fff", fontFamily: "Inter, sans-serif", fontWeight: 800, fontSize: 54 }}>
        Har shabd ki timing ⏱
      </div>
      {/* waveform */}
      <div style={{ position: "absolute", left: 60, right: 60, top: 470, height: 200, display: "flex", alignItems: "center", gap: 6 }}>
        {Array.from({ length: 70 }).map((_, i) => {
          const h = 30 + 150 * Math.abs(Math.sin(i * 0.7) * Math.sin(i * 0.23 + 1));
          const lit = i / 70 < clamp(t / 5);
          return <div key={i} style={{ flex: 1, height: h, borderRadius: 4, background: lit ? PINK : "rgba(255,255,255,0.25)", boxShadow: lit ? `0 0 10px ${PINK}` : "none" }} />;
        })}
      </div>
      <div style={{ position: "absolute", left: 60 + (960 * clamp(t / 5)), top: 440, width: 4, height: 260, background: "#fff", boxShadow: "0 0 16px #fff" }} />
      {/* words landing with timestamps */}
      <div style={{ position: "absolute", left: 70, right: 70, top: 760, display: "flex", flexWrap: "wrap", gap: 20 }}>
        {words.map((w, i) => {
          const k = spring({ frame: Math.round((t - 0.35 - i * 0.5) * FPS), fps: FPS, config: { damping: 12 } });
          return (
            <div key={i} style={{ opacity: k, transform: `translateY(${(1 - k) * -60}px)`, background: "rgba(255,255,255,0.08)", border: `2px solid ${PINK}`,
              borderRadius: 18, padding: "12px 20px", fontFamily: "Inter, sans-serif", textAlign: "center" }}>
              <div style={{ color: "#fff", fontWeight: 800, fontSize: 46 }}>{w}</div>
              <div style={{ color: "#ffb3cd", fontSize: 26 }}>{times[i]}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Terminal: React.FC<{ t: number }> = ({ t }) => {
  const cmd = "python3 make_props.py --audio gaana.mp3 --lyrics lyrics.txt --card pink";
  const n = Math.floor(clamp(t / 1.1) * cmd.length);
  const p = clamp((t - 1.2) / 0.9);
  return (
    <AbsoluteFill style={{ background: "linear-gradient(180deg, #120f16, #0b0a0d)" }}>
      <div style={{ position: "absolute", left: 60, right: 60, top: 380, background: "#1c1a20", borderRadius: 26, padding: 40, boxShadow: "0 30px 70px rgba(0,0,0,0.6)",
        fontFamily: "'JetBrains Mono', 'DejaVu Sans Mono', monospace", fontSize: 36, color: "#e8e8e8", lineHeight: 1.5 }}>
        <div style={{ display: "flex", gap: 12, marginBottom: 26 }}>{["#ff5f57", "#febc2e", "#28c840"].map((c) => <div key={c} style={{ width: 22, height: 22, borderRadius: "50%", background: c }} />)}</div>
        <span style={{ color: PINK }}>$ </span>{cmd.slice(0, n)}<span style={{ opacity: Math.floor(t * 3) % 2 ? 1 : 0 }}>▌</span>
        {p > 0 ? (
          <div style={{ marginTop: 34 }}>
            <div style={{ height: 26, background: "#333", borderRadius: 13, overflow: "hidden" }}>
              <div style={{ width: `${p * 100}%`, height: "100%", background: PINK, boxShadow: `0 0 20px ${PINK}` }} />
            </div>
            <div style={{ marginTop: 18, color: p >= 1 ? "#5ee38a" : "#aaa" }}>{p >= 1 ? "✅ reel.mp4 ready (1080x1920)" : `rendering… ${Math.round(p * 100)}%`}</div>
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

const CTA: React.FC<{ t: number }> = ({ t }) => {
  const k = spring({ frame: Math.round(t * FPS), fps: FPS, config: { damping: 12 } });
  const pulse = 1 + 0.06 * Math.sin(t * 8);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: 0, filter: "blur(18px) brightness(0.45)" }}>
        <LyricCard {...D} volume={0} noFade />
      </div>
      <div style={{ position: "absolute", top: 380, left: 0, right: 0, textAlign: "center", transform: `scale(${0.8 + 0.2 * k})`, opacity: k }}>
        <div style={{ color: "#fff", fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 64 }}>Comment karo</div>
        <div style={{ display: "inline-block", marginTop: 26, background: PINK, color: "#fff", fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 110,
          padding: "16px 50px", borderRadius: 30, boxShadow: `0 0 60px ${PINK}`, transform: `scale(${pulse})` }}>"LYRICS"</div>
        <div style={{ color: "rgba(255,255,255,0.85)", fontFamily: "Inter, sans-serif", fontWeight: 600, fontSize: 44, marginTop: 40 }}>aur aisi reels ke liye</div>
        <div style={{ display: "inline-block", marginTop: 26, border: "4px solid #fff", color: "#fff", fontFamily: "Inter, sans-serif", fontWeight: 800, fontSize: 56,
          padding: "14px 60px", borderRadius: 24, background: t > 1.4 ? "#fff" : "transparent", ...(t > 1.4 ? { color: "#111" } : {}) }}>{t > 1.4 ? "Following ✓" : "Follow"}</div>
      </div>
    </AbsoluteFill>
  );
};

export const Tutorial: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const s = (i: number) => Math.round(SCENES[i] * FPS);
  const len = (i: number) => s(i + 1) - s(i);
  let flash = 0;
  for (const c of SCENES.slice(1, -1)) flash = Math.max(flash, 1 - Math.abs(t - c) / 0.08);
  const sel = (u: number) => spring({ frame: Math.round((t - u) * FPS), fps, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ background: BG }}>
      <Audio src={staticFile("vo.wav")} />
      {SCENES.slice(1, -1).map((c, i) => (
        <Sequence key={i} from={Math.max(0, Math.round((c - 0.25) * FPS))} durationInFrames={20}><Audio src={staticFile("whoosh.wav")} volume={0.35} /></Sequence>
      ))}
      {/* 1-2: hook, the pink card playing, then it shrinks into a phone */}
      <Sequence from={0} durationInFrames={s(3)}>
        <AbsoluteFill>
          {t < SCENES[1] ? <LyricCard {...D} volume={0.22} noFade /> : (
            <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, #3a1828, #0b0709)" }}>
              <Phone scale={interpolate(t, [SCENES[1], SCENES[1] + 0.5], [0.62, 0.5], { extrapolateRight: "clamp" })} x={interpolate(t, [SCENES[1], SCENES[1] + 0.5], [190, 260], { extrapolateRight: "clamp" })}
                y={170} glow={PINK}>
                <LyricCard {...D} volume={0.22} noFade />
              </Phone>
              <div style={{ position: "absolute", top: 1130, left: 0, right: 0, textAlign: "center", color: "#fff", fontFamily: "Inter, sans-serif", fontWeight: 800, fontSize: 46, opacity: sel(SCENES[1] + 0.3) }}>
                Bina kisi editing app ke ✂️❌
              </div>
            </AbsoluteFill>
          )}
          {t < SCENES[1] ? (
            <div style={{ position: "absolute", top: 120, left: 0, right: 0, textAlign: "center" }}>
              <span style={{ background: "rgba(0,0,0,0.55)", color: "#fff", fontFamily: "Inter, sans-serif", fontWeight: 800, fontSize: 44, padding: "12px 26px", borderRadius: 16 }}>
                Claude se banao 👇
              </span>
            </div>
          ) : null}
        </AbsoluteFill>
      </Sequence>
      <Sequence from={s(2)} durationInFrames={len(2)}><ChatWrap /></Sequence>
      <Sequence from={s(3)} durationInFrames={len(3)}><TimelineWrap /></Sequence>
      {/* 5: two themes side by side */}
      <Sequence from={s(4)} durationInFrames={len(4)}>
        <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, #241a2c, #0b0709)" }}>
          <Phone scale={0.4} x={70} y={260} glow={t > 16.8 && t < 18.7 ? PINK : undefined} rot={-3}><LyricCard {...D} volume={0.15} noFade /></Phone>
          <Phone scale={0.4} x={566} y={260} glow={t > 18.7 ? "#ffc272" : undefined} rot={3}><SpotifyLyric {...D} volume={0} noFade /></Phone>
          {[{ x: 70, l: "Pink Card", on: t > 16.8 }, { x: 566, l: "Music Player", on: t > 18.7 }].map((b) => (
            <div key={b.l} style={{ position: "absolute", top: 1080, left: b.x, width: 456, textAlign: "center", fontFamily: "Inter, sans-serif", fontWeight: 800, fontSize: 44,
              color: b.on ? "#fff" : "rgba(255,255,255,0.4)", transform: `scale(${b.on ? 1.08 : 1})` }}>{b.l}</div>
          ))}
        </AbsoluteFill>
      </Sequence>
      {/* 6: glow + bars close-up */}
      <Sequence from={s(5)} durationInFrames={len(5)}>
        <AbsoluteFill style={{ transform: `scale(${interpolate(t, [SCENES[5], SCENES[6]], [1.0, 1.12])})`, transformOrigin: "50% 60%" }}>
          <SpotifyLyric {...D} volume={0.22} noFade />
        </AbsoluteFill>
      </Sequence>
      <Sequence from={s(6)} durationInFrames={len(6)}><TerminalWrap /></Sequence>
      <Sequence from={s(7)} durationInFrames={len(7)}><CTAWrap /></Sequence>
      <Captions t={t} />
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash * 0.5, pointerEvents: "none" }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: interpolate(t, [0, 0.25, TUTORIAL_SEC - 0.5, TUTORIAL_SEC], [1, 0, 0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

// local-time wrappers (inside a Sequence, useCurrentFrame starts at 0)
const local = () => useCurrentFrame() / FPS;
const ChatWrap = () => <Chat t={local()} />;
const TimelineWrap = () => <Timeline t={local()} />;
const TerminalWrap = () => <Terminal t={local()} />;
const CTAWrap = () => <CTA t={local()} />;
void Img;
