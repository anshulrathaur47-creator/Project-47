import { AbsoluteFill, Audio, interpolate, Sequence, spring, staticFile, useCurrentFrame } from "remotion";

// "Claude Ultra 6 mahine free" (ReelAudio-16334): AI-offer news reel, Hindi VO, Hinglish word captions.
const FPS = 30;
export const DURATION = Math.ceil(36.45 * FPS);
const ACC = "#e8834f";      // warm coral accent
const BG = "#120f0e";
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const pop = (t: number, at: number, damping = 11) => spring({ frame: Math.round((t - at) * FPS), fps: FPS, config: { damping, mass: 0.55 } });

// spoken words (Whisper, chunked), in Hinglish
const W: [number, string][] = [
  [0.0, "Claude"], [0.46, "ka"], [0.6, "sabse"], [1.12, "bada"], [1.36, "plan,"],
  [1.68, "Claude"], [2.32, "ULTRA"], [2.76, "6"], [3.22, "mahine"], [3.66, "bilkul"], [4.16, "FREE!"],
  [4.4, "Matlab"], [5.12, "Pro"], [5.38, "se"], [5.6, "10"], [5.92, "guna"], [6.2, "usage"],
  [6.66, "aur"], [6.98, "5"], [7.34, "ghante"], [7.66, "wali"], [7.88, "limit"], [8.22, "bhi"], [8.34, "khatam."],
  [8.66, "Official"], [9.48, "program"], [9.9, "hai:"], [10.06, "Claude"], [10.76, "for"], [10.88, "Open"], [11.24, "Source."],
  [11.68, "Open"], [11.98, "Source"], [12.52, "pe"], [12.66, "kaam"], [12.8, "karte"], [13.12, "ho?"],
  [13.4, "Bas"], [13.76, "ek"], [14.14, "form"], [14.34, "bharna"], [14.68, "hai."],
  [15.18, "Is"], [15.38, "plan"], [15.62, "ki"], [15.86, "keemat"], [16.18, "$200"], [16.88, "mahina,"],
  [17.64, "yaani"], [17.86, "6"], [18.14, "mahine"], [18.62, "ke"], [18.96, "$1,200."],
  [20.48, "Ek"], [21.0, "paisa"], [21.32, "nahi"], [21.52, "dena!"],
  [22.06, "Form"], [22.42, "kaise"], [22.78, "bharna"], [23.12, "hai,"], [23.46, "aur"], [23.7, "kya"], [23.96, "dhyaan"], [24.1, "rakhna"], [24.4, "hai,"],
  [24.62, "sab"], [24.96, "main"], [25.12, "step"], [25.28, "by"], [25.48, "step"], [25.68, "bata"], [25.94, "dunga."],
  [26.36, "Form"], [26.8, "ka"], [27.04, "link"], [27.2, "aur"], [27.52, "poori"], [27.8, "guide"], [27.96, "chahiye?"],
  [28.68, "Comment"], [28.96, "mein"], [29.2, "likho"], [29.42, "“CLAUDE”"],
  [30.1, "Main"], [30.66, "seedha"], [30.96, "tumhe"], [31.46, "DM"], [31.62, "kar"], [31.8, "dunga,"],
  [31.92, "aur"], [32.44, "follow"], [32.68, "karo"], [33.04, "taaki"], [33.54, "aisi"], [33.96, "free"], [34.24, "AI"], [34.56, "offers"], [34.88, "miss"], [35.26, "na"], [35.54, "ho."],
];
const KEY = new Set(["ULTRA", "FREE!", "10", "khatam.", "Source.", "form", "$200", "$1,200.", "dena!", "“CLAUDE”", "DM", "follow"]);
const SC = [0, 4.4, 8.66, 13.4, 15.18, 20.48, 22.06, 28.68, 31.92, 36.45];

const Captions: React.FC<{ t: number }> = ({ t }) => {
  const i = Math.max(0, W.filter(([s]) => s <= t).length - 1);
  // chunk of up to 3 words, breaking at sentence ends
  let a = i; while (a > 0 && i - a < 2 && !/[.?!:,]$/.test(W[a - 1][1])) a--;
  const chunk: [number, string][] = [];
  for (let k = a; k < W.length && chunk.length < 3; k++) { chunk.push(W[k]); if (/[.?!:,]$/.test(W[k][1]) && k >= i) break; }
  const p = pop(t, chunk[0][0], 13);
  const top = t >= SC[7] && t < SC[8] ? 1520 : 1260;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top, display: "flex", justifyContent: "center" }}>
      <div style={{ background: "#fff", borderRadius: 22, padding: "14px 30px", transform: `scale(${0.86 + 0.14 * p}) rotate(-1.5deg)`, boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
        fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 68, color: "#111", letterSpacing: -1.5, maxWidth: 960, textAlign: "center" }}>
        {chunk.map(([s, w], k) => {
          const on = t >= s && (k + 1 >= chunk.length || t < chunk[k + 1][0] + 0.02);
          return <span key={k} style={{ marginRight: k < chunk.length - 1 ? 18 : 0, color: on || KEY.has(w) ? ACC : "#111", textDecoration: KEY.has(w) && on ? "underline" : "none" }}>{w}</span>;
        })}
      </div>
    </div>
  );
};

const Glow: React.FC<{ t: number }> = ({ t }) => (
  <AbsoluteFill style={{ background: `radial-gradient(circle at ${50 + 20 * Math.sin(t * 0.6)}% ${32 + 8 * Math.cos(t * 0.5)}%, ${ACC}55 0%, transparent 45%), radial-gradient(circle at 20% 85%, #ffffff12 0%, transparent 40%), ${BG}` }}>
    {Array.from({ length: 30 }).map((_, k) => (
      <div key={k} style={{ position: "absolute", left: `${(k * 37) % 100}%`, top: `${(110 - ((t * (12 + (k % 5) * 4) + k * 31) % 120))}%`, width: 6, height: 6, borderRadius: 3, background: ACC, opacity: 0.35, boxShadow: `0 0 12px ${ACC}` }} />
    ))}
  </AbsoluteFill>
);

const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{ background: "rgba(255,255,255,0.06)", border: "2px solid rgba(255,255,255,0.12)", borderRadius: 36, padding: 40, boxShadow: "0 30px 80px rgba(0,0,0,0.5)", fontFamily: "Inter, sans-serif", color: "#fff", ...style }}>{children}</div>
);

// ------------------------------------------------------------------ scenes (t is global time)
const Hook: React.FC<{ t: number }> = ({ t }) => {
  const k1 = pop(t, 0.05), k2 = pop(t, 1.68), stamp = pop(t, 4.12, 8);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 230, left: 0, right: 0, textAlign: "center", fontFamily: "Inter, sans-serif", color: "#fff" }}>
        <div style={{ fontSize: 46, fontWeight: 700, opacity: k1, letterSpacing: 6, color: "#f4d8c8" }}>CLAUDE KA SABSE BADA PLAN</div>
        <div style={{ fontSize: 200, fontWeight: 900, letterSpacing: -6, marginTop: 30, transform: `scale(${0.6 + 0.4 * k2})`, opacity: k2, textShadow: `0 0 60px ${ACC}aa`, color: "#fff" }}>ULTRA</div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 24, marginTop: 30, opacity: k2 }}>
          <span style={{ fontSize: 70, fontWeight: 800, color: "#bbb", textDecoration: t > 4.1 ? "line-through" : "none", textDecorationThickness: 8, textDecorationColor: "#ff4a4a" }}>$200/mo</span>
        </div>
      </div>
      {t > 4.1 ? (
        <div style={{ position: "absolute", top: 820, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <div style={{ transform: `scale(${2.2 - 1.2 * stamp}) rotate(-8deg)`, opacity: clamp(stamp * 2), border: `10px solid ${ACC}`, color: ACC, borderRadius: 26, padding: "10px 40px",
            fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 104, letterSpacing: 2, background: "rgba(0,0,0,0.35)", boxShadow: `0 0 50px ${ACC}88` }}>6 MAHINE FREE</div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const Usage: React.FC<{ t: number }> = ({ t }) => {
  const g = clamp((t - 5.55) / 0.7), x = pop(t, 8.2, 9);
  return (
    <AbsoluteFill>
      <Card style={{ position: "absolute", top: 230, left: 80, right: 80 }}>
        <div style={{ fontSize: 40, fontWeight: 700, color: "#ccc", marginBottom: 30 }}>Usage</div>
        {[{ l: "Pro", v: 0.1, c: "#7a7a86" }, { l: "Ultra", v: 0.1 + 0.9 * g, c: ACC }].map((b) => (
          <div key={b.l} style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 26 }}>
            <div style={{ width: 160, fontSize: 44, fontWeight: 800 }}>{b.l}</div>
            <div style={{ flex: 1, height: 56, background: "rgba(255,255,255,0.08)", borderRadius: 28 }}>
              <div style={{ width: `${b.v * 100}%`, height: "100%", borderRadius: 28, background: b.c, boxShadow: b.l === "Ultra" ? `0 0 30px ${ACC}` : "none" }} />
            </div>
          </div>
        ))}
        <div style={{ textAlign: "right", fontSize: 90, fontWeight: 900, color: ACC, opacity: g }}>10×</div>
      </Card>
      {/* the 5-hour limit, crossed out */}
      <div style={{ position: "absolute", top: 820, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: clamp((t - 6.7) / 0.3) }}>
        <div style={{ position: "relative", width: 300, height: 300, borderRadius: 150, border: "14px solid #fff", display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 90, color: "#fff" }}>
          5h
          <div style={{ position: "absolute", width: 360, height: 26, background: "#ff4a4a", borderRadius: 13, transform: `rotate(-40deg) scaleX(${x})`, boxShadow: "0 0 20px #ff4a4a" }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Program: React.FC<{ t: number }> = ({ t }) => {
  const k = pop(t, 8.7), k2 = pop(t, 11.6);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 210, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: k, transform: `translateY(${(1 - k) * 40}px)` }}>
        <div style={{ background: ACC, color: "#1a0e08", fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 40, padding: "10px 30px", borderRadius: 40 }}>✔ OFFICIAL PROGRAM</div>
      </div>
      <Card style={{ position: "absolute", top: 330, left: 80, right: 80, transform: `scale(${0.85 + 0.15 * k})`, opacity: k }}>
        <div style={{ fontSize: 78, fontWeight: 900, lineHeight: 1.05 }}>Claude for<br /><span style={{ color: ACC }}>Open Source</span></div>
        <div style={{ fontSize: 36, color: "#ccc", marginTop: 20 }}>maintainers & contributors ke liye</div>
      </Card>
      {/* a contribution grid: "open source pe kaam karte ho?" */}
      <div style={{ position: "absolute", top: 820, left: 110, right: 110, display: "grid", gridTemplateColumns: "repeat(14, 1fr)", gap: 8, opacity: k2 }}>
        {Array.from({ length: 70 }).map((_, i) => {
          const on = clamp((t - 11.7 - i * 0.012) / 0.2), lvl = (i * 7) % 4;
          return <div key={i} style={{ aspectRatio: "1", borderRadius: 6, background: on > 0.5 && lvl ? ["", "#5a3a2a", "#a8562e", ACC][lvl] : "rgba(255,255,255,0.07)" }} />;
        })}
      </div>
    </AbsoluteFill>
  );
};

const Form: React.FC<{ t: number }> = ({ t }) => {
  const k = pop(t, 13.4);
  const fields = [["Name", "Your Name"], ["GitHub", "github.com/you"], ["Project", "your-open-source-repo"]];
  return (
    <AbsoluteFill>
      <Card style={{ position: "absolute", top: 260, left: 110, right: 110, transform: `scale(${0.85 + 0.15 * k})`, opacity: k }}>
        <div style={{ fontSize: 50, fontWeight: 900, marginBottom: 26 }}>📝 Application form</div>
        {fields.map(([l, v], i) => {
          const n = Math.floor(clamp((t - 13.6 - i * 0.4) / 0.4) * v.length);
          return (
            <div key={l} style={{ marginBottom: 22 }}>
              <div style={{ fontSize: 28, color: "#aaa" }}>{l}</div>
              <div style={{ background: "rgba(255,255,255,0.1)", borderRadius: 14, padding: "14px 20px", fontSize: 36, minHeight: 44, fontFamily: "monospace" }}>{v.slice(0, n)}</div>
            </div>
          );
        })}
        <div style={{ marginTop: 10, background: t > 14.9 ? "#3ac06a" : ACC, borderRadius: 18, padding: "16px", textAlign: "center", fontSize: 40, fontWeight: 900 }}>{t > 14.9 ? "✔ Submitted" : "Submit"}</div>
      </Card>
    </AbsoluteFill>
  );
};

const Money: React.FC<{ t: number }> = ({ t }) => {
  const k = pop(t, 15.2), total = Math.round(interpolate(t, [18.6, 19.6], [200, 1200], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 270, left: 0, right: 0, textAlign: "center", fontFamily: "Inter, sans-serif", color: "#fff", opacity: k }}>
        <div style={{ fontSize: 44, color: "#ccc", fontWeight: 700 }}>Ultra ki keemat</div>
        <div style={{ fontSize: 150, fontWeight: 900, marginTop: 10 }}>$200<span style={{ fontSize: 60, color: "#aaa" }}>/mahina</span></div>
        <div style={{ fontSize: 80, fontWeight: 800, color: "#aaa", opacity: clamp((t - 17.6) / 0.3) }}>× 6 mahine =</div>
        <div style={{ fontSize: 190, fontWeight: 900, color: ACC, textShadow: `0 0 50px ${ACC}99`, opacity: clamp((t - 18.6) / 0.2) }}>${total.toLocaleString("en-US")}</div>
      </div>
    </AbsoluteFill>
  );
};

const Zero: React.FC<{ t: number }> = ({ t }) => {
  const s = pop(t, 20.5, 8);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ position: "absolute", top: 420, transform: `scale(${2 - s}) rotate(-6deg)`, opacity: clamp(s * 2), fontFamily: "Inter, sans-serif", textAlign: "center" }}>
        <div style={{ fontSize: 300, fontWeight: 900, color: "#3ac06a", textShadow: "0 0 60px #3ac06a88", lineHeight: 1 }}>₹0</div>
        <div style={{ fontSize: 64, fontWeight: 900, color: "#fff", marginTop: 20 }}>EK PAISA NAHI</div>
      </div>
    </AbsoluteFill>
  );
};

const Steps: React.FC<{ t: number }> = ({ t }) => {
  const items = ["Form kaise bharna hai", "Kya dhyaan rakhna hai", "Eligibility check", "Link + poori guide"];
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 220, left: 0, right: 0, textAlign: "center", color: "#fff", fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 64, opacity: pop(t, 22.1) }}>Step-by-step guide 👇</div>
      <div style={{ position: "absolute", top: 370, left: 110, right: 110 }}>
        {items.map((it, i) => {
          const k = pop(t, 22.4 + i * 1.2);
          return (
            <div key={it} style={{ display: "flex", alignItems: "center", gap: 26, marginBottom: 30, opacity: k, transform: `translateX(${(1 - k) * -80}px)` }}>
              <div style={{ width: 84, height: 84, borderRadius: 42, background: ACC, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 44, color: "#1a0e08" }}>{i + 1}</div>
              <div style={{ fontFamily: "Inter, sans-serif", fontWeight: 800, fontSize: 50, color: "#fff" }}>{it}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const CommentCTA: React.FC<{ t: number }> = ({ t }) => {
  const k = pop(t, 28.7, 9), pulse = 1 + 0.05 * Math.sin(t * 9), dm = pop(t, 30.9);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 280, left: 0, right: 0, textAlign: "center", fontFamily: "Inter, sans-serif" }}>
        <div style={{ fontSize: 64, fontWeight: 900, color: "#fff", opacity: k }}>Comment karo 👇</div>
        <div style={{ display: "inline-block", marginTop: 30, background: ACC, color: "#1a0e08", fontWeight: 900, fontSize: 130, padding: "18px 56px", borderRadius: 34,
          transform: `scale(${(0.6 + 0.4 * k) * pulse})`, boxShadow: `0 0 70px ${ACC}` }}>“CLAUDE”</div>
        <div style={{ marginTop: 70, display: "inline-flex", alignItems: "center", gap: 20, background: "rgba(255,255,255,0.1)", borderRadius: 30, padding: "20px 34px", opacity: dm, transform: `translateY(${(1 - dm) * 40}px)` }}>
          <span style={{ fontSize: 56 }}>📩</span><span style={{ fontSize: 46, fontWeight: 800, color: "#fff" }}>Seedha DM mein link</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const FollowCTA: React.FC<{ t: number }> = ({ t }) => {
  const k = pop(t, 32.3, 9), on = t > 33.4;
  return (
    <AbsoluteFill>
      {Array.from({ length: 14 }).map((_, i) => (
        <div key={i} style={{ position: "absolute", left: `${(i * 23) % 92}%`, top: `${-10 + ((t - 31.9) * (22 + (i % 4) * 8) + i * 9) % 90}%`, fontSize: 64, transform: `rotate(${t * 40 + i * 30}deg)` }}>🎁</div>
      ))}
      <div style={{ position: "absolute", top: 520, left: 0, right: 0, textAlign: "center", fontFamily: "Inter, sans-serif" }}>
        <div style={{ fontSize: 60, fontWeight: 900, color: "#fff", opacity: k }}>Free AI offers miss na ho</div>
        <div style={{ display: "inline-block", marginTop: 40, border: "6px solid #fff", borderRadius: 30, padding: "22px 80px", fontWeight: 900, fontSize: 80,
          background: on ? "#fff" : "transparent", color: on ? "#111" : "#fff", transform: `scale(${0.7 + 0.3 * k})` }}>{on ? "Following ✓" : "+ Follow"}</div>
      </div>
    </AbsoluteFill>
  );
};

export const UltraFree: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  let flash = 0; for (const c of SC.slice(1, -1)) flash = Math.max(flash, 1 - Math.abs(t - c) / 0.07);
  const scene = SC.filter((s) => t >= s).length - 1;
  const Scenes = [Hook, Usage, Program, Form, Money, Zero, Steps, CommentCTA, FollowCTA];
  const S = Scenes[Math.min(scene, Scenes.length - 1)];
  const showNote = (t >= SC[2] && t < SC[5]) || t >= SC[7];
  return (
    <AbsoluteFill style={{ background: BG }}>
      <Audio src={staticFile("vo.mp3")} />
      {SC.slice(1, -1).map((c, i) => <Sequence key={i} from={Math.max(0, Math.round((c - 0.2) * FPS))} durationInFrames={20}><Audio src={staticFile("whoosh-fast.wav")} volume={0.3} /></Sequence>)}
      {[4.12, 20.45, 28.68].map((c, i) => <Sequence key={"b" + i} from={Math.round(c * FPS)} durationInFrames={40}><Audio src={staticFile("boom-hit.wav")} volume={0.35} /></Sequence>)}
      {[14.9, 33.4].map((c, i) => <Sequence key={"d" + i} from={Math.round(c * FPS)} durationInFrames={40}><Audio src={staticFile("ding.wav")} volume={0.35} /></Sequence>)}
      {[1.7, 5.6, 8.2, 11.7, 18.9].map((c, i) => <Sequence key={"p" + i} from={Math.round(c * FPS)} durationInFrames={20}><Audio src={staticFile("pop.wav")} volume={0.3} /></Sequence>)}
      <Glow t={t} />
      <S t={t} />
      {showNote ? (
        <div style={{ position: "absolute", top: 1180, left: 60, right: 60, textAlign: "center", fontFamily: "Inter, sans-serif", fontSize: 26, color: "rgba(255,255,255,0.75)" }}>
          *Sirf eligible open-source maintainers / contributors ke liye · seats limited · terms: claude.com
        </div>
      ) : null}
      <Captions t={t} />
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash * 0.35, pointerEvents: "none" }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: interpolate(t, [0, 0.2, 35.9, 36.45], [1, 0, 0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
