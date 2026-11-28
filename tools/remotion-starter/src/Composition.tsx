import { AbsoluteFill, Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// Starter composition for vertical reels (1080x1920, 30 fps). Copy this project
// into projects/<name>/ to start a new Remotion-based edit.
export const MyComposition = () => {
  return (
    <Composition
      id="ReelTest"
      component={ReelTest}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};

export const ReelTest: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 12 } });
  const fade = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(#0a0e1e, #1e2846)",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "'Noto Serif Devanagari', 'Noto Sans', sans-serif",
        color: "white",
      }}
    >
      <div style={{ fontSize: 110, fontWeight: 700, transform: `scale(${pop})` }}>Remotion ✓</div>
      <div style={{ fontSize: 72, marginTop: 40, opacity: fade, color: "#ffd27a" }}>
        हम भी अपने शहजादे हैं
      </div>
    </AbsoluteFill>
  );
};
