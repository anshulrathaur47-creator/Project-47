import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { G, Look, Person, Pose, Toon, restPose } from "./Character";
import { rng, skyMat } from "./World";

// "जिस मगरमच्छ को बंदर ने…" (ReelAudio-38695): the monkey-and-crocodile tale told from the crocodile's side.
export const DURATION = 3343; // 111.43 s
const FPS = 30;
const END = DURATION / FPS;
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (x: number) => { const t = clamp(x); return t * t * (3 - 2 * t); };
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: number[], b: number[], t: number) => a.map((v, i) => lerp(v, b[i], t)) as [number, number, number];
const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

// narration subtitles (Whisper, with chunked passes for the parts VAD dropped)
const SUBS: [number, number, string][] = [
  [0.0, 4.18, "जिस मगरमच्छ को बंदर ने “मेरा दिल तो पेड़ पर छूट गया”"],
  [4.18, 7.56, "कहकर बेवकूफ़ बनाया, वो बेवकूफ़ बना ही नहीं था।"],
  [7.56, 9.96, "उसकी बीवी तीन दिन से बिस्तर पर थी।"],
  [9.96, 13.38, "बचाने का एक ही रास्ता था… बंदर का दिल।"],
  [13.38, 16.3, "मगरमच्छ की नज़र जामुन के उस पेड़ की तरफ़ गई,"],
  [16.3, 18.7, "जहाँ पाँच साल से उसका दोस्त बैठता था।"],
  [18.7, 21.06, "वो पूरी रात किनारे पर बैठा रहा।"],
  [21.06, 24.44, "एक तरफ़ उसकी बीवी, जिसकी साँसें धीमी पड़ रही थीं।"],
  [24.44, 27.76, "दूसरी तरफ़ उसका सबसे अच्छा दोस्त, बंदर।"],
  [27.76, 30.8, "बंदर हँसता हुआ आया, “आज उदास क्यों है दोस्त?”"],
  [30.8, 33.9, "मगरमच्छ बोला, “चल, तुझे भाभी से मिलवाता हूँ।”"],
  [33.9, 35.4, "बंदर उसकी पीठ पर बैठ गया।"],
  [35.4, 39.08, "पर सोचो, बीच नदी में पहुँचकर उसने सच क्यों बताया?"],
  [39.08, 42.6, "क्योंकि वो बंदर को मारना नहीं चाहता था। वो उसका दोस्त था।"],
  [42.6, 46.2, "वो बस इतना चाहता था कि दोस्त खुद कोई बहाना ढूँढ ले,"],
  [46.2, 49.4, "ताकि ये फ़ैसला उसे अपने हाथों से ना लेना पड़े।"],
  [49.4, 53.76, "धीमी आवाज़ में बोला, “दोस्त, मेरी बीवी को तेरा दिल चाहिए।”"],
  [53.76, 56.7, "बंदर की साँस रुक गई। फिर काँपती हँसी में बोला,"],
  [56.7, 61.7, "“अरे पागल, पहले बताता! मेरा दिल तो पेड़ पर टँगा है। चल, वापस चलते हैं।”"],
  [61.7, 64.6, "मगरमच्छ जानता था कि दिल सीने में होता है।"],
  [64.6, 67.56, "उसे अपनी पीठ पर उसकी धड़कन महसूस हो रही थी।"],
  [67.6, 70.36, "फिर भी वो चुपचाप किनारे की तरफ़ मुड़ गया।"],
  [70.4, 74.74, "बंदर पेड़ पर चढ़ते ही हँसा, “मूर्ख, कहीं दिल भी पेड़ पर होता है?”"],
  [74.74, 76.26, "पूरा किनारा हँस पड़ा।"],
  [76.26, 81.38, "मगरमच्छ ने एक बार ऊपर देखा, कुछ कहना चाहा, पर बिना बोले पानी में उतर गया।"],
  [81.38, 85.92, "पूरा दिन वो बीवी के पास बैठा रहा। फिर रात को उसकी साँसें थम गईं।"],
  [85.92, 88.62, "वो उसका ठंडा हाथ थामे रोते हुए बोला,"],
  [88.62, 91.88, "“तू कहती थी, मेरा पति किसी का बुरा नहीं कर सकता।"],
  [91.88, 95.64, "आज तुझे खोकर भी मैं वही निकला। मुझे माफ़ कर देना।”"],
  [95.64, 98.72, "हर बार बेवकूफ़ बनने वाला बेवकूफ़ नहीं होता।"],
  [98.72, 104.06, "कुछ लोग हारना खुद चुनते हैं, क्योंकि उनके लिए जीत की कीमत उनका ज़मीर होती है।"],
  [104.06, 107.26, "अगली बार किसी को सीधा कहकर हँसने से पहले सोचना,"],
  [107.26, 111.3, "कहीं उसने हार इसलिए तो नहीं चुनी कि तुम्हें बचाना ज़्यादा ज़रूरी था?"],
];
// scene boundaries
const S = { den: 7.56, heart: 9.96, look: 13.38, flash: 14.9, night: 18.7, morning: 27.76, ride: 33.9, mid: 35.4, tell: 49.4, shock: 53.76, beat: 61.7, turn: 67.6,
  laugh: 70.4, sink: 76.26, day: 81.38, cry: 85.92, moral: 95.64 };

// ------------------------------------------------------------------ places
const TREE = V(-0.6, 0, -5.2);        // jamun tree on the north bank
const DEN = V(2.4, 0, 4.6);           // the couple's den on the south bank
const BANK_N = -3.4, BANK_S = 3.4;

// ------------------------------------------------------------------ the crocodile
type CrocPose = { walk: number; phase: number; jaw: number; eyes: number; brow: number; tear: number; lookX: number; headYaw: number; headPitch: number; swim: number };
const crocRest = (): CrocPose => ({ walk: 0, phase: 0, jaw: 0, eyes: 1, brow: 0, tear: -1, lookX: 0, headYaw: 0, headPitch: 0, swim: 0 });

const Croc: React.FC<{ p: CrocPose; color?: string; belly?: string; flower?: boolean; t: number }> = ({ p, color = "#4f7a3a", belly = "#b8c27a", flower, t }) => {
  const dark = new THREE.Color(color).multiplyScalar(0.7).getStyle();
  const tailSway = (k: number) => Math.sin(t * (p.swim > 0 ? 3.5 : 1.2) - k * 0.7) * (0.12 + 0.18 * p.swim) * (k / 6);
  return (
    <group>
      <Toon geom={G.sphere} color={color} position={[0, 0.12, 0]} scale={[0.46, 0.26, 1.1]} outline={0.006} />
      <Toon geom={G.sphere} color={belly} position={[0, 0.02, 0.05]} scale={[0.4, 0.15, 0.95]} outline={0} />
      {Array.from({ length: 9 }).map((_, k) => (
        <Toon key={k} geom={G.sphere} color={dark} position={[(k % 2 ? 0.1 : -0.1), 0.36, 0.8 - k * 0.2]} scale={[0.05, 0.05, 0.07]} outline={0.005} />
      ))}
      {/* tail */}
      {Array.from({ length: 6 }).map((_, k) => {
        let x = 0; for (let j = 0; j <= k; j++) x += tailSway(j);
        return <Toon key={k} geom={G.sphere} color={color} position={[x, 0.1 - k * 0.012, -1.0 - k * 0.27]} scale={[0.3 - k * 0.045, 0.18 - k * 0.022, 0.22]} outline={0.006} />;
      })}
      {/* legs */}
      {[[-1, 1], [1, 1], [-1, -1], [1, -1]].map(([sx, sz], k) => {
        const sw = Math.sin(p.phase + k * Math.PI / 2) * 0.5 * Math.max(p.walk, p.swim * 0.6);
        return (
          <group key={k} position={[sx * 0.38, 0.0, sz * 0.55]} rotation={[sw, 0, sx * 0.9]}>
            <Toon geom={G.capsule} color={color} position={[0, -0.12, 0]} scale={[0.07, 0.07, 0.07]} outline={0.006} />
            <Toon geom={G.sphere} color={dark} position={[0, -0.24, 0.04]} scale={[0.08, 0.03, 0.1]} outline={0.004} />
          </group>
        );
      })}
      {/* head */}
      <group position={[0, 0.16, 1.02]} rotation={[p.headPitch, p.headYaw, 0]}>
        <Toon geom={G.sphere} color={color} position={[0, 0.03, 0.05]} scale={[0.3, 0.17, 0.3]} outline={0.006} />
        <Toon geom={G.sphere} color={color} position={[0, 0.04, 0.48]} scale={[0.22, 0.1, 0.48]} outline={0.006} />
        {[-1, 1].map((s) => <mesh key={s} position={[s * 0.06, 0.12, 0.9]} scale={0.022}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#1a1a12" /></mesh>)}
        {/* teeth along the upper jaw */}
        {[-1, 1].map((s) => Array.from({ length: 6 }).map((_, k) => (
          <mesh key={`${s}${k}`} position={[s * (0.19 - k * 0.01), -0.035, 0.2 + k * 0.12]} rotation={[Math.PI, 0, 0]} scale={[0.018, 0.04, 0.018]}><coneGeometry args={[1, 1, 5]} /><meshBasicMaterial color="#f4f0e0" /></mesh>
        )))}
        {/* lower jaw */}
        <group position={[0, -0.04, 0.05]} rotation={[p.jaw * 0.45, 0, 0]}>
          <Toon geom={G.sphere} color={belly} position={[0, -0.03, 0.4]} scale={[0.2, 0.06, 0.45]} outline={0.006} />
          {p.jaw > 0.1 ? <mesh position={[0, 0.0, 0.35]} rotation={[-Math.PI / 2, 0, 0]} scale={[0.16, 0.36, 1]}><circleGeometry args={[1, 16]} /><meshBasicMaterial color="#a83a3a" /></mesh> : null}
        </group>
        {/* eyes on top, with lids, brows and tears */}
        {[-1, 1].map((s) => (
          <group key={s} position={[s * 0.13, 0.19, 0.08]}>
            <Toon geom={G.sphere} color={color} scale={[0.1, 0.08, 0.1]} outline={0.006} />
            <mesh position={[0, 0.03, 0.05]} scale={[0.075, 0.075 * Math.max(0.1, p.eyes), 0.06]}><sphereGeometry args={[1, 14, 12]} /><meshBasicMaterial color="#f6f2dc" /></mesh>
            {p.eyes > 0.15 ? (
              <>
                <mesh position={[p.lookX * 0.02, 0.03, 0.105]} scale={[0.035, 0.05 * Math.min(1, p.eyes), 0.02]}><sphereGeometry args={[1, 10, 8]} /><meshBasicMaterial color="#1a1208" /></mesh>
                <mesh position={[p.lookX * 0.02 - 0.012, 0.05, 0.12]} scale={0.009}><sphereGeometry args={[1, 6, 6]} /><meshBasicMaterial color="#ffffff" /></mesh>
              </>
            ) : <mesh position={[0, 0.03, 0.11]} rotation={[0, 0, Math.PI]} scale={[0.05, 0.03, 0.02]}><torusGeometry args={[1, 0.25, 6, 14, Math.PI]} /><meshBasicMaterial color="#1a1208" /></mesh>}
            <mesh position={[0, 0.115 + p.brow * 0.012, 0.07]} rotation={[0, 0, -s * (0.05 + p.brow * 0.5)]} scale={[0.09, 0.016, 0.02]}><boxGeometry /><meshBasicMaterial color="#2a3a1a" /></mesh>
            {p.tear >= 0 ? <mesh position={[s * 0.05, 0.0 - p.tear * 0.18, 0.1]} scale={0.02}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#9fd0ff" transparent opacity={0.9} /></mesh> : null}
          </group>
        ))}
        {flower ? (
          <group position={[0.14, 0.32, 0.04]} rotation={[0.3, 0, 0.3]}>
            {Array.from({ length: 5 }).map((_, k) => <mesh key={k} position={[Math.cos(k * 1.256) * 0.04, Math.sin(k * 1.256) * 0.04, 0]} scale={[0.035, 0.025, 0.01]}><sphereGeometry args={[1, 8, 6]} /><meshToonMaterial color="#ff8ab0" /></mesh>)}
            <mesh scale={0.02}><sphereGeometry args={[1, 8, 6]} /><meshToonMaterial color="#ffd040" /></mesh>
          </group>
        ) : null}
      </group>
    </group>
  );
};

// ------------------------------------------------------------------ the monkey
const MONKEY: Look = { skin: "#e2b48a", hair: "#7a4a28", hairStyle: "monkey", shirt: "#7a4a28", inner: "#d8a878", pants: "#7a4a28", shoes: "#5a341c", face: true, tail: "#7a4a28", muzzle: "#e2b48a" };
const MONKEY_FRIENDS: Look[] = [{ ...MONKEY, hair: "#8a5a34", shirt: "#8a5a34", pants: "#8a5a34", tail: "#8a5a34" }, { ...MONKEY, hair: "#5a3a20", shirt: "#5a3a20", pants: "#5a3a20", tail: "#5a3a20" }];

// ------------------------------------------------------------------ world
const Water: React.FC<{ t: number; night: number }> = ({ t, night }) => {
  const glints = useMemo(() => { const r = rng(12); return Array.from({ length: 90 }, () => ({ x: -12 + r() * 24, z: BANK_N + r() * (BANK_S - BANK_N), ph: r() * 6 })); }, []);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[40, BANK_S - BANK_N + 0.4]} />
        <meshStandardMaterial color={new THREE.Color("#3a7a8a").lerp(new THREE.Color("#0c1a2a"), night)} roughness={0.25} metalness={0.35} transparent opacity={0.92} />
      </mesh>
      {glints.map((g, k) => {
        const a = 0.5 + 0.5 * Math.sin(t * 2 + g.ph);
        return <mesh key={k} rotation={[-Math.PI / 2, 0, 0]} position={[((g.x + t * 0.3 + 12) % 24) - 12, 0.0, g.z]} scale={[0.25 * a, 0.03, 1]}><planeGeometry /><meshBasicMaterial color={night > 0.5 ? "#8aa8d8" : "#e8f6ff"} transparent opacity={0.5 * a} /></mesh>;
      })}
    </group>
  );
};

const Banks: React.FC = () => {
  const reeds = useMemo(() => { const r = rng(3); return Array.from({ length: 70 }, () => ({ x: -10 + r() * 20, side: r() < 0.5 ? -1 : 1, h: 0.4 + r() * 0.6, d: r() * 0.4 })); }, []);
  return (
    <group>
      {[[-1, BANK_N - 4], [1, BANK_S + 4]].map(([s, z]) => (
        <mesh key={s} position={[0, -0.1, z]} receiveShadow><boxGeometry args={[40, 0.4, 8]} /><meshToonMaterial color={s < 0 ? "#6a8a3a" : "#7a8a44"} /></mesh>
      ))}
      {reeds.map((r, k) => (
        <mesh key={k} position={[r.x, r.h / 2, r.side < 0 ? BANK_N - 0.1 - r.d : BANK_S + 0.1 + r.d]} rotation={[0, 0, 0.1 * Math.sin(k)]}>
          <cylinderGeometry args={[0.012, 0.02, r.h, 4]} /><meshToonMaterial color="#5a7a2a" />
        </mesh>
      ))}
    </group>
  );
};

const JamunTree: React.FC<{ t: number }> = ({ t }) => {
  const fruit = useMemo(() => { const r = rng(8); return Array.from({ length: 50 }, () => ({ x: (r() - 0.5) * 2.6, y: 2.6 + r() * 1.4, z: (r() - 0.5) * 1.6 })); }, []);
  return (
    <group position={TREE}>
      <mesh position={[0, 1.4, 0]} castShadow><cylinderGeometry args={[0.22, 0.34, 2.8, 12]} /><meshToonMaterial color="#5a3a24" /></mesh>
      <mesh position={[0.5, 2.3, 0.3]} rotation={[0, 0, -0.9]}><cylinderGeometry args={[0.09, 0.12, 1.4, 8]} /><meshToonMaterial color="#5a3a24" /></mesh>
      <mesh position={[-0.55, 2.5, 0.1]} rotation={[0, 0, 0.9]}><cylinderGeometry args={[0.08, 0.11, 1.3, 8]} /><meshToonMaterial color="#5a3a24" /></mesh>
      {[[0, 3.4, 0, 1.4], [1.0, 3.0, 0.3, 1.0], [-1.0, 3.1, 0.2, 1.05], [0.2, 4.1, -0.3, 1.0], [0.3, 3.2, 0.9, 0.9]].map(([x, y, z, r], k) => (
        <Toon key={k} geom={G.sphere} color={k % 2 ? "#2f5a2a" : "#3a6a30"} position={[x, y + 0.03 * Math.sin(t + k), z]} scale={r} outline={0.005} />
      ))}
      {fruit.map((f, k) => <mesh key={k} position={[f.x, f.y, f.z + 0.95]} scale={0.06}><sphereGeometry args={[1, 8, 6]} /><meshToonMaterial color="#4a1a5a" /></mesh>)}
    </group>
  );
};

const Den: React.FC<{ t: number; glow: number }> = ({ t, glow }) => (
  <group position={DEN}>
    {[[-1.3, 0.35, -0.9, 0.55], [1.3, 0.4, -1.0, 0.6], [0, 0.7, -1.5, 0.8], [-0.7, 0.6, -1.4, 0.6], [0.7, 0.65, -1.45, 0.6]].map(([x, y, z, r], k) => (
      <Toon key={k} geom={G.sphere} color={k % 2 ? "#6a6058" : "#7a6e62"} position={[x, y, z]} scale={[r, r * 0.85, r]} outline={0.005} />
    ))}
    {/* bed of leaves */}
    <mesh position={[0, 0.06, 0.2]} rotation={[-Math.PI / 2, 0, 0]} scale={[1.1, 0.7, 1]}><circleGeometry args={[1, 20]} /><meshToonMaterial color="#8a7a3a" /></mesh>
    {/* fireflies */}
    {Array.from({ length: 12 }).map((_, k) => (
      <mesh key={k} position={[Math.sin(t * 0.7 + k) * 1.3, 0.8 + 0.4 * Math.sin(t * 1.1 + k * 2), 0.6 + Math.cos(t * 0.5 + k) * 0.6]} scale={0.02}>
        <sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color="#e8ff8a" transparent opacity={glow * (0.5 + 0.5 * Math.sin(t * 5 + k))} />
      </mesh>
    ))}
    <pointLight position={[0, 0.8, 0.8]} color="#d8ff9a" intensity={1.4 * glow} distance={3.5} />
  </group>
);

// ------------------------------------------------------------------ who is where
const CROC_S = 0.62, WIFE_S = 0.55, MONK_S = 0.58;
type Placed = { pos: [number, number, number]; yaw: number };

function crocAt(t: number): Placed & { p: CrocPose } {
  const p = crocRest();
  p.brow = 0.6; p.eyes = 0.8;
  if (t < S.den) {   // the famous moment: in the water under the tree, looking up at the laughing monkey
    p.headPitch = -0.35; p.brow = 0.8; p.eyes = 0.75; p.swim = 0.2; p.phase = t * 3;
    return { pos: [0.2, -0.08, BANK_N + 1.5], yaw: Math.PI, p };
  }
  if (t < S.look) {  // beside his sick wife in the den
    p.headYaw = -0.4; p.brow = 0.9; p.eyes = 0.7;
    return { pos: [DEN.x - 0.55, 0.02, DEN.z + 1.15], yaw: 2.62, p };
  }
  if (t < S.night) { // looks across the river to the tree (then a warm flashback)
    p.headPitch = -0.1; p.brow = 0.7; p.eyes = 0.9;
    if (t >= S.flash) { p.jaw = 0.5 + 0.2 * Math.sin(t * 8); p.eyes = 0.2; p.brow = -0.2; }   // laughing with his friend, long ago
    return t >= S.flash ? { pos: [TREE.x + 1.5, 0.05, BANK_N - 0.6], yaw: -2.4, p } : { pos: [0.8, 0.02, BANK_S + 0.4], yaw: Math.PI, p };
  }
  if (t < S.morning) {  // all night on the bank, between wife and friend
    p.brow = 0.9; p.eyes = 0.6 + 0.3 * Math.sin(t * 0.8); p.headYaw = 0.5 * Math.sin((t - S.night) * 0.6);
    return { pos: [0.6, 0.02, BANK_S + 0.3], yaw: Math.PI, p };
  }
  if (t < S.ride) {     // morning: waits at the north bank; the monkey comes down
    p.brow = 0.8; p.eyes = 0.8; p.headPitch = -0.15; p.swim = 0.15; p.phase = t * 2;
    if (t > S.morning + 3.1) { p.jaw = 0.25 * Math.abs(Math.sin(t * 9)); }   // "चल, भाभी से मिलवाता हूँ"
    return { pos: [-0.2, -0.08, BANK_N + 0.9], yaw: Math.PI * 0.5, p };
  }
  // the ride: from the north bank out to mid-river, the truth, the turn, and back
  p.swim = 1; p.phase = t * 3.5;
  let z: number, yaw = 0;
  if (t < S.mid) z = lerp(BANK_N + 0.9, BANK_N + 2.0, seg(t, S.ride, S.mid));
  else if (t < S.tell) z = lerp(BANK_N + 2.0, 0.4, seg(t, S.mid, S.tell - 2));
  else if (t < S.turn) { z = 0.4; p.swim = 0.25; }
  else if (t < S.laugh) { z = 0.4; yaw = lerp(0, Math.PI, seg(t, S.turn, S.turn + 2.4)); p.swim = 0.5; }
  else if (t < S.sink) { z = lerp(0.4, BANK_N + 0.9, seg(t, S.laugh, S.laugh + 2.0)); yaw = Math.PI; }
  else if (t < S.day) { z = BANK_N + 0.9; yaw = Math.PI; p.swim = 0.2; }
  else z = 0;
  if (t >= S.mid && t < S.tell) { p.brow = 1; p.eyes = 0.7; p.lookX = -0.5; }
  if (t >= S.tell && t < S.shock) { p.jaw = 0.18 * Math.abs(Math.sin(t * 7)); p.eyes = 0.5; p.brow = 1; }   // "दोस्त, मेरी बीवी को तेरा दिल चाहिए"
  if (t >= S.beat && t < S.turn) { p.eyes = 0.15; p.brow = 1; p.tear = clamp((t - S.beat - 1) / 2); }      // he feels the heartbeat on his back
  if (t >= S.laugh && t < S.sink) { p.headPitch = -0.4; p.eyes = 0.9; p.brow = 1; }
  if (t >= S.sink && t < S.day) { p.headPitch = -0.45; p.jaw = t < S.sink + 2.2 ? 0.35 * seg(t, S.sink + 0.8, S.sink + 1.4) * (1 - seg(t, S.sink + 1.8, S.sink + 2.3)) : 0; p.eyes = 0.8; p.brow = 1; }
  if (t >= S.day) {   // back at the den with her
    p.swim = 0; p.brow = 1; p.eyes = t < S.cry ? 0.6 : 0.1; p.headPitch = 0.25; p.tear = t > S.cry ? ((t - S.cry) % 1.6) / 1.6 : -1;
    if (t > S.cry && t < S.moral && Math.sin(t * 2.5) > 0) p.jaw = 0.2;
    return { pos: [DEN.x - 0.55, 0.02, DEN.z + 1.15], yaw: 2.62, p };
  }
  const sinkY = t >= S.sink && t < S.day ? -0.08 - 0.5 * seg(t, S.sink + 3.2, S.day - 0.4) : -0.1;
  return { pos: [-0.2, sinkY, z], yaw, p };
}

function wifeAt(t: number): { p: CrocPose; breath: number } {
  const p = crocRest();
  p.eyes = 0.35; p.brow = 0.6; p.headPitch = 0.1;
  let breath = 0.02 * Math.sin(t * 1.6);
  if (t > S.night && t < S.morning) breath = 0.012 * Math.sin(t * 0.9);
  if (t > S.day + 2.2) { p.eyes = lerp(0.35, 0, seg(t, S.day + 2.4, S.day + 3.6)); breath = 0.01 * Math.sin(t * 0.7) * (1 - seg(t, S.day + 3, S.day + 4.3)); }
  return { p, breath };
}

function monkeyAt(t: number, croc: Placed): (Placed & { pose: Pose; heart: number; s?: number }) | null {
  const p = restPose();
  p.smile = 0.8; p.blush = 0.5;
  const treeTop: [number, number, number] = [TREE.x + 0.75, 2.0, TREE.z + 0.75];
  if (t < S.den) {   // on the branch, laughing at the crocodile
    p.sit = 1; p.armR = [-1.6, -0.4]; p.elbowR = -0.2; p.armL = [-0.6, 0.6]; p.elbowL = -1.5; p.happyEyes = true; p.eyes = Math.sin(t * 11) > -0.2 ? 0 : 1; p.smile = 1; p.headPitch = 0.3 + 0.12 * Math.sin(t * 13);
    return { pos: [treeTop[0], treeTop[1] - 0.25, treeTop[2]], yaw: 0.2, pose: p, heart: 0 };
  }
  if (t >= S.flash && t < S.night) {   // flashback: sharing jamuns with his friend
    p.sit = 1; p.armR = [-1.3, -0.2]; p.elbowR = -0.4; p.happyEyes = true; p.eyes = 0; p.smile = 1; p.headPitch = -0.1;
    return { pos: [TREE.x + 0.5, 0.0, BANK_N - 1.0], yaw: 0.9, pose: p, heart: 0 };
  }
  if (t >= S.night && t < S.morning) {   // asleep on the branch
    p.sit = 1; p.eyes = 0; p.smile = 0.3; p.headRoll = 0.4; p.headPitch = 0.3; p.armL = [-0.7, 0.4]; p.armR = [-0.7, -0.4]; p.elbowL = -1.6; p.elbowR = -1.6;
    return { pos: [treeTop[0], treeTop[1] - 0.25, treeTop[2]], yaw: 0.2, pose: p, heart: 0 };
  }
  if (t >= S.morning && t < S.ride) {   // swings down, laughing, hops on
    const k = seg(t, S.morning, S.morning + 2.0);
    p.armR = [-2.8 * (1 - k), -0.3]; p.armL = [-2.8 * (1 - k), 0.3]; p.smile = 1; p.headPitch = -0.1;
    if (t > S.morning + 2.0) { p.armR = [-0.4, -0.2]; p.headYaw = 0.3 * Math.sin(t * 3); }
    return { pos: [lerp(treeTop[0], -0.3, k), lerp(treeTop[1], 0.15, k), lerp(treeTop[2], BANK_N - 0.3, k)], yaw: -0.3, pose: p, heart: 0 };
  }
  if (t >= S.ride && t < S.laugh + 1.5) {   // on the crocodile's back
    p.sit = 1; p.armL = [-0.6, 0.4]; p.armR = [-0.6, -0.4]; p.elbowL = -0.6; p.elbowR = -0.6;
    p.smile = 0.8; p.headYaw = 0.4 * Math.sin(t * 0.8);
    if (t >= S.tell) { p.smile = 0; p.eyes = 1.3; p.mouthO = 1; p.brow = -0.4; p.headYaw = 0; p.headPitch = 0.3; }   // the truth
    if (t >= S.shock + 1.4) { p.mouthO = 0; p.smile = 0.6 + 0.2 * Math.sin(t * 20); p.eyes = 1.1; p.brow = 0.5; p.armR = [-1.4, -0.5]; p.elbowR = -0.6 + 0.3 * Math.sin(t * 10); }   // a shaky laugh
    if (t >= S.beat) { p.smile = 0.2; p.eyes = 1.0; p.brow = 0.6; p.headYaw = -0.4; }
    let heart = 0;
    if (t >= S.beat - 0.5 && t < S.turn + 1) heart = 1;
    if (t >= S.laugh) {   // jumps off and climbs
      const k = seg(t, S.laugh, S.laugh + 1.4);
      return { pos: [lerp(croc.pos[0], treeTop[0], k), lerp(0.3, treeTop[1] - 0.25, k), lerp(croc.pos[2], treeTop[2], k)], yaw: 0.2, pose: p, heart: 0 };
    }
    const fwd = V(Math.sin(croc.yaw), 0, Math.cos(croc.yaw));
    const back = V(croc.pos[0], croc.pos[1] + 0.36 * CROC_S, croc.pos[2]).addScaledVector(fwd, 0.1 * CROC_S);
    return { pos: [back.x, back.y - 0.41 * MONK_S + 0.02, back.z], yaw: croc.yaw, pose: p, heart };
  }
  if (t >= S.laugh + 1.5 && t < S.day) {   // back up the tree, laughing down at him
    p.sit = 1; p.armR = [-1.5, -0.3]; p.elbowR = -0.1; p.happyEyes = true; p.eyes = Math.sin(t * 11) > -0.2 ? 0 : 1; p.smile = 1; p.headPitch = 0.35 + 0.1 * Math.sin(t * 12);
    if (t > S.sink + 1) { p.happyEyes = false; p.eyes = 1; p.smile = lerp(1, 0, seg(t, S.sink + 1, S.sink + 2.5)); p.brow = lerp(0, 0.6, seg(t, S.sink + 2, S.sink + 3.5)); }
    return { pos: [treeTop[0], treeTop[1] - 0.25, treeTop[2]], yaw: 0.2, pose: p, heart: 0 };
  }
  if (t >= S.moral) {   // at dawn, alone on the branch, looking down, quiet
    p.sit = 1; p.smile = -0.2; p.brow = 0.9; p.eyes = 0.6; p.headPitch = 0.45; p.armL = [-0.7, 0.4]; p.armR = [-0.7, -0.4]; p.elbowL = -1.4; p.elbowR = -1.4;
    return { pos: [treeTop[0], treeTop[1] - 0.25, treeTop[2]], yaw: 0.2, pose: p, heart: 0 };
  }
  return null;
}

// ------------------------------------------------------------------ signs
const heartGeo = (() => {
  const s = new THREE.Shape();
  s.moveTo(0, -0.3); s.bezierCurveTo(-0.6, 0.1, -0.35, 0.55, 0, 0.25); s.bezierCurveTo(0.35, 0.55, 0.6, 0.1, 0, -0.3);
  return new THREE.ExtrudeGeometry(s, { depth: 0.08, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 });
})();
const Heart: React.FC<{ pos: [number, number, number]; s: number; color?: string; light?: number; yaw?: number }> = ({ pos, s, color = "#ff3a5a", light = 1.2, yaw = 0 }) => (
  <group position={pos} rotation={[0, yaw, Math.PI]} scale={s}>
    <mesh geometry={heartGeo}><meshBasicMaterial color={color} /></mesh>
    <pointLight color={color} intensity={light} distance={2} />
  </group>
);

// ------------------------------------------------------------------ camera
type Cam = { pos: [number, number, number]; target: [number, number, number]; fov: number; roll?: number };
function camAt(t: number, c: Placed): Cam {
  if (t < S.den) {   // crane down from the laughing monkey to the croc in the water
    const k = Easing.inOut(Easing.cubic)(clamp(t / S.den));
    return { pos: lerp3([2.0, 2.4, -0.6], [1.4, 0.7, -0.2], k), target: lerp3([TREE.x + 0.75, 1.9, TREE.z + 0.75], [0.2, 0.3, BANK_N + 1.5], k), fov: 46 };
  }
  if (t < S.heart) return { pos: [DEN.x + 1.1, 0.5, DEN.z + 2.3], target: [DEN.x - 0.3, 0.25, DEN.z + 0.8], fov: 40 };
  if (t < S.look) { const k = (t - S.heart) / (S.look - S.heart); return { pos: [DEN.x + 1.3, 0.6, DEN.z + 2.5], target: lerp3([DEN.x - 0.3, 0.3, DEN.z + 0.7], [DEN.x, 0.9, DEN.z + 0.3], k), fov: 42 }; }
  if (t < S.flash) return { pos: [1.4, 0.55, BANK_S + 1.6], target: [TREE.x, 2.0, TREE.z], fov: 30 };                 // his gaze across the river
  if (t < S.night) { const k = (t - S.flash) / (S.night - S.flash); return { pos: lerp3([TREE.x + 2.6, 1.0, BANK_N + 1.6], [TREE.x + 2.2, 0.9, BANK_N + 1.2], k), target: [TREE.x + 1.0, 0.4, BANK_N - 0.8], fov: 40 }; }
  if (t < S.morning) { const k = (t - S.night) / (S.morning - S.night);   // behind him on the bank: den on one side, tree on the other
    return { pos: lerp3([0.6, 1.6, BANK_S + 3.4], [0.6, 1.3, BANK_S + 2.2], k), target: [0.3, 0.8, -1.5], fov: lerp(56, 48, k) }; }
  if (t < S.ride) return { pos: [1.8, 1.0, BANK_N + 2.6], target: [-0.3, 0.6, BANK_N + 0.2], fov: 42 };
  if (t < S.mid) return { pos: [3.5, 3.5, 2.0], target: [c.pos[0], 0, c.pos[2]], fov: 44 };                           // aerial: out onto the river
  if (t < S.tell) { const k = (t - S.mid) / (S.tell - S.mid);   // slow orbit round them mid-river; his troubled eyes
    const a = lerp(0.6, 2.0, k); return { pos: [c.pos[0] + 2.0 * Math.sin(a), 0.75, c.pos[2] + 2.0 * Math.cos(a)], target: [c.pos[0], 0.35, c.pos[2]], fov: 42 }; }
  if (t < S.shock) return { pos: [c.pos[0] + 1.2, 0.45, c.pos[2] + 1.9], target: [c.pos[0], 0.25, c.pos[2] + 0.7], fov: 34 };   // close: his whisper
  if (t < S.beat) return { pos: [c.pos[0] - 0.7, 0.75, c.pos[2] + 0.9], target: [c.pos[0], 0.55, c.pos[2] + 0.05], fov: 36 };     // the monkey's face
  if (t < S.turn) return { pos: [c.pos[0] + 1.2, 0.8, c.pos[2] + 1.5], target: [c.pos[0], 0.45, c.pos[2] + 0.1], fov: 38, roll: 0.06 };   // the heartbeat on his back
  if (t < S.laugh) return { pos: [c.pos[0], 5.0, c.pos[2] + 0.5], target: [c.pos[0], 0, c.pos[2]], fov: 46 };                     // top-down: the quiet U-turn
  if (t < S.sink) { const k = (t - S.laugh) / (S.sink - S.laugh); return { pos: lerp3([2.4, 0.6, BANK_N + 3.0], [1.9, 0.5, BANK_N + 2.6], k), target: [TREE.x + 0.3, 1.6, TREE.z + 0.8], fov: 48 }; }   // low: the laughing bank
  if (t < S.day) return { pos: [0.6, 0.25, BANK_N + 2.2], target: [-0.2, 0.25, BANK_N + 0.9], fov: 38 };                         // he looks up, then sinks
  if (t < S.cry) { const k = (t - S.day) / (S.cry - S.day); return { pos: lerp3([DEN.x + 1.5, 0.7, DEN.z + 2.8], [DEN.x + 1.1, 0.5, DEN.z + 2.3], k), target: [DEN.x - 0.3, 0.25, DEN.z + 0.8], fov: 40 }; }
  if (t < S.moral) return { pos: [DEN.x + 0.45, 0.35, DEN.z + 2.0], target: [DEN.x - 0.35, 0.2, DEN.z + 1.0], fov: 36 };          // close: holding her cold hand
  const k = Easing.inOut(Easing.cubic)(clamp((t - S.moral) / (END - S.moral)));   // dawn: crane up from him across the river to the tree
  return { pos: lerp3([DEN.x + 1.6, 1.2, DEN.z + 3.0], [2.6, 4.4, 6.5], k), target: lerp3([DEN.x - 0.4, 0.4, DEN.z + 0.9], [TREE.x + 0.5, 1.8, TREE.z + 0.6], k), fov: lerp(42, 46, k) };
}

const CameraRig: React.FC<{ t: number; c: Placed }> = ({ t, c }) => {
  const { camera } = useThree();
  const k = camAt(t, c);
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(...k.pos); cam.up.set(Math.sin(k.roll ?? 0), Math.cos(k.roll ?? 0), 0);
  cam.fov = k.fov; cam.near = 0.03; cam.far = 120; cam.lookAt(V(...k.target)); cam.updateProjectionMatrix();
  return null;
};

// time of day: 0 = day, 1 = night; plus dawn warmth
function sky(t: number): { night: number; dawn: number; flash: boolean } {
  const flash = t >= S.flash && t < S.night;
  if (t < S.den) return { night: 0, dawn: 0.4, flash };
  if (t < S.morning) return { night: flash ? 0 : 1, dawn: flash ? 0.6 : 0, flash };
  if (t < S.day) return { night: 0, dawn: t < S.ride ? 0.6 : 0, flash };
  if (t < S.moral) return { night: seg(t, S.day, S.day + 3), dawn: 0, flash };
  return { night: 1 - seg(t, S.moral, S.moral + 5), dawn: seg(t, S.moral, S.moral + 5), flash };
}

const Scene: React.FC<{ t: number }> = ({ t }) => {
  const c = crocAt(t);
  const w = wifeAt(t);
  const m = monkeyAt(t, c);
  const sk = sky(t);
  const skyN = useMemo(() => skyMat("#040816", "#1c2448", 1), []);
  const skyD = useMemo(() => skyMat("#5aa0e8", "#f2e8c8", 0), []);
  const skyDawn = useMemo(() => skyMat("#3a4a8a", "#ffb070", 0.3), []);
  const skyM = sk.night > 0.5 ? skyN : sk.dawn > 0.3 ? skyDawn : skyD;
  const laughBank = t >= S.laugh && t < S.sink + 1;
  const showHeartSign = t >= S.heart && t < S.look;
  const beat = 1 + 0.25 * Math.max(0, Math.sin(t * 7.5)) ** 8;
  return (
    <>
      <CameraRig t={t} c={c} />
      <mesh material={skyM} scale={100}><sphereGeometry args={[1, 32, 16]} /></mesh>
      {sk.night > 0.5 ? <mesh position={[-20, 25, -60]}><sphereGeometry args={[3, 24, 16]} /><meshBasicMaterial color="#f4ecd2" /></mesh> : null}
      <fog attach="fog" args={[sk.night > 0.5 ? "#0a1022" : "#d8e4e8", 14, 60]} />
      <ambientLight intensity={lerp(1.0, 0.35, sk.night)} color={sk.dawn > 0.3 ? "#ffd8b0" : "#ffffff"} />
      <hemisphereLight args={[sk.night > 0.5 ? "#4a5a9a" : "#9ad0ff", "#3a4a2a", 0.5]} />
      <directionalLight position={sk.night > 0.5 ? [-8, 12, -10] : [8, 12, 6]} intensity={lerp(2.0, 0.5, sk.night)} color={sk.night > 0.5 ? "#9fb4ff" : sk.dawn > 0.3 ? "#ffc080" : "#fff4e0"}
        castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-9} shadow-camera-right={9} shadow-camera-top={9} shadow-camera-bottom={-9} shadow-bias={-0.001} />
      <Water t={t} night={sk.night} />
      <Banks />
      <JamunTree t={t} />
      <Den t={t} glow={sk.night} />
      {/* the wife, lying on the leaves (a flower on her head) */}
      <group position={[DEN.x, 0.04, DEN.z + 0.2]} rotation={[0, -0.5, 0]} scale={[WIFE_S, WIFE_S * (1 + w.breath), WIFE_S]}>
        <Croc p={w.p} color="#6a9a4a" belly="#d0d89a" flower t={t * 0.3} />
      </group>
      {/* him */}
      <group position={c.pos} rotation={[0, c.yaw, 0]} scale={CROC_S}><Croc p={c.p} t={t} /></group>
      {/* the monkey */}
      {m ? (
        <group position={m.pos} rotation={[0, m.yaw, 0]} scale={MONK_S}>
          <Person look={MONKEY} pose={m.pose} handR={t >= S.flash && t < S.night ? <mesh scale={0.07}><sphereGeometry args={[1, 8, 6]} /><meshToonMaterial color="#4a1a5a" /></mesh> : undefined} />
          {m.heart > 0 ? <Heart pos={[0, 0.95, 0.16]} s={0.13 * beat} yaw={0} light={2.2} /> : null}
        </group>
      ) : null}
      {/* heartbeat rings travelling into his back */}
      {t >= S.beat && t < S.turn ? [0, 0.33, 0.66].map((d, k) => {
        const u = ((t * 1.2 + d) % 1);
        return <mesh key={k} position={[c.pos[0], c.pos[1] + 0.24 + 0.01 * k, c.pos[2] + 0.06]} rotation={[-Math.PI / 2, 0, 0]} scale={0.1 + u * 0.6}>
          <ringGeometry args={[0.9, 1, 32]} /><meshBasicMaterial color="#ff4a6a" transparent opacity={(1 - u) * 0.8} side={THREE.DoubleSide} /></mesh>;
      }) : null}
      {showHeartSign ? <Heart pos={[DEN.x, 1.0 + 0.1 * Math.sin(t * 2), DEN.z + 0.2]} s={0.35 * seg(t, S.heart, S.heart + 0.5) * beat} light={2.5} /> : null}
      {/* the whole bank laughing: two more monkeys and some frogs */}
      {laughBank ? <>
        {MONKEY_FRIENDS.map((lk, k) => {
          const pp = restPose(); pp.sit = 1; pp.happyEyes = true; pp.eyes = Math.sin(t * 12 + k) > 0 ? 0 : 1; pp.smile = 1; pp.armR = [-1.4, -0.3]; pp.headPitch = 0.2 + 0.1 * Math.sin(t * 13 + k);
          return <group key={k} position={[TREE.x - 0.8 + k * 1.9, k ? 1.75 : 1.6, TREE.z + 1.0]} rotation={[0, 0.1, 0]} scale={MONK_S * 0.9}><Person look={lk} pose={pp} /></group>;
        })}
        {[-1.4, 1.6, 2.6].map((x, k) => (
          <group key={k} position={[x, 0.05 + 0.04 * Math.abs(Math.sin(t * 9 + k)), BANK_N - 0.3]}>
            <Toon geom={G.sphere} color="#6ab03a" scale={[0.14, 0.1, 0.12]} outline={0.006} />
            {[-1, 1].map((s) => <mesh key={s} position={[s * 0.06, 0.09, 0.06]} scale={0.035}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#fff" /></mesh>)}
          </group>
        ))}
      </> : null}
      {/* ripples where he sinks */}
      {t >= S.sink + 3.2 && t < S.day ? [0, 0.4, 0.8].map((d, k) => {
        const u = ((t - S.sink - 3.2 + d) % 1.2) / 1.2;
        return <mesh key={k} position={[-0.2, 0.01, BANK_N + 0.9]} rotation={[-Math.PI / 2, 0, 0]} scale={0.2 + u * 1.2}><ringGeometry args={[0.92, 1, 32]} /><meshBasicMaterial color="#e8f4ff" transparent opacity={(1 - u) * 0.6} /></mesh>;
      }) : null}
      {/* his hand on hers at the end (a small paw meeting her paw) */}
      {t >= S.cry ? <Toon geom={G.sphere} color="#4f7a3a" position={[DEN.x - 0.3, 0.08, DEN.z + 0.85]} scale={[0.08, 0.04, 0.1]} outline={0.006} /> : null}
    </>
  );
};

export const Magarmachh3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const sub = SUBS.find(([a, b]) => t >= a && t < b);
  const sk = sky(t);
  const cuts = (Object.keys(S) as (keyof typeof S)[]).map((k) => S[k]);
  let dip = 0; for (const c of cuts) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.1);
  const fade = Math.min(clamp(t / 0.4), clamp((END - t) / 1.2));
  const filter = sk.flash ? "sepia(0.55) saturate(1.2) brightness(1.05)" : t >= S.cry && t < S.moral ? "saturate(0.75)" : "none";
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter }}>
        <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
          <Scene t={t} />
        </ThreeCanvas>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 52%, rgba(0,0,0,${sk.flash ? 0.65 : 0.5}) 100%)` }} />
      {sub ? (
        <div style={{ position: "absolute", top: 1300, left: 60, right: 60, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 54, lineHeight: 1.4, color: "#faf6ee", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill",
          textShadow: "0 4px 14px rgba(0,0,0,0.75)" }}>{sub[2]}</div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.4) }} />
    </AbsoluteFill>
  );
};
