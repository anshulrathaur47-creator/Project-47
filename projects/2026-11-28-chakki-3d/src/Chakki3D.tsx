import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import {
  HLook, HPose, Human, SkyEnv, SkyPreset, barkTex, basicMat, canvasTex, clamp, clothMat, dirtTex, hRest, lerp, mat, mudTex,
  nightSkyMat, plainMat, rng, seg, strawTex, sunDir, useGrass, useLeaves, woodTex,
} from "./Real";

// "जादुई चक्की चुराने वाले अमीर भाई को सब लालची कहते हैं…" (ReelAudio-21913): the magic mill, the elder brother's side of the story.
export const DURATION = 3855; // 128.5 s (narration ends 127.1 s)
const FPS = 30;
const END = DURATION / FPS;
type V = [number, number, number];

const SUBS: [number, number, string][] = [
  [0.0, 3.72, "जादुई चक्की चुराने वाले अमीर भाई को सब लालची कहते हैं।"],
  [3.74, 7.2, "पर किसी ने ये नहीं पूछा कि जिसके पास पहले से सब कुछ था,"],
  [7.22, 9.06, "उसने आखिर चक्की क्यों चुराई?"],
  [9.08, 13.06, "एक दिन छोटा भाई पैसों की मदद मांगने अपने बड़े भाई के पास गया,"],
  [13.08, 15.08, "मगर बड़े भाई ने साफ मना कर दिया।"],
  [15.1, 17.64, "छोटा भाई उसे स्वार्थी कहकर चला गया।"],
  [17.66, 21.44, "लेकिन बड़े भाई ने सालों की मेहनत से अपना कारोबार खड़ा किया था।"],
  [21.46, 24.9, "जब भी छोटा भाई मुसीबत में पड़ता, वो उसकी मदद करता।"],
  [24.92, 27.8, "मगर छोटा भाई बार-बार मदद मांगने आ जाता।"],
  [27.88, 30.88, "पर सोचो, जिस भाई ने इतनी बार मदद की थी,"],
  [31.2, 32.84, "उसने इस बार मना क्यों किया?"],
  [33.06, 35.88, "क्योंकि उसे लगने लगा था कि उसकी बार-बार की मदद"],
  [35.9, 40.1, "छोटे भाई को आत्मनिर्भर बनाने के बजाय उस पर निर्भर बना रही थी।"],
  [40.14, 43.32, "वो सोचता था, अगर मैं हर बार इसका सहारा बनता रहा,"],
  [43.34, 45.76, "तो ये अपने पैरों पर खड़ा होना कब सीखेगा?"],
  [45.78, 49.14, "कुछ दिनों बाद छोटे भाई को एक जादुई चक्की मिल गई।"],
  [49.16, 51.9, "वो चक्की से जो भी मांगता, उसे मिल जाता।"],
  [51.92, 56.02, "देखते ही देखते छोटा भाई गांव का सबसे अमीर आदमी बन गया।"],
  [56.04, 57.7, "लेकिन किस्मत ने करवट ली।"],
  [57.72, 62.12, "बड़े भाई का कारोबार घाटे में चला गया और उसकी जमा पूंजी खत्म होने लगी।"],
  [62.14, 66.12, "जिंदगी में पहली बार वो अपने छोटे भाई से मदद मांगने गया।"],
  [66.14, 67.6, "मगर छोटे भाई ने कहा,"],
  [67.7, 70.5, "\"जब मुझे जरूरत थी, तब आपने मेरी मदद नहीं की थी।\""],
  [70.6, 72.1, "\"आज मैं आपकी मदद क्यों करूं?\""],
  [72.14, 74.7, "बड़ा भाई चुपचाप घर लौट आया।"],
  [74.72, 77.6, "उसे पैसे ना मिलने से ज्यादा दुख इस बात का था"],
  [77.65, 80.1, "कि जिस भाई की उसने सालों तक मदद की,"],
  [80.15, 83.95, "उसने उसकी एक गलती याद रखी और सारी अच्छाइयां भुला दीं।"],
  [84.26, 87.96, "उसी दुख और गुस्से में एक रात उसने जादुई चक्की चुरा ली।"],
  [88.0, 90.12, "वो नाव लेकर समुद्र में निकल गया।"],
  [90.14, 93.76, "उसने सोचा कि नमक बेचकर अपना कारोबार फिर से खड़ा करेगा।"],
  [93.78, 96.64, "मगर उसे चक्की बंद करने का मंत्र नहीं पता था।"],
  [96.66, 97.98, "नमक निकलता रहा"],
  [98.0, 100.68, "और आखिरकार नाव समुद्र में डूब गई।"],
  [100.7, 103.98, "पूरी दुनिया ने बड़े भाई के लालच की कहानी सुनाई।"],
  [104.0, 107.98, "किसी ने उसके पीछे छिपी तकलीफ और टूटते भरोसे को नहीं देखा।"],
  [108.0, 112.52, "हमारी जिंदगी में भी कई बार कोई अपना 100 बार हमारी मदद करता है।"],
  [112.56, 117.28, "मगर जिस दिन वो मना कर देता है, हम उसकी पिछली सारी अच्छाइयां भूल जाते हैं।"],
  [117.3, 122.8, "कहीं तुम भी किसी अपने की एक ना की वजह से उसकी 100 हां तो नहीं भूल गए?"],
  [122.82, 127.3, "ऐसी ही कहानियों के अनसुने पहलुओं को समझने के लिए मुझे follow करें।"],
];
const T = {
  c2: 3.74, c3: 7.22, rewind: 8.4, truth: 9.08, arrive: 11.3, refuse: 13.08, selfish: 15.1, leave: 16.3, work: 17.66, night1: 19.6,
  past: 21.46, again: 24.92, again2: 25.88, again3: 26.84, think: 27.88, because: 33.06, watch2: 36.5, thought: 40.14, feet: 43.34,
  find: 45.78, ask: 49.16, rich: 51.92, flashRich: 52.5, fate: 56.04, loss: 57.72, goAsk: 62.14, said: 66.14, need: 67.7, why2: 70.6,
  back: 72.14, hurt: 74.72, years: 77.65, forgot: 80.15, theft: 84.26, sea: 88.0, salt: 90.14, mantra: 93.78, flow: 96.66, sink: 98.0,
  world: 100.7, hidden: 104.0, life: 108.0, refuse2: 112.56, mem3: 114.9, forgot2: 117.3, follow: 122.82,
};

// ------------------------------------------------------------------ the people (new faces)
const ELDER: HLook = { skin: "#8a5a3c", hair: "#3a3430", hairStyle: "short", top: "#6e1e2a", topStyle: "kurta", bottom: "#ece2cc", bottomStyle: "dhoti", pallu: "#c8a060", moustache: "#1e1a16", chappal: "plain" };
const YOUNG_POOR: HLook = { skin: "#956240", hair: "#120e0a", hairStyle: "short", top: "#5a7a9a", topStyle: "shirt", bottom: "#8a7a64", bottomStyle: "dhoti", worn: 1, chappal: "torn", stubble: "#2a2420" };
const YOUNG_RICH: HLook = { skin: "#956240", hair: "#120e0a", hairStyle: "short", top: "#d8a83a", topStyle: "kurta", bottom: "#f4efe4", bottomStyle: "dhoti", pallu: "#b8242a", turban: "#c8302a", chappal: "plain", moustache: "#120e0a" };
const VILL1: HLook = { skin: "#9a6a48", hair: "#151010", hairStyle: "bun", top: "#8a2a4a", topStyle: "blouse", bottom: "#1f7a7a", bottomStyle: "saree", pallu: "#2a8a8a", bindi: true, chappal: "plain" };
const VILL2: HLook = { skin: "#86583a", hair: "#1a1612", hairStyle: "short", top: "#c8b048", topStyle: "shirt", bottom: "#4a4038", bottomStyle: "pants", moustache: "#1a1612", chappal: "plain" };
const VILL3: HLook = { skin: "#8a5e42", hair: "#d8d4cc", hairStyle: "bun", top: "#d8d0c0", topStyle: "blouse", bottom: "#ece6da", bottomStyle: "saree", pallu: "#e4ddd0", chappal: "plain" };
const S_YOUNG = 0.96;

// ------------------------------------------------------------------ places (village: the shop on the left, the younger's hut / mansion on the right, the lane along x at z≈1.2)
const SHOP: V = [-3.2, 0, -1.6]; const PLINTH = 0.25;
const COUNTER: V = [-3.2, 0, -0.95];      // where the elder stands behind his counter
const FRONT: V = [-2.9, 0, 0.55];         // where a customer stands
const HUT: V = [3.6, 0, -1.8];
const MANSION: V = [3.6, 0, -2.2];
const MDOOR: V = [3.6, 0.15, -0.3];       // the mansion's door step
const GATE: V = [3.4, 0, 1.05];
const CHARPAI: V = [5.7, 0, -0.35];
const FIND: V = [6.8, 0, 1.0];
const STOOL: V = [4.75, 0, 0.3];          // the chakki on its stool in the mansion yard
const fwd = (yaw: number, d: number): [number, number] => [Math.sin(yaw) * d, Math.cos(yaw) * d];
const add = (a: V, b: V): V => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const lerp3 = (a: V, b: V, k: number): V => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
const orbit = (c: V, yaw: number, off: number, d: number, h: number): V => [c[0] + Math.sin(yaw + off) * d, c[1] + h, c[2] + Math.cos(yaw + off) * d];
const yawTo = (from: V, to: V) => Math.atan2(to[0] - from[0], to[2] - from[2]);
const angLerp = (a: number, b: number, k: number) => { let d = b - a; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2; return a + d * k; };
const onTop = (p: V, h: number, s: number): V => [p[0], h - 0.2 * s, p[2]];

// ------------------------------------------------------------------ modes and story time
type Mode = "classic" | "village" | "sea" | "world" | "dawnsea" | "memory" | "shore";
const modeAt = (t: number): Mode => t < T.truth ? "classic" : t < T.sea ? "village" : t < T.world ? "sea" : t < T.hidden ? "world" : t < T.life ? "dawnsea" : t < T.forgot2 ? "memory" : "shore";
function storyTime(t: number): number {
  if (t >= T.rewind && t < T.truth) return Math.max(0.8, T.rewind - (t - T.rewind) * 11);
  if (t >= T.life && t < T.refuse2) return 21.6 + (t - T.life) * 0.75;
  if (t >= T.refuse2 && t < T.forgot2) return 13.1 + (t - T.refuse2) * 0.95;
  return t;
}
const isPast = (t: number) => (t >= T.past && t < T.think) || (t >= T.life && t < T.forgot2);

// ------------------------------------------------------------------ props
const POUCH = <group position={[0.0, -0.04, 0.05]}><mesh material={clothMat("#a8242a", 0.3)} castShadow><sphereGeometry args={[0.075, 14, 10]} /></mesh><mesh material={clothMat("#a8242a", 0.3)} position={[0, 0.08, 0]} castShadow><cylinderGeometry args={[0.02, 0.035, 0.05, 8]} /></mesh><mesh material={plainMat("#d8b040", 0.4, 0.6)} position={[0, 0.06, 0]}><torusGeometry args={[0.024, 0.006, 6, 12]} /></mesh></group>;
const SACK_SHOULDER = <mesh material={mat("jute", () => new THREE.MeshStandardMaterial({ map: strawTex(1), color: "#d8c8a0", roughness: 1 }))} position={[0.02, 0.18, -0.12]} rotation={[0.2, 0, 1.3]} scale={[0.22, 0.34, 0.17]} castShadow><sphereGeometry args={[1, 14, 10]} /></mesh>;
const PEN = <mesh material={plainMat("#222", 0.5)} position={[0, -0.02, 0.06]} rotation={[1.2, 0, 0]} castShadow><cylinderGeometry args={[0.005, 0.005, 0.14, 6]} /></mesh>;

// the chakki: two stones, a wooden peg; glows gold when it is working magic
const Chakki: React.FC<{ spin: number; glow: number; s?: number }> = ({ spin, glow, s = 1 }) => {
  const stone = mat("stone", () => new THREE.MeshStandardMaterial({ map: dirtTex(2, "#8c8780"), roughness: 0.92, color: "#ffffff" }));
  return (
    <group scale={s}>
      <mesh material={stone} position={[0, 0.055, 0]} castShadow receiveShadow><cylinderGeometry args={[0.26, 0.27, 0.11, 28]} /></mesh>
      <mesh material={stone} position={[0.27, 0.07, 0]} castShadow><boxGeometry args={[0.1, 0.05, 0.07]} /></mesh>
      <group position={[0, 0.11, 0]} rotation={[0, spin, 0]}>
        <mesh material={stone} position={[0, 0.05, 0]} castShadow receiveShadow><cylinderGeometry args={[0.245, 0.25, 0.1, 28]} /></mesh>
        <mesh material={basicMat("#1a1410")} position={[0, 0.101, 0]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.045, 16]} /></mesh>
        <mesh material={mat("pegwood", () => new THREE.MeshStandardMaterial({ map: woodTex(), roughness: 0.8 }))} position={[0.18, 0.17, 0]} castShadow><cylinderGeometry args={[0.018, 0.02, 0.16, 8]} /></mesh>
      </group>
      {glow > 0 ? (
        <>
          <mesh position={[0, 0.11, 0]} rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.258, 0.012, 8, 40]} /><meshBasicMaterial color="#ffd060" transparent opacity={glow} blending={THREE.AdditiveBlending} depthWrite={false} /></mesh>
          <mesh position={[0, 0.12, 0]}><sphereGeometry args={[0.42, 20, 14]} /><meshBasicMaterial color="#ffb840" transparent opacity={0.1 * glow} blending={THREE.AdditiveBlending} depthWrite={false} /></mesh>
          {Array.from({ length: 14 }, (_, k) => { const a = k * 0.45 + spin * 0.4, r = 0.32 + 0.06 * Math.sin(k * 3 + spin); return <mesh key={k} position={[Math.cos(a) * r, 0.1 + ((k * 0.13 + spin * 0.05) % 0.5), Math.sin(a) * r]} scale={0.008 + 0.006 * Math.sin(k + spin * 2) ** 2}><sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color="#fff0b0" transparent opacity={glow} blending={THREE.AdditiveBlending} depthWrite={false} /></mesh>; })}
          <pointLight position={[0, 0.4, 0]} intensity={2.2 * glow} distance={3.5} decay={1.6} color="#ffc060" />
        </>
      ) : null}
    </group>
  );
};

// ------------------------------------------------------------------ who does what, when
type Act = { look: HLook; pos: V; yaw: number; p: HPose; s: number; lying?: boolean };
const plead = (p: HPose) => { p.armL = [-0.95, 0.6]; p.armR = [-0.95, -0.6]; p.elbowL = -1.5; p.elbowR = -1.5; p.brow = 1; p.headPitch = 0.12; p.smile = -0.2; };
const crossArms = (p: HPose) => { p.armL = [-0.55, 0.32]; p.elbowL = -1.85; p.armR = [-0.55, -0.32]; p.elbowR = -1.85; };
const walkP = (p: HPose, t: number, sp = 6.5) => { p.walk = 1; p.phase = t * sp; };
const talk = (p: HPose, t: number, k = 1) => { p.mouth = (0.2 + 0.25 * Math.abs(Math.sin(t * 9))) * k; };
const carryChakki = (p: HPose) => { p.armL = [-0.75, 0.42]; p.armR = [-0.75, -0.42]; p.elbowL = -1.25; p.elbowR = -1.25; };

function elderAt(t: number, st: number, mode: Mode): Act | null {
  const p = hRest();
  if (mode === "classic") {
    if (st < T.c2) {   // the version everyone tells: sneaking off with the mill, grinning
      carryChakki(p); p.smile = 1; p.eyes = 0.7; p.lookX = Math.sin(st * 3); p.brow = -0.3; p.spine = 0.15; walkP(p, st, 5); p.headYaw = 0.4 * Math.sin(st * 2.2);
      return { look: ELDER, pos: lerp3(STOOL, [2.0, 0, 1.6], seg(st, 0.6, 3.7)), yaw: yawTo(STOOL, [2.0, 0, 1.6]), p, s: 1 };
    }
    p.smile = st < T.c3 ? 0.5 : 0; p.headPitch = -0.08; crossArms(p); p.brow = st < T.c3 ? -0.2 : 0.6;
    return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0, p, s: 1 };
  }
  if (mode === "world" || mode === "shore" || mode === "dawnsea") return null;
  if (mode === "sea") {   // rowing out, then the mill
    p.sit = 1; p.spine = 0.15;
    if (t < T.salt) { const ph = t * 3.2; p.armL = [-1.25 + 0.45 * Math.sin(ph), 0.2]; p.armR = [-1.25 + 0.45 * Math.sin(ph), -0.2]; p.elbowL = -0.7 - 0.5 * Math.cos(ph); p.elbowR = p.elbowL; p.spine = 0.12 + 0.18 * Math.sin(ph); p.headPitch = -0.1; p.brow = 0.5; }
    else if (t < T.mantra) { p.armR = [-1.15, -0.1]; p.elbowR = -0.5 + 0.35 * Math.sin(t * 7); p.spine = 0.3; p.smile = seg(t, 91.0, 92.0) * 0.6; p.eyes = 0.9; p.headPitch = 0.35; }
    else if (t < T.sink) { p.armL = [-1.2, 0.3]; p.armR = [-1.2, -0.3]; p.elbowL = -0.6; p.elbowR = -0.6; p.spine = 0.35; p.brow = 1; p.eyes = 1.15; p.mouth = 0.5 + 0.3 * Math.abs(Math.sin(t * 6)); p.smile = -0.6; p.headPitch = 0.3 + 0.1 * Math.sin(t * 8); }
    else { const k = seg(t, T.sink, 99.0); p.sit = 1 - k; p.spine = 0.1; p.headPitch = -0.5 * k; p.brow = 1; p.eyes = 1.1; p.mouth = 0.4; p.armL = [-0.3, 0.5 * k]; p.armR = [-0.3, -0.5 * k]; p.elbowL = -0.4; p.elbowR = -0.4; p.tear = 1; }
    return { look: ELDER, pos: [0, 0, 0], yaw: 0, p, s: 1 };
  }
  // the village (and the memories, which replay it)
  if (st < T.work) {
    if (st < T.refuse) { p.headYaw = st > 10.6 ? 0.35 : 0; p.eyes = 0.95; p.armL = [-0.5, 0.2]; p.elbowL = -1.1; p.armR = [-0.5, -0.2]; p.elbowR = -1.1; return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0.25, p, s: 1 }; }
    if (st < T.selfish) { p.headYaw = 0.35 * Math.sin((st - T.refuse) * 7) * (1 - seg(st, 14.4, 15.0)); p.armR = [-1.3, -0.25]; p.elbowR = -1.25; p.brow = 0.4; p.smile = -0.3; p.anger = 0.25; p.mouth = st < 14.2 ? 0.15 : 0; return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0.25, p, s: 1 }; }
    p.brow = 0.8; p.smile = -0.4; p.headPitch = st > T.leave ? 0.2 : 0; p.headYaw = st > T.leave ? 0.5 : 0.25;
    return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0.25, p, s: 1 };
  }
  if (st < T.night1) {   // carrying a sack into the shop
    const k = seg(st, T.work, T.night1 - 0.15); p.handR = SACK_SHOULDER; p.armR = [-2.9, -0.45]; p.elbowR = -2.3; p.spine = 0.2; walkP(p, st, 5.5); p.brow = 0.3; p.mouth = 0.15;
    const a: V = [-0.4, 0, 1.6], b: V = [-2.6, PLINTH, -0.55];
    return { look: ELDER, pos: [lerp(a[0], b[0], k), seg(st, 19.0, 19.3) * PLINTH, lerp(a[2], b[2], k)], yaw: yawTo(a, b), p, s: 1 };
  }
  if (st < T.past) { p.handR = PEN; p.armR = [-1.1, -0.1]; p.elbowR = -0.6 + 0.08 * Math.sin(st * 12); p.armL = [-0.9, 0.15]; p.elbowL = -0.7; p.spine = 0.35; p.headPitch = 0.45; p.eyes = 0.6; p.brow = 0.5; return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0, p, s: 1 }; }
  if (st < T.think) {   // the past: giving, again and again
    const local = st < T.again ? st - T.past : st < T.again2 ? st - T.again : st < T.again3 ? st - T.again2 : st - T.again3;
    const giveAt = st < T.again ? 1.4 : 0.35;
    const k = seg(local, giveAt, giveAt + 0.4);
    p.armR = [lerp(-0.5, -1.35, k), -0.1]; p.elbowR = lerp(-1.0, -0.25, k); p.handR = k < 0.98 || local < giveAt + 0.6 ? POUCH : null;
    p.smile = st < T.again ? 0.55 : st < T.again2 ? 0.25 : st < T.again3 ? 0 : -0.2; p.brow = st < T.again ? 0 : 0.4 + (st > T.again3 ? 0.4 : 0); p.eyes = st > T.again3 ? 0.75 : 0.95;
    return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0.25, p, s: 1 };
  }
  if (st < T.because) { p.handR = POUCH; p.armR = [-0.7, -0.1]; p.elbowR = -1.3; p.headPitch = 0.25; p.brow = 0.7; p.eyes = 0.75; p.headYaw = 0.15 * Math.sin(st * 0.8); return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0.1, p, s: 1 }; }
  if (st < T.thought) { p.brow = 0.8; p.smile = -0.4; p.headYaw = 0; p.armL = [-0.2, -0.2]; p.armR = [-0.2, 0.2]; p.elbowL = -1.2; p.elbowR = -1.2; return { look: ELDER, pos: [2.9, 0, 1.75], yaw: yawTo([2.9, 0, 1.75], CHARPAI), p, s: 1 }; }
  if (st < T.feet) { const k = seg(st, 40.6, 41.4); p.handR = POUCH; p.armR = [lerp(-1.2, -0.75, k), lerp(-0.1, 0.35, k)]; p.elbowR = lerp(-0.2, -1.7, k); p.brow = lerp(0.6, 0.3, k); p.anger = 0.3 * k; p.eyes = 0.9; p.headPitch = 0.1; return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0.15, p, s: 1 }; }
  if (st < T.fate) return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0.2, p, s: 1 };
  if (st < T.loss) { p.headPitch = -0.3; p.brow = 0.8; p.eyes = 1.05; return { look: ELDER, pos: [COUNTER[0], PLINTH, COUNTER[2]], yaw: 0.2, p, s: 1 }; }
  if (st < T.goAsk) {   // sitting on the edge of his empty shop
    p.sit = 1; p.spine = 0.45; p.headPitch = 0.4; p.brow = 1; p.eyes = 0.45; p.smile = -0.6; p.armL = [-1.0, 0.2]; p.armR = [-1.0, -0.2]; p.elbowL = 0.8; p.elbowR = 0.8;
    return { look: ELDER, pos: onTop([-3.0, 0, -0.25], PLINTH, 1), yaw: 0.1, p, s: 1 };
  }
  if (st < T.said) {   // walks to the mansion and folds his hands at the gate
    const a: V = [-2.2, 0, 1.35]; const k = seg(st, T.goAsk, 65.2);
    if (k < 1) { walkP(p, st, 5); p.headPitch = 0.2; p.brow = 0.8; } else plead(p);
    return { look: ELDER, pos: lerp3(a, GATE, k), yaw: k < 1 ? yawTo(a, GATE) : yawTo(GATE, MDOOR), p, s: 1 };
  }
  if (st < T.back) { plead(p); p.brow = 1; p.eyes = st > T.why2 ? 0.8 : 1; if (st > 71.4) { p.armL = [-0.2, 0.1]; p.armR = [-0.2, -0.1]; p.elbowL = -0.3; p.elbowR = -0.3; p.headPitch = 0.3; } return { look: ELDER, pos: GATE, yaw: yawTo(GATE, MDOOR), p, s: 1 }; }
  if (st < T.hurt) { const a: V = [3.0, 0, 1.3], b: V = [-0.2, 0, 1.4]; walkP(p, st, 4.6); p.headPitch = 0.35; p.brow = 1; p.eyes = 0.6; p.smile = -0.6; p.spine = 0.12; return { look: ELDER, pos: lerp3(a, b, seg(st, T.back, T.hurt + 0.3)), yaw: yawTo(a, b), p, s: 1 }; }
  if (st < T.theft) {   // alone in the dark shop, with a diya
    p.sit = 1; p.spine = 0.35; p.headPitch = st > T.forgot ? -0.05 : 0.3; p.brow = 1; p.eyes = 0.5; p.smile = -0.7; p.tear = seg(st, 76, 78.5); p.mouth = st > T.years && st < T.forgot ? 0.12 : 0;
    p.armL = [-1.0, 0.2]; p.armR = [-1.0, -0.2]; p.elbowL = 0.8; p.elbowR = 0.8; p.headYaw = st > T.forgot ? 0.9 : 0;
    return { look: ELDER, pos: onTop([-3.0, 0, -0.25], PLINTH, 1), yaw: 0.1, p, s: 1 };
  }
  // the theft
  const inK = seg(st, T.theft, 85.6), outK = seg(st, 86.3, 87.98);
  const a: V = [3.0, 0, 1.6], b: V = add(STOOL, [-0.35, 0, 0.35]), c: V = [1.0, 0, 1.8];
  if (st < 85.6) { walkP(p, st, 4); p.spine = 0.25; p.headYaw = 0.5 * Math.sin(st * 2.5); p.brow = 0.6; p.anger = 0.4; return { look: ELDER, pos: lerp3(a, b, inK), yaw: yawTo(a, b), p, s: 1 }; }
  if (st < 86.3) { const k = seg(st, 85.6, 86.1); p.spine = lerp(0.6, 0.15, seg(st, 85.9, 86.3)); p.armL = [lerp(-1.2, -0.75, k), 0.42]; p.armR = [lerp(-1.2, -0.75, k), -0.42]; p.elbowL = -1.25; p.elbowR = -1.25; p.anger = 0.5; p.brow = 0.5; return { look: ELDER, pos: b, yaw: yawTo(b, STOOL), p, s: 1 }; }
  carryChakki(p); walkP(p, st, 5); p.spine = 0.2; p.anger = 0.5; p.headYaw = -0.4 * Math.sin(st * 2);
  return { look: ELDER, pos: lerp3(b, c, outK), yaw: angLerp(yawTo(b, STOOL), yawTo(b, c), seg(st, 86.3, 86.6)), p, s: 1 };
}
const elderHolding = (st: number, mode: Mode) => mode === "classic" ? st < T.c2 : mode === "village" && st >= 86.0 && st < T.sea;

function youngAt(t: number, st: number, mode: Mode): Act | null {
  const p = hRest(); const S = S_YOUNG;
  if (mode === "classic" || mode === "sea" || mode === "world" || mode === "dawnsea") return null;
  if (mode === "shore") {   // at the water's edge at dawn, holding the shawl the sea gave back
    p.brow = 1; p.eyes = 0.6; p.smile = -0.6; p.tear = seg(t, 119, 121); p.headPitch = 0.25 - 0.3 * seg(t, 121.5, 123);
    p.armL = [-0.6, 0.3]; p.armR = [-0.6, -0.3]; p.elbowL = -1.2; p.elbowR = -1.2;
    p.handR = <mesh material={clothMat("#c8a060", 1)} position={[0.04, -0.2, 0.04]} rotation={[0.15, 0.3, 0.1]} castShadow><boxGeometry args={[0.22, 0.5, 0.012]} /></mesh>;
    return { look: { ...YOUNG_RICH, turban: undefined }, pos: [0.2, 0.06, 9.3], yaw: Math.PI + 0.1, p, s: S };
  }
  if (st < T.work) {
    if (st < T.arrive) { const a: V = [2.4, 0, 1.4]; walkP(p, st); p.brow = 0.6; p.headPitch = 0.15; return { look: YOUNG_POOR, pos: lerp3(a, FRONT, seg(st, T.truth, T.arrive)), yaw: yawTo(a, FRONT), p, s: S }; }
    if (st < T.refuse) { plead(p); talk(p, st, 0.8); return { look: YOUNG_POOR, pos: FRONT, yaw: Math.PI - 0.15, p, s: S }; }
    if (st < T.selfish) { plead(p); p.brow = 1; p.eyes = lerp(1, 1.1, seg(st, 13.4, 13.8)); p.smile = -0.5; return { look: YOUNG_POOR, pos: FRONT, yaw: Math.PI - 0.15, p, s: S }; }
    if (st < T.leave) { p.armR = [-1.55, -0.1]; p.elbowR = -0.05; p.anger = 1; talk(p, st, 1.4); p.brow = 0; return { look: YOUNG_POOR, pos: FRONT, yaw: Math.PI - 0.15, p, s: S }; }
    const turn = seg(st, T.leave, T.leave + 0.35); const b: V = [4.6, 0, 1.3];
    walkP(p, st, 7); p.anger = 0.8; p.headYaw = st < 16.9 ? 0.6 : 0;
    return { look: YOUNG_POOR, pos: lerp3(FRONT, b, seg(st, T.leave + 0.2, 19.5)), yaw: angLerp(Math.PI - 0.15, yawTo(FRONT, b), turn), p, s: S };
  }
  if (st < T.past) return null;
  if (st < T.think) {   // the past: comes asking, gets help, again and again
    const local = st < T.again ? st - T.past : st < T.again2 ? st - T.again : st < T.again3 ? st - T.again2 : st - T.again3;
    const giveAt = st < T.again ? 1.4 : 0.35;
    if (local < giveAt) { plead(p); talk(p, st, 0.7); }
    else { const k = seg(local, giveAt + 0.25, giveAt + 0.6); p.armR = [lerp(-1.3, -0.6, k), -0.1]; p.elbowR = lerp(-0.3, -1.3, k); p.handR = POUCH; p.smile = 0.8; p.eyes = 0.8; p.armL = [-0.95, 0.6]; p.elbowL = -1.5; }
    return { look: YOUNG_POOR, pos: FRONT, yaw: Math.PI - 0.15, p, s: S };
  }
  if (st < T.because) return null;
  if (st < T.thought) {   // lounging on his charpai, the field gone to weeds
    p.eyes = 0; p.smile = 0.25; p.mouth = 0.1 + 0.08 * Math.abs(Math.sin(st * 1.5)); p.armL = [-2.8, 0.4]; p.elbowL = -2.0; p.armR = [-0.3, -0.1];
    return { look: YOUNG_POOR, pos: [CHARPAI[0], 0.47, CHARPAI[2]], yaw: Math.PI / 2, p, s: S, lying: true };
  }
  if (st < T.feet) return null;
  if (st < T.find) { const a: V = [3.0, 0, 1.45], b: V = [6.2, 0, 1.6]; walkP(p, st, 6); p.headPitch = 0.1; return { look: YOUNG_POOR, pos: lerp3(a, b, seg(st, T.feet, T.find)), yaw: yawTo(a, b), p, s: S }; }
  if (st < T.ask) {   // finds the glowing mill in the weeds
    const k = seg(st, T.find, 46.8); p.sit = 0.55 * k; p.spine = 0.45 * k; p.headPitch = 0.4 * k; p.eyes = lerp(1, 1.15, k); p.brow = 0.6; p.mouth = 0.3 * k; p.smile = 0.3;
    p.armL = [-0.9 * k, 0.3]; p.armR = [-0.9 * k, -0.3]; p.elbowL = -0.4; p.elbowR = -0.4;
    return { look: YOUNG_POOR, pos: add(FIND, [0, 0, 0.55]), yaw: Math.PI, p, s: S };
  }
  if (st < T.flashRich) {   // asks; gold pours out
    p.sit = 1; p.spine = 0.3; p.armR = [-1.25, -0.1]; p.elbowR = -0.6 + 0.35 * Math.sin(st * 7); p.smile = 1; p.eyes = 0.75; p.mouth = 0.3 + 0.2 * Math.abs(Math.sin(st * 5)); p.headPitch = 0.3;
    return { look: YOUNG_POOR, pos: add(FIND, [0, 0, 0.5]), yaw: Math.PI, p, s: S };
  }
  if (st < T.fate) {   // the richest man in the village: walks out of his new mansion
    const a: V = add(MDOOR, [0, 0, -0.1]), b: V = add(GATE, [0.2, 0, -0.25]); const k = seg(st, 53.3, 55.0);
    if (st < 53.3) return null;
    if (k < 1) walkP(p, st, 5);
    p.smile = 0.8; p.headPitch = -0.12; p.armL = [0.1, -0.35]; p.armR = [0.1, 0.35]; p.elbowL = -1.2; p.elbowR = -1.2;
    return { look: YOUNG_RICH, pos: lerp3(a, b, k), yaw: yawTo(a, b), p, s: S };
  }
  if (st < T.said) return null;
  if (st < T.back) {   // at his door: the refusal
    crossArms(p); p.smile = 0.45; p.brow = -0.2; p.headPitch = -0.1;
    if (st > T.need - 0.1 && st < 70.5) { talk(p, st, 1.1); p.anger = 0.3; }
    if (st > T.why2) { talk(p, st, 1.3); p.smile = 0.6; p.anger = 0.5; p.spine = 0.15; }
    const turn = seg(st, 71.6, 71.95);
    return st < 71.95 ? { look: YOUNG_RICH, pos: MDOOR, yaw: angLerp(Math.PI - 0.05, 0, turn), p, s: S } : null;
  }
  return null;
}
const doorClosed = (st: number) => (st >= 71.9 && st < T.sea) ? seg(st, 71.95, 72.4) : 0;

function villagersAt(t: number, st: number, mode: Mode): Act[] {
  const out: Act[] = [];
  if (mode === "classic" && st >= T.c2 && st < T.c3) {
    [[VILL1, [-1.6, 0, 1.9], 0.92], [VILL2, [-0.6, 0, 2.2], 0.98], [VILL3, [-2.6, 0, 2.4], 0.88]].forEach(([look, pos, s], i) => {
      const p = hRest(); p.armR = [-1.5, -0.1]; p.elbowR = -0.1; p.anger = 0.5; p.smile = -0.3; talk(p, st + i, 0.8); p.headYaw = i === 1 ? 0.3 * Math.sin(st * 2) : 0;
      if (i === 2) { p.armR = [-0.9, 0.3]; p.elbowR = -1.9; p.armL = [0, 0.1]; }
      out.push({ look: look as HLook, pos: pos as V, yaw: yawTo(pos as V, COUNTER), p, s: s as number });
    });
  }
  if (mode === "world") {
    [[VILL1, [-0.5, 0, 1.3], 0.92], [VILL2, [0.6, 0, 1.6], 0.98], [VILL3, [-0.2, 0, 2.2], 0.88]].forEach(([look, pos, s], i) => {
      const p = hRest(); talk(p, t + i * 0.7, i === Math.floor(t * 0.8) % 3 ? 1 : 0.2); p.smile = 0.3; p.brow = -0.1;
      if (i === 0) { p.armR = [-1.4, 0.7]; p.elbowR = -0.2; }
      if (i === 1) crossArms(p);
      if (i === 2) { p.armR = [-0.9, 0.3]; p.elbowR = -1.9; }
      out.push({ look: look as HLook, pos: pos as V, yaw: yawTo(pos as V, [0.0, 0, 1.6]) + (i === 0 ? 0.6 : 0), p, s: s as number });
    });
  }
  if (mode === "village" && st >= 53.6 && st < T.fate) {   // they greet the rich brother
    [[VILL1, [2.2, 0, 2.3], 0.92], [VILL2, [4.9, 0, 2.4], 0.98]].forEach(([look, pos, s]) => {
      const p = hRest(); plead(p); p.brow = 0; p.smile = 0.7; p.headPitch = 0.2;
      out.push({ look: look as HLook, pos: pos as V, yaw: yawTo(pos as V, GATE), p, s: s as number });
    });
  }
  return out;
}

// ------------------------------------------------------------------ light presets
const MORN: SkyPreset = { sunElev: 22, sunAz: 60, turbidity: 4, rayleigh: 1.3, exposure: 0.5, env: 0.9 };
const NOON: SkyPreset = { sunElev: 58, sunAz: 20, turbidity: 3, rayleigh: 2.2, exposure: 0.5, env: 0.9 };
const GOLD: SkyPreset = { sunElev: 11, sunAz: 300, turbidity: 8, rayleigh: 2.4, exposure: 0.5, env: 0.75 };
const STORM: SkyPreset = { sunElev: 18, sunAz: 330, turbidity: 18, rayleigh: 0.6, exposure: 0.4, env: 0.55 };
const DUSK: SkyPreset = { sunElev: 2.5, sunAz: 280, turbidity: 10, rayleigh: 3.0, exposure: 0.8, env: 0.65 };
const DAWN: SkyPreset = { sunElev: 2.2, sunAz: 180, turbidity: 7, rayleigh: 3.2, exposure: 0.7, env: 0.8 };
type Light = SkyPreset | "night";
function villageLight(st: number): Light {
  if (st < T.truth) return st < T.c2 ? "night" : NOON;
  if (st < T.work) return MORN;
  if (st < T.night1) return MORN;
  if (st < T.past) return "night";
  if (st < T.again) return GOLD;
  if (st < T.again2) return MORN;
  if (st < T.again3) return NOON;
  if (st < T.think) return GOLD;
  if (st < T.find) return NOON;
  if (st < T.fate) return GOLD;
  if (st < T.goAsk) return STORM;
  if (st < T.hurt) return DUSK;
  return "night";
}
const presetName = (p: SkyPreset) => p === MORN ? "morn" : p === NOON ? "noon" : p === GOLD ? "gold" : p === STORM ? "storm" : p === DUSK ? "dusk" : "dawn";

// ------------------------------------------------------------------ the village
const Hut: React.FC<{ p: V; r?: number; wall: THREE.Material; thatch: THREE.Material; lit?: boolean }> = ({ p, r = 0, wall, thatch, lit }) => (
  <group position={p} rotation={[0, r, 0]}>
    <mesh position={[0, 0.9, 0]} material={wall} castShadow receiveShadow><boxGeometry args={[3, 1.8, 2.4]} /></mesh>
    <mesh position={[0, 2.3, 0]} rotation={[0, Math.PI / 4, 0]} material={thatch} castShadow receiveShadow><coneGeometry args={[2.4, 1.3, 4]} /></mesh>
    <mesh position={[0.4, 0.78, 1.205]} material={basicMat(lit ? "#e8a050" : "#0c0906")}><planeGeometry args={[0.8, 1.55]} /></mesh>
    <mesh position={[-0.85, 1.15, 1.205]} material={basicMat(lit ? "#d88a3a" : "#0c0906")}><planeGeometry args={[0.36, 0.32]} /></mesh>
  </group>
);
const signTex = () => canvasTex("signboard", 512, (x, n) => {
  x.fillStyle = "#1d4a3a"; x.fillRect(0, 0, n, n);
  x.strokeStyle = "#e8c860"; x.lineWidth = 14; x.strokeRect(12, n * 0.3 + 12, n - 24, n * 0.4 - 24);
  x.fillStyle = "#f2e2a0"; x.font = "bold 96px 'Noto Sans Devanagari', sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText("अनाज भंडार", n / 2, n / 2 + 6);
}, [1, 1]);
const Shop: React.FC<{ full: number; night: boolean; t: number; ledger: boolean; diya: number; moneyBox: boolean; signSwing: number }> = ({ full, night, t, ledger, diya, moneyBox, signSwing }) => {
  const plaster = mat("plaster", () => new THREE.MeshStandardMaterial({ map: mudTex(2, "#d8c8a0"), roughness: 1 }));
  const wood = mat("woodm", () => new THREE.MeshStandardMaterial({ map: woodTex(), roughness: 0.85 }));
  const jute = mat("jute", () => new THREE.MeshStandardMaterial({ map: strawTex(1), color: "#d8c8a0", roughness: 1 }));
  const sign = useMemo(() => { const tx = signTex().clone(); tx.repeat.set(1, 0.4); tx.offset.set(0, 0.3); tx.needsUpdate = true; return new THREE.MeshStandardMaterial({ map: tx, roughness: 0.7 }); }, []);
  const sacks: V[] = [[-4.6, PLINTH, -2.6], [-4.0, PLINTH, -2.65], [-3.4, PLINTH, -2.6], [-2.8, PLINTH, -2.65], [-2.2, PLINTH, -2.6], [-1.6, PLINTH, -2.55], [-4.7, PLINTH, -2.0], [-4.75, PLINTH, -1.4], [-1.55, PLINTH, -1.9], [-4.3, PLINTH + 0.5, -2.62], [-3.1, PLINTH + 0.5, -2.62], [-1.9, PLINTH + 0.5, -2.6]];
  const nSacks = Math.round(full * sacks.length);
  return (
    <group>
      <mesh position={[SHOP[0], PLINTH / 2, SHOP[2] + 0.2]} material={plaster} castShadow receiveShadow><boxGeometry args={[4.4, PLINTH, 3.4]} /></mesh>
      <mesh position={[SHOP[0], 1.4 + PLINTH, SHOP[2] - 1.45]} material={plaster} castShadow receiveShadow><boxGeometry args={[4.2, 2.8, 0.2]} /></mesh>
      {[-1, 1].map((s) => <mesh key={s} position={[SHOP[0] + s * 2.0, 1.4 + PLINTH, SHOP[2]]} material={plaster} castShadow receiveShadow><boxGeometry args={[0.2, 2.8, 3.0]} /></mesh>)}
      <mesh position={[SHOP[0], 2.85 + PLINTH, SHOP[2]]} material={plaster} castShadow receiveShadow><boxGeometry args={[4.5, 0.16, 3.3]} /></mesh>
      <mesh position={[SHOP[0], 2.42, 0.18]} rotation={[0.32, 0, 0]} material={wood} castShadow receiveShadow><boxGeometry args={[4.5, 0.05, 0.95]} /></mesh>
      {[-1, 1].map((s) => <mesh key={"po" + s} position={[SHOP[0] + s * 2.05, 1.15, 0.55]} material={wood} castShadow><cylinderGeometry args={[0.05, 0.05, 2.3, 8]} /></mesh>)}
      {/* signboard (swings in the storm) */}
      <group position={[SHOP[0], 3.35, -0.05]} rotation={[signSwing, 0, 0]}><mesh position={[0, -0.05, 0]} material={sign} castShadow><boxGeometry args={[2.6, 0.62, 0.05]} /></mesh></group>
      {/* counter, scale, ledger, diya */}
      <mesh position={[COUNTER[0], PLINTH + 0.42, -0.45]} material={wood} castShadow receiveShadow><boxGeometry args={[2.6, 0.84, 0.5]} /></mesh>
      <group position={[COUNTER[0] - 0.75, PLINTH + 0.84, -0.45]}>
        <mesh material={plainMat("#b89040", 0.35, 0.8)} position={[0, 0.32, 0]} castShadow><cylinderGeometry args={[0.012, 0.012, 0.64, 6]} /></mesh>
        <mesh material={plainMat("#b89040", 0.35, 0.8)} position={[0, 0.62, 0]} rotation={[0, 0, Math.PI / 2 + 0.03 * Math.sin(t)]} castShadow><cylinderGeometry args={[0.01, 0.01, 0.6, 6]} /></mesh>
        {[-1, 1].map((s) => <mesh key={s} material={plainMat("#c8a050", 0.3, 0.85)} position={[s * 0.28, 0.32, 0]} castShadow><cylinderGeometry args={[0.1, 0.08, 0.025, 18]} /></mesh>)}
      </group>
      {ledger ? <mesh position={[COUNTER[0] + 0.1, PLINTH + 0.86, -0.5]} rotation={[0, 0.15, 0]} material={clothMat("#9a2a24", 0.3)} castShadow><boxGeometry args={[0.36, 0.035, 0.26]} /></mesh> : null}
      {diya > 0 ? (
        <group position={[COUNTER[0] + 0.55, PLINTH + 0.84, -0.3]}>
          <mesh material={plainMat("#9a5a30", 0.9)} castShadow><sphereGeometry args={[0.045, 14, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2]} /></mesh>
          <mesh position={[0.02, 0.04 + 0.004 * Math.sin(t * 29), 0]} scale={[0.012, 0.03 * diya, 0.012]}><sphereGeometry args={[1, 10, 8]} /><meshBasicMaterial color="#ffd080" /></mesh>
          <pointLight position={[0, 0.15, 0.15]} intensity={diya * (2.4 + 0.25 * Math.sin(t * 23))} distance={5} decay={1.6} color="#ffb060" />
        </group>
      ) : null}
      {moneyBox ? (
        <group position={[-2.35, PLINTH, -0.2]}>
          <mesh material={wood} position={[0, 0.09, 0]} castShadow><boxGeometry args={[0.36, 0.18, 0.26]} /></mesh>
          <mesh material={wood} position={[0, 0.2, -0.13]} rotation={[-1.9, 0, 0]} castShadow><boxGeometry args={[0.36, 0.02, 0.26]} /></mesh>
          <mesh material={basicMat("#140e0a")} position={[0, 0.181, 0]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[0.32, 0.22]} /></mesh>
        </group>
      ) : null}
      {/* sacks of grain */}
      {sacks.slice(0, nSacks).map((s, k) => <mesh key={"sk" + k} position={[s[0], s[1] + 0.27, s[2]]} rotation={[0, k * 0.7, 0]} scale={[0.26, 0.3, 0.24]} material={jute} castShadow receiveShadow><sphereGeometry args={[1, 14, 10]} /></mesh>)}
      {full > 0.3 ? [[-1.85, -0.15], [-4.55, -0.2]].map(([x, z], k) => (
        <group key={"os" + k} position={[x, PLINTH, z]}>
          <mesh material={jute} position={[0, 0.2, 0]} castShadow><cylinderGeometry args={[0.24, 0.26, 0.4, 14, 1, true]} /></mesh>
          <mesh material={plainMat(k ? "#e8d8a0" : "#c89a40", 1)} position={[0, 0.4, 0]} castShadow><sphereGeometry args={[0.235, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2]} /></mesh>
        </group>
      )) : null}
      {night && diya === 0 ? null : null}
    </group>
  );
};
const Mansion: React.FC<{ night: boolean; door: number; t: number }> = ({ night, door, t }) => {
  const plaster = mat("mplaster", () => new THREE.MeshStandardMaterial({ map: mudTex(2, "#ecd2a8"), roughness: 0.95 }));
  const trim = plainMat("#8a2a2a", 0.7);
  const wood = mat("mwood", () => new THREE.MeshStandardMaterial({ map: woodTex(), color: "#a87a50", roughness: 0.7 }));
  const [x, , z] = MANSION;
  return (
    <group>
      <mesh position={[x, 0.075, z + 0.3]} material={plainMat("#c8b8a0", 0.9)} receiveShadow castShadow><boxGeometry args={[5.2, 0.15, 4.2]} /></mesh>
      <mesh position={[x, 1.35, z - 0.2]} material={plaster} castShadow receiveShadow><boxGeometry args={[4.6, 2.4, 3.2]} /></mesh>
      <mesh position={[x, 2.6, z - 0.2]} material={trim} castShadow><boxGeometry args={[4.8, 0.12, 3.4]} /></mesh>
      <mesh position={[x, 3.6, z - 0.4]} material={plaster} castShadow receiveShadow><boxGeometry args={[3.8, 1.9, 2.6]} /></mesh>
      <mesh position={[x, 4.6, z - 0.4]} material={trim} castShadow><boxGeometry args={[4.0, 0.14, 2.8]} /></mesh>
      {[-1.6, -0.55, 0.55, 1.6].map((dx, k) => <mesh key={k} position={[x + dx, 1.3, z + 1.55]} material={plainMat("#f4ead8", 0.6)} castShadow><cylinderGeometry args={[0.1, 0.12, 2.3, 12]} /></mesh>)}
      <mesh position={[x, 2.5, z + 1.55]} material={trim} castShadow><boxGeometry args={[4.0, 0.16, 0.4]} /></mesh>
      {/* arched doorway with two door leaves that close */}
      <mesh position={[x, 1.05, z + 1.405]} material={basicMat(night ? "#e09040" : "#140e0a")}><planeGeometry args={[1.1, 1.8]} /></mesh>
      <mesh position={[x, 1.95, z + 1.41]} material={trim}><torusGeometry args={[0.55, 0.06, 8, 20, Math.PI]} /></mesh>
      {[-1, 1].map((s) => (
        <group key={"dl" + s} position={[x + s * 0.55, 0.15, z + 1.43]} rotation={[0, s * (1 - door) * 1.4, 0]}>
          <mesh position={[-s * 0.275, 0.9, 0]} material={wood} castShadow><boxGeometry args={[0.55, 1.8, 0.05]} /></mesh>
        </group>
      ))}
      {[[-1.5, 1.6], [1.5, 1.6], [-1.0, 3.6], [1.0, 3.6]].map(([dx, y], k) => <mesh key={"w" + k} position={[x + dx, y, (y > 3 ? z + 0.905 : z + 1.405)]} material={basicMat(night ? "#e8a050" : "#2a201a")}><planeGeometry args={[0.6, 0.8]} /></mesh>)}
      {/* bunting and, at night, strings of lamps */}
      {Array.from({ length: 14 }, (_, k) => { const u = k / 13; return <mesh key={"f" + k} position={[x - 2.1 + u * 4.2, 2.35 - Math.sin(u * Math.PI) * 0.25, z + 1.8]} rotation={[0, 0, Math.PI]} material={plainMat(["#d83a2a", "#e8b030", "#2a8a4a"][k % 3], 0.8)}><coneGeometry args={[0.08, 0.18, 3]} /></mesh>; })}
      {night ? Array.from({ length: 20 }, (_, k) => <mesh key={"b" + k} position={[x - 2.3 + (k / 19) * 4.6, 2.72, z + 1.42]}><sphereGeometry args={[0.035, 8, 6]} /><meshBasicMaterial color={k % 2 ? "#ffd070" : "#ff9a40"} /></mesh>) : null}
      {night ? <pointLight position={[x, 2.0, z + 2.6]} intensity={3.0 + 0.2 * Math.sin(t * 3)} distance={8} decay={1.5} color="#ffb060" /> : null}
      {/* low wall and gate posts */}
      {[-1, 1].map((s) => <mesh key={"lw" + s} position={[x + s * 1.75, 0.4, z + 3.25]} material={plaster} castShadow receiveShadow><boxGeometry args={[2.3, 0.8, 0.22]} /></mesh>)}
      {[-1, 1].map((s) => <mesh key={"gp" + s} position={[x + s * 0.55, 0.6, z + 3.25]} material={trim} castShadow><boxGeometry args={[0.24, 1.2, 0.24]} /></mesh>)}
      {/* the chakki's stool in the yard */}
      <mesh position={[STOOL[0], 0.22, STOOL[2]]} material={wood} castShadow><cylinderGeometry args={[0.3, 0.32, 0.44, 16]} /></mesh>
      <mesh position={[STOOL[0], 0.45, STOOL[2]]} material={clothMat("#b8242a", 0)} castShadow><cylinderGeometry args={[0.34, 0.34, 0.03, 18]} /></mesh>
    </group>
  );
};

const Village: React.FC<{ t: number; st: number; mode: Mode; focus: V }> = ({ t, st, mode, focus }) => {
  const { scene, gl } = useThree();
  const L: Light = mode === "world" ? NOON : villageLight(st);
  const night = L === "night";
  const preset = night ? NOON : (L as SkyPreset);
  const bark = useMemo(() => new THREE.MeshStandardMaterial({ map: barkTex(1, 2), roughness: 0.95, color: "#ffffff" }), []);
  const ground = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(60, "#8c7656"), roughness: 1, color: "#ffffff" }), []);
  const lane = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(18, "#a88a66"), roughness: 1, color: "#ffffff" }), []);
  const fieldM = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(6, "#6a4e34"), roughness: 1, color: "#ffffff" }), []);
  const wall = useMemo(() => new THREE.MeshStandardMaterial({ map: mudTex(2), roughness: 1 }), []);
  const thatch = useMemo(() => new THREE.MeshStandardMaterial({ map: strawTex(3), roughness: 1 }), []);
  const nightSky = useMemo(() => nightSkyMat(), []);
  const leaves = useLeaves([
    { c: [-7.0, 4.0, -2.6], r: 1.6, n: 520 }, { c: [-6.2, 4.6, -2.2], r: 1.1, n: 260 },
    { c: [0.2, 4.4, -3.6], r: 1.7, n: 560 }, { c: [1.0, 4.9, -3.3], r: 1.1, n: 260 },
    { c: [8.8, 4.1, -2.9], r: 1.5, n: 480 }, { c: [9.6, 4.6, -2.5], r: 1.0, n: 220 },
  ], 51, 0.22);
  const grass = useGrass(1800, 9, (r) => { const x = -12 + r() * 24, z = -8 + r() * 16; if (z > 0.2 && z < 2.4) return null; if (x > -5.6 && x < -0.8 && z > -3.4 && z < 0.8) return null; if (x > 1.0 && x < 6.3 && z > -4.6 && z < 1.4) return null; return [x, z]; }, 0.26, "#8a9048");
  const weeds = useGrass(700, 13, (r) => { const x = 5.6 + r() * 3.2, z = -2.6 + r() * 2.9; return [x, z]; }, 0.62, "#7a8a3a");
  const light = useMemo(() => { const l = new THREE.DirectionalLight(); l.castShadow = true; l.shadow.mapSize.set(2048, 2048); const c = l.shadow.camera; c.left = -9; c.right = 9; c.top = 9; c.bottom = -9; c.near = 1; c.far = 90; l.shadow.bias = -0.0004; l.shadow.normalBias = 0.02; return l; }, []);
  const sd = night ? new THREE.Vector3(0.35, 0.8, 0.5).normalize() : sunDir(preset);
  light.position.set(focus[0] + sd.x * 35, sd.y * 35, focus[2] + sd.z * 35); light.target.position.set(...focus); light.target.updateMatrixWorld();
  light.intensity = night ? 1.6 : L === DUSK ? 2.4 : L === GOLD ? 3.0 : L === STORM ? 1.1 : L === NOON ? 3.4 : 2.8;
  light.color.set(night ? "#9ab0e0" : L === DUSK ? "#ff9a58" : L === GOLD ? "#ffc890" : L === STORM ? "#c8ccd4" : "#fff4e6");
  if (night) { scene.environment = null; gl.toneMappingExposure = 1.15; }
  const mansion = st >= T.flashRich || mode === "classic" || mode === "world";
  const shopFull = mode === "classic" || mode === "world" || st < T.fate ? 1 : st < T.loss ? 1 - seg(st, T.fate, T.loss) : 0;
  const sway = Math.sin(t * (L === STORM ? 3.5 : 0.9)) * (L === STORM ? 0.03 : 0.006);
  const chakkiOnStool = mansion && !(elderHolding(st, mode)) && (mode === "world" ? false : st < 86.0 || mode === "classic") && !(mode === "classic" && st < T.c2);
  return (
    <group>
      {night ? (
        <>
          <mesh material={nightSky} scale={500}><sphereGeometry args={[1, 32, 16]} /></mesh>
          <mesh position={[120, 140, 380]}><sphereGeometry args={[12, 24, 16]} /><meshBasicMaterial color="#f2eedc" fog={false} /></mesh>
          <fog attach="fog" args={["#141a2c", 12, 60]} />
          <ambientLight intensity={0.75} color="#6a7aaa" />
          <hemisphereLight args={["#5a6a9a", "#20180c", 0.55]} />
        </>
      ) : (
        <>
          <SkyEnv preset={preset} name={presetName(preset)} />
          <fog attach="fog" args={[L === DUSK ? "#c88a68" : L === GOLD ? "#e8c8a0" : L === STORM ? "#8a9098" : "#d8dce0", L === STORM ? 10 : 16, L === STORM ? 55 : 90]} />
          <directionalLight position={[focus[0] - 6, 4, focus[2] + 9]} intensity={L === DUSK ? 0.45 : 0.35} color={L === DUSK ? "#ffb890" : "#e8f0ff"} />
          <hemisphereLight args={[L === DUSK ? "#c87a6a" : L === GOLD ? "#ffd8b0" : L === STORM ? "#8a929c" : "#b8d0f0", "#5a4a30", L === DUSK ? 0.75 : 0.4]} />
        </>
      )}
      <primitive object={light} /><primitive object={light.target} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} material={ground} receiveShadow><planeGeometry args={[220, 220]} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.003, 1.3]} material={lane} receiveShadow><planeGeometry args={[80, 2.0]} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[7.2, 0.004, -1.15]} material={fieldM} receiveShadow><planeGeometry args={[3.4, 3.1]} /></mesh>
      <primitive object={grass} /><primitive object={weeds} />
      <Shop full={shopFull} night={night} t={t} ledger={st >= T.night1 && st < T.past} diya={(st >= T.night1 && st < T.past) || (st >= T.hurt && st < T.theft) ? 1 : 0} moneyBox={st >= T.loss && st < T.theft && mode === "village"} signSwing={L === STORM ? 0.25 * Math.sin(t * 4.5) : 0.02 * Math.sin(t)} />
      {mansion ? <Mansion night={night} door={doorClosed(st)} t={t} /> : (
        <>
          <Hut p={HUT} r={0} wall={wall} thatch={thatch} lit={night} />
          <group position={CHARPAI} rotation={[0, Math.PI / 2, 0]}>
            {[[-0.9, -0.42], [0.9, -0.42], [-0.9, 0.42], [0.9, 0.42]].map(([x, z], k) => <mesh key={k} position={[x, 0.2, z]} material={mat("cw", () => new THREE.MeshStandardMaterial({ map: woodTex(), roughness: 0.9 }))} castShadow><cylinderGeometry args={[0.035, 0.03, 0.4, 8]} /></mesh>)}
            <mesh position={[0, 0.41, 0]} rotation={[-Math.PI / 2, 0, 0]} material={mat("crope", () => new THREE.MeshStandardMaterial({ map: dirtTex(8, "#b49a64"), roughness: 1 }))} castShadow receiveShadow><planeGeometry args={[1.85, 0.88]} /></mesh>
          </group>
        </>
      )}
      {chakkiOnStool ? <group position={[STOOL[0], 0.47, STOOL[2]]}><Chakki spin={0} glow={0.25} /></group> : null}
      {/* trees, well, far huts, hills */}
      {[[-7.0, -2.6], [0.2, -3.6], [8.8, -2.9]].map(([x, z], k) => <mesh key={"tr" + k} position={[x, 1.7, z]} material={bark} castShadow receiveShadow><cylinderGeometry args={[0.2, 0.32, 3.4, 12]} /></mesh>)}
      <group rotation={[sway, 0, sway * 0.7]}><primitive object={leaves} /></group>
      <group position={[0.3, 0, 3.7]}>
        <mesh position={[0, 0.4, 0]} material={wall} castShadow receiveShadow><cylinderGeometry args={[0.7, 0.75, 0.8, 22, 1, true]} /></mesh>
        <mesh position={[0, 0.8, 0]} rotation={[Math.PI / 2, 0, 0]} material={wall} castShadow><torusGeometry args={[0.71, 0.08, 8, 22]} /></mesh>
        <mesh position={[0, 0.78, 0]} rotation={[-Math.PI / 2, 0, 0]} material={basicMat("#0a0806")}><circleGeometry args={[0.66, 22]} /></mesh>
      </group>
      {[[-11, -9, 0.3], [-4.5, -12, -0.2], [12, -10, 0.5], [16, -4, -0.6], [-15, -3, 0.8], [6.5, -13, 0.1]].map(([x, z, r], k) => <Hut key={"fh" + k} p={[x, 0, z]} r={r} wall={wall} thatch={thatch} lit={night} />)}
      {[[-60, -90, 34], [5, -110, 44], [70, -85, 30], [95, 20, 36], [-90, 30, 40]].map(([x, z, r], k) => <mesh key={"hill" + k} position={[x, -r * 0.72, z]} scale={[r * 1.6, r, r]} material={plainMat(night ? "#1a2018" : "#6a7a48", 1)}><sphereGeometry args={[1, 24, 12]} /></mesh>)}
      {L === STORM ? Array.from({ length: 30 }, (_, k) => { const r = rng(400 + k); const u = (t * (0.6 + r() * 0.5) + r()) % 1; return <mesh key={"d" + k} position={[-6 + u * 12, 0.2 + r() * 1.6, -1 + r() * 4]} scale={0.02 + r() * 0.03}><sphereGeometry args={[1, 6, 4]} /><meshStandardMaterial color="#b8a888" transparent opacity={0.35} depthWrite={false} /></mesh>; }) : null}
    </group>
  );
};

// ------------------------------------------------------------------ the sea (night) and the shore (dawn)
const waveH = (x: number, z: number, t: number, amp = 1) => amp * (0.14 * Math.sin(0.55 * x + 1.1 * t) + 0.1 * Math.sin(0.75 * z - 0.8 * t + 1.3) + 0.05 * Math.sin(1.6 * x + 1.2 * z + 2.0 * t));
const waveBump = () => canvasTex("wavebump", 512, (x, n, r) => {
  const img = x.createImageData(n, n);
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    const u = (i / n) * Math.PI * 2, v = (j / n) * Math.PI * 2;
    const h = 0.5 + 0.18 * Math.sin(u * 3 + Math.sin(v * 2) * 1.5) + 0.14 * Math.sin(v * 5 + u * 2) + 0.08 * Math.sin(u * 11 - v * 7) + 0.05 * (r() - 0.5);
    const c = Math.max(0, Math.min(255, h * 255)); const o = (j * n + i) * 4; img.data[o] = img.data[o + 1] = img.data[o + 2] = c; img.data[o + 3] = 255;
  }
  x.putImageData(img, 0, 0);
}, [40, 40], false);
const Sea: React.FC<{ t: number; dawn: boolean }> = ({ t, dawn }) => {
  const { scene, gl } = useThree();
  const uni = useMemo(() => ({ uTime: { value: 0 }, uAmp: { value: 1 } }), []);
  uni.uTime.value = t; uni.uAmp.value = dawn ? 0.45 : 1;
  const water = useMemo(() => {
    const m = new THREE.MeshStandardMaterial({ color: "#0e2c3e", roughness: 0.14, metalness: 0.25, bumpMap: waveBump(), bumpScale: 0.9 });
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uTime = uni.uTime; sh.uniforms.uAmp = uni.uAmp;
      sh.vertexShader = "uniform float uTime;\nuniform float uAmp;\n" + sh.vertexShader.replace("#include <begin_vertex>", `#include <begin_vertex>
        float wx = position.x; float wz = -position.y;
        transformed.z += uAmp * (0.14 * sin(0.55 * wx + 1.1 * uTime) + 0.1 * sin(0.75 * wz - 0.8 * uTime + 1.3) + 0.05 * sin(1.6 * wx + 1.2 * wz + 2.0 * uTime));`);
    };
    return m;
  }, [uni]);
  const bm = water.bumpMap; if (bm) bm.offset.set(t * 0.004, t * 0.006);
  const nightSky = useMemo(() => nightSkyMat(), []);
  const sand = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(30, "#c8b08a"), roughness: 1, color: "#ffffff" }), []);
  const light = useMemo(() => { const l = new THREE.DirectionalLight(); l.castShadow = true; l.shadow.mapSize.set(1024, 1024); const c = l.shadow.camera; c.left = -6; c.right = 6; c.top = 6; c.bottom = -6; c.near = 1; c.far = 80; l.shadow.bias = -0.0005; return l; }, []);
  const focus: V = dawn ? [0, 0, 8] : [0, 0, 0];
  const sd = dawn ? sunDir(DAWN) : new THREE.Vector3(-0.39, 0.16, -0.92).normalize();
  light.position.set(focus[0] + sd.x * 30, Math.max(4, sd.y * 30), focus[2] + sd.z * 30); light.target.position.set(...focus); light.target.updateMatrixWorld();
  light.intensity = dawn ? 2.2 : 2.3; light.color.set(dawn ? "#ffb48a" : "#a8bce8");
  if (!dawn) { scene.environment = null; gl.toneMappingExposure = 1.15; }
  return (
    <group>
      {dawn ? (
        <>
          <SkyEnv preset={DAWN} name="dawn" />
          <fog attach="fog" args={["#e8b8a0", 25, 160]} />
          <hemisphereLight args={["#f0c0b0", "#40506a", 0.5]} />
        </>
      ) : (
        <>
          <mesh material={nightSky} scale={500}><sphereGeometry args={[1, 32, 16]} /></mesh>
          <mesh position={[-125, 42, -295]}><sphereGeometry args={[5.5, 24, 16]} /><meshBasicMaterial color="#f4f0de" fog={false} /></mesh>
          <mesh position={[-125, 42, -296]}><sphereGeometry args={[16, 24, 16]} /><meshBasicMaterial color="#6a7aaa" transparent opacity={0.18} fog={false} depthWrite={false} /></mesh>
          <fog attach="fog" args={["#0e1626", 20, 120]} />
          <ambientLight intensity={0.95} color="#5a6a9a" />
          <hemisphereLight args={["#5a6a9a", "#0a1018", 0.6]} />
        </>
      )}
      <primitive object={light} /><primitive object={light.target} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} material={water} receiveShadow><planeGeometry args={[600, 600, 220, 220]} /></mesh>
      {dawn ? <mesh rotation={[-Math.PI / 2 + 0.035, 0, 0]} position={[0, -0.1, 24]} material={sand} receiveShadow><planeGeometry args={[200, 34]} /></mesh> : null}
      {dawn ? Array.from({ length: 3 }, (_, k) => { const u = ((t * 0.18 + k / 3) % 1); return <mesh key={"foam" + k} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.05 + 0.02 * k, 7.6 + u * 1.6]}><planeGeometry args={[60, 0.14 + 0.2 * (1 - u)]} /><meshBasicMaterial color="#f4f0ea" transparent opacity={0.5 * (1 - u)} depthWrite={false} /></mesh>; }) : null}
    </group>
  );
};
const BOAT_SINK = (t: number) => seg(t, 98.3, 100.5) * 1.7;
const Boat: React.FC<{ t: number }> = ({ t }) => {
  const wood = mat("boatwood", () => new THREE.MeshStandardMaterial({ map: woodTex(), color: "#8a6a4a", roughness: 0.85, side: THREE.DoubleSide }));
  const saltK = seg(t, T.salt + 0.6, T.sink + 1.0);
  const ph = t * 3.2;
  const lantern = t < 99.9 ? 1 : 0;
  return (
    <group>
      <mesh material={wood} scale={[0.75, 0.48, 1.9]} castShadow receiveShadow><sphereGeometry args={[1, 26, 14, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2]} /></mesh>
      <mesh material={wood} position={[0, 0.0, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[0.75, 1.9, 1]} castShadow><torusGeometry args={[1, 0.04, 6, 40]} /></mesh>
      {[-0.45, 0.65].map((z, k) => <mesh key={k} material={wood} position={[0, -0.12, z]} castShadow receiveShadow><boxGeometry args={[1.25, 0.05, 0.28]} /></mesh>)}
      {/* oars, rowing until the salt starts */}
      {[-1, 1].map((s) => { const a = t < T.salt ? Math.sin(ph) * 0.5 : 0.2; return (
        <group key={"oar" + s} position={[s * 0.72, 0.02, -0.35]} rotation={[0, s * (0.15 + a), s * (t < T.salt ? 0.35 + 0.15 * Math.cos(ph) : 0.6)]}>
          <mesh material={wood} position={[s * 0.6, 0, 0]} rotation={[0, 0, Math.PI / 2]} castShadow><cylinderGeometry args={[0.02, 0.02, 1.8, 6]} /></mesh>
          <mesh material={wood} position={[s * 1.4, 0, 0]} castShadow><boxGeometry args={[0.32, 0.02, 0.12]} /></mesh>
        </group>); })}
      {/* lantern on a pole at the stern */}
      <mesh material={wood} position={[0, 0.45, -1.55]} castShadow><cylinderGeometry args={[0.025, 0.025, 1.0, 6]} /></mesh>
      <group position={[0, 0.95, -1.55]}>
        <mesh><boxGeometry args={[0.12, 0.16, 0.12]} /><meshStandardMaterial color="#ffe0a0" emissive="#ffb040" emissiveIntensity={1.5 * lantern} transparent opacity={0.85} /></mesh>
        {lantern ? <pointLight intensity={4.2 + 0.4 * Math.sin(t * 17)} distance={7} decay={1.5} color="#ffb060" /> : null}
      </group>
      {/* the salt: a sack filling, then a growing heap */}
      <mesh material={plainMat("#f4f2ee", 0.9)} position={[0, -0.32 + 0.3 * saltK, 0.25]} scale={[0.62 * (0.6 + 0.4 * saltK), 0.05 + 0.3 * saltK, 1.3 * (0.6 + 0.4 * saltK)]} receiveShadow castShadow><sphereGeometry args={[1, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2]} /></mesh>
    </group>
  );
};

// ------------------------------------------------------------------ gold pouring out of the mill
const COIN_N = 46;
const Coins: React.FC<{ t: number; at: V }> = ({ t, at }) => {
  const t0 = T.ask + 0.5;
  const gold = plainMat("#e8b830", 0.25, 0.95);
  const pile = clamp((t - t0) / 2.4);
  return (
    <group position={at}>
      <mesh material={gold} position={[0.55, 0.0, 0.05]} scale={[0.32 * pile + 0.01, 0.2 * pile + 0.005, 0.32 * pile + 0.01]} castShadow receiveShadow><coneGeometry args={[1, 1, 24]} /></mesh>
      {Array.from({ length: COIN_N }, (_, k) => {
        const s = t0 + k * 0.055; const u = (t - s) / 0.55; if (u < 0) return null;
        const r = rng(700 + k); const land: V = [0.42 + (r() - 0.5) * 0.4, 0.02 + 0.15 * pile * r(), (r() - 0.5) * 0.4];
        const uu = clamp(u); const p: V = [lerp(0.28, land[0], uu), 0.12 + 0.35 * Math.sin(uu * Math.PI) * (1 - uu * 0.3) + (land[1] - 0.12) * uu, lerp(0, land[2], uu)];
        return <mesh key={k} material={gold} position={p} rotation={[uu * 6 + k, k, uu * 4]} castShadow><cylinderGeometry args={[0.03, 0.03, 0.006, 14]} /></mesh>;
      })}
    </group>
  );
};

// ------------------------------------------------------------------ camera
type Cam = { pos: V; target: V; fov: number; roll?: number };
const headOf = (a: Act): V => { const f = fwd(a.yaw, 0.02); return [a.pos[0] + f[0], a.pos[1] + (lerp(1.6, 0.92, a.p.sit) - 0.06 * a.p.spine) * a.s, a.pos[2] + f[1]]; };
function camAt(t: number, st: number, mode: Mode): Cam {
  const el = elderAt(t, st, mode); const yo = youngAt(t, st, mode);
  const eh = el ? headOf(el) : ([0, 1.6, 0] as V); const yh = yo ? headOf(yo) : ([0, 1.5, 0] as V);
  if (mode === "classic") {
    if (st < T.c2) return { pos: [2.6, 1.3, 3.9], target: add(el!.pos, [0, 1.05, 0]), fov: 42, roll: 0.08 };
    if (st < T.c3) { const k = seg(st, T.c2, T.c3); return { pos: lerp3([0.2, 1.7, 4.6], [-0.3, 1.6, 4.0], k), target: [-3.0, 1.2, -0.7], fov: 44 }; }
    return { pos: [eh[0] + 0.3, eh[1] - 0.05, eh[2] + 1.1], target: eh, fov: 30 };
  }
  if (mode === "world") { const k = seg(t, T.world, T.hidden); return { pos: lerp3([0.4, 1.55, 4.6], [0.3, 1.5, 4.0], k), target: [0.1, 1.3, 1.6], fov: 42 }; }
  if (mode === "sea") {
    const by = waveH(0, 0, t) + 0.3 - BOAT_SINK(t);
    if (t < T.salt) { const k = seg(t, T.sea, T.salt); return { pos: lerp3([2.8, 1.7, 5.6], [2.3, 1.5, 4.8], k), target: [0, by + 0.45, -0.3], fov: 42 }; }
    if (t < T.mantra) return { pos: [0.9, by + 1.15, 1.7], target: [0, by + 0.75, 0.15], fov: 38 };
    if (t < T.flow) return { pos: [-0.8, by + 1.05, 1.25], target: [0, by + 0.65, 0.2], fov: 40, roll: -0.08 };
    if (t < T.sink) return { pos: [1.2, by + 0.7, 2.0], target: [0, by + 0.1, 0.5], fov: 40 };
    const k = seg(t, T.sink, T.world); return { pos: lerp3([3.0, 1.2, 4.6], [3.8, 1.5, 5.6], k), target: [0, Math.max(-0.4, by + 0.35), -0.3], fov: 44 };
  }
  if (mode === "dawnsea") { const k = seg(t, T.hidden, T.life); return { pos: lerp3([1.6, 2.0, 3.4], [1.3, 1.8, 2.9], k), target: [0.35, 0.0, 0.25], fov: 40 }; }
  if (mode === "shore") {
    if (t < T.follow) { const k = seg(t, T.forgot2, T.follow); return { pos: lerp3([1.9, 1.45, 9.35], [1.6, 1.45, 9.25], k), target: add(yh, [0, -0.1, -0.15]), fov: 34 }; }
    const k = seg(t, T.follow, END); return { pos: lerp3([0.6, 1.6, 13.5], [0.9, 2.6, 16.5], k), target: [0, 1.0, 2], fov: 46 };
  }
  if (mode === "memory") {
    if (t < T.refuse2) return { pos: [-3.75, 1.9, -1.8], target: [-2.9, 1.45, 0.5], fov: 40 };
    if (t < T.mem3) return { pos: [eh[0] + 0.25, eh[1] - 0.05, eh[2] + 1.15], target: eh, fov: 30 };
    return { pos: [-1.0, 1.35, 2.7], target: add(yo ? yo.pos : FRONT, [0, 1.15, 0]), fov: 40 };
  }
  // the village story
  if (st < T.arrive) return { pos: [1.9, 1.7, 5.3], target: [-1.6, 1.15, 0.3], fov: 44 };
  if (st < T.refuse) return { pos: [-2.25, 1.75, 2.0], target: [-3.2, 1.7, -0.9], fov: 38 };
  if (st < T.selfish) return { pos: [eh[0] + 0.15, eh[1] - 0.05, eh[2] + 1.25], target: eh, fov: 30 };
  if (st < T.leave + 0.1) return { pos: [-3.65, 2.0, -1.7], target: [-2.9, 1.45, 0.6], fov: 40 };
  if (st < T.work) return { pos: [-2.4, 1.4, 3.8], target: yo ? add(yo.pos, [0, 1.0, 0]) : [0, 1, 1], fov: 40 };
  if (st < T.night1) return { pos: [0.7, 1.35, 3.0], target: el ? add(el.pos, [0, 1.15, 0]) : [-1.5, 1.2, 0.5], fov: 42 };
  if (st < T.past) return { pos: [-2.45, 1.9, 0.5], target: [-3.15, 1.62, -0.8], fov: 38 };
  if (st < T.again) return { pos: [-1.55, 1.6, 1.6], target: [-3.05, 1.5, -0.2], fov: 38 };
  if (st < T.again2) return { pos: [-1.2, 1.4, 2.7], target: [-2.95, 1.35, 0.4], fov: 40 };
  if (st < T.again3) return { pos: [-4.7, 1.5, 2.3], target: [-3.0, 1.4, 0.0], fov: 40 };
  if (st < T.think) return { pos: [-2.5, 1.8, 0.95], target: [-3.1, 1.55, -0.6], fov: 38 };
  if (st < T.because) { const k = seg(st, T.think, T.because); return { pos: [eh[0] + 0.2, eh[1] - 0.06, eh[2] + lerp(1.15, 0.85, k)], target: eh, fov: 30 }; }
  if (st < T.watch2) return { pos: [2.1, 1.8, 3.5], target: [5.5, 0.55, -0.4], fov: 40 };
  if (st < T.thought) return { pos: orbit(eh, el!.yaw, 0.25, 1.1, -0.05), target: eh, fov: 30 };
  if (st < T.feet) return { pos: [eh[0] + 0.3, eh[1] - 0.12, eh[2] + 1.3], target: add(eh, [0, -0.12, 0]), fov: 34 };
  if (st < T.find) { const p = yo!.pos; return { pos: [p[0] - 0.7, 0.26, p[2] + 1.55], target: [p[0] + 0.25, 0.22, p[2]], fov: 40 }; }
  if (st < T.ask) return { pos: [7.35, 0.85, -0.2], target: [6.8, 0.5, 1.25], fov: 40 };
  if (st < T.rich) return { pos: [8.0, 0.9, 1.95], target: [6.95, 0.38, 0.95], fov: 38 };
  if (st < T.fate) return { pos: [1.0, 1.6, 5.4], target: [3.6, 1.7, -1.0], fov: 46 };
  if (st < T.loss) return { pos: [-1.7, 0.45, 2.7], target: [-3.2, 2.7, -0.1], fov: 44 };
  if (st < T.goAsk) { const k = seg(st, T.loss, T.goAsk); return { pos: lerp3([-1.7, 1.05, 2.3], [-2.0, 0.95, 1.8], k), target: [-3.0, 0.75, -0.4], fov: 40 }; }
  if (st < T.said) return { pos: add(el!.pos, [-0.9, 1.45, 2.4]), target: add(el!.pos, [0.3, 1.2, -0.4]), fov: 40 };
  if (st < T.need) return { pos: [2.95, 1.75, 2.45], target: [3.6, 1.6, -0.3], fov: 36 };
  if (st < T.why2) return { pos: orbit(yh, yo ? yo.yaw : Math.PI, -0.2, 1.05, -0.02), target: yh, fov: 30 };
  if (st < T.back) return { pos: [4.3, 0.95, 0.6], target: [3.6, 1.5, -0.35], fov: 42 };
  if (st < T.hurt) return { pos: [6.2, 0.6, 3.3], target: el ? add(el.pos, [0, 1.0, 0]) : [1, 1, 1.3], fov: 40 };
  if (st < T.years) return { pos: [-1.55, 1.2, 2.4], target: [-3.0, 0.75, -0.25], fov: 40 };
  if (st < T.forgot) return { pos: [eh[0] + 0.25, eh[1] - 0.22, eh[2] + 0.9], target: add(eh, [0, -0.05, 0]), fov: 30 };
  if (st < T.theft) return { pos: [-4.2, 1.1, 0.6], target: [1.5, 1.2, -0.3], fov: 40 };
  return { pos: [5.9, 0.85, 2.15], target: el ? add(el.pos, [0, 0.95, 0]) : [4.4, 0.9, 0.5], fov: 42, roll: 0.14 };
}
const CameraRig: React.FC<{ cam: Cam }> = ({ cam }) => {
  const { camera } = useThree();
  const c = camera as THREE.PerspectiveCamera;
  c.position.set(...cam.pos); c.fov = cam.fov; c.near = 0.03; c.far = 2000;
  c.up.set(Math.sin(cam.roll ?? 0), Math.cos(cam.roll ?? 0), 0); c.lookAt(new THREE.Vector3(...cam.target)); c.updateProjectionMatrix();
  return null;
};

const Person: React.FC<{ a: Act }> = ({ a }) => a.lying ? (
  <group position={a.pos} rotation={[0, a.yaw, 0]} scale={a.s}><group rotation={[-Math.PI / 2, 0, 0]}><Human look={a.look} p={a.p} /></group></group>
) : (
  <group position={a.pos} rotation={[0, a.yaw, 0]} scale={a.s}><Human look={a.look} p={a.p} /></group>
);

const Scene: React.FC<{ t: number }> = ({ t }) => {
  const mode = modeAt(t);
  const st = storyTime(t);
  const cam = camAt(t, st, mode);
  if (mode === "sea" || mode === "dawnsea" || mode === "shore") {
    const el = elderAt(t, st, mode); const yo = youngAt(t, st, mode);
    const by = waveH(0, 0, t) + 0.3 - BOAT_SINK(t); const pitch = 0.05 * Math.sin(t * 0.9) + 0.22 * seg(t, 97.5, 100.2); const roll = 0.06 * Math.sin(t * 1.1 + 1);
    const spin = t < T.salt ? 0 : (t - T.salt) * (t < T.mantra ? 6 : 11);
    return (
      <>
        <CameraRig cam={cam} />
        <Sea t={t} dawn={mode !== "sea"} />
        {mode === "sea" ? (
          <group position={[0, by, 0]} rotation={[pitch, 0, roll]}>
            <Boat t={t} />
            {el ? <group position={onTop([0, 0, -0.45], -0.07, 1)} rotation={[0, el.yaw, 0]}><Human look={el.look} p={el.p} /></group> : null}
            <group position={[0, -0.09, 0.62]}><Chakki spin={spin} glow={t >= T.salt ? 0.7 : 0.25} s={0.85} /></group>
            {t >= T.salt && t < 100.3 ? Array.from({ length: 16 }, (_, k) => { const u = ((t * 2.2 + k / 16) % 1); return <mesh key={"st" + k} position={[0.24 - u * 0.05, -0.0 - u * 0.25, 0.62 + (k % 3 - 1) * 0.02]} scale={0.012}><boxGeometry args={[1, 1, 1]} /><meshStandardMaterial color="#f8f8f4" /></mesh>; }) : null}
          </group>
        ) : null}
        {mode === "dawnsea" ? (
          <>
            <mesh position={[0, waveH(0, 0, t, 0.45) + 0.04, 0]} rotation={[-Math.PI / 2, 0, 0.4]}><circleGeometry args={[1.2, 32]} /><meshBasicMaterial color="#ffc060" transparent opacity={0.4 + 0.08 * Math.sin(t * 3)} blending={THREE.AdditiveBlending} depthWrite={false} /></mesh>
            <pointLight position={[0, 0.5, 0]} intensity={2.5} distance={3} decay={1.6} color="#ffc060" />
            <mesh position={[0.6, waveH(0.6, 0.45, t, 0.45) + 0.03, 0.45]} rotation={[-Math.PI / 2 + 0.05 * Math.sin(t), 0, 0.7]}><planeGeometry args={[0.6, 1.3]} /><meshStandardMaterial color="#c8a060" emissive="#20160a" roughness={0.95} side={THREE.DoubleSide} /></mesh>
          </>
        ) : null}
        {yo ? <Person a={yo} /> : null}
      </>
    );
  }
  const el = elderAt(t, st, mode); const yo = youngAt(t, st, mode);
  const focus: V = cam.target[0] > 0.8 ? [4.2, 0, 0] : [-2.4, 0, 0];
  const holding = elderHolding(st, mode) && el;
  return (
    <>
      <CameraRig cam={cam} />
      <Village t={t} st={st} mode={mode} focus={focus} />
      {el ? <Person a={el} /> : null}
      {holding ? (() => { const f = fwd(el!.yaw, 0.36); return <group position={[el!.pos[0] + f[0], el!.pos[1] + 0.92, el!.pos[2] + f[1]]} rotation={[0.2, el!.yaw, 0]}><Chakki spin={0} glow={0.35} s={0.75} /></group>; })() : null}
      {yo ? <Person a={yo} /> : null}
      {villagersAt(t, st, mode).map((v, k) => <Person key={"v" + k} a={v} />)}
      {mode === "village" && st >= T.find - 0.2 && st < T.flashRich ? (
        <group position={FIND}>
          <Chakki spin={st >= T.ask ? (st - T.ask) * 6 : 0} glow={st < T.ask ? 0.5 + 0.5 * seg(st, T.find, T.find + 1.0) : 1} s={0.8} />
          {st >= T.ask ? <Coins t={st} at={[0, 0, 0]} /> : null}
        </group>
      ) : null}
      {mode === "village" && st >= T.flashRich - 0.05 && st < T.flashRich + 0.9 ? Array.from({ length: 40 }, (_, k) => { const r = rng(900 + k); const u = (st - T.flashRich) / 0.9; return <mesh key={"sp" + k} position={[3.6 + (r() - 0.5) * 5 * u, 0.5 + r() * 4 * u, -1.0 + (r() - 0.5) * 3 * u]} scale={0.03 * (1 - u)}><sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color="#fff0b0" transparent opacity={1 - u} blending={THREE.AdditiveBlending} depthWrite={false} /></mesh>; }) : null}
    </>
  );
};

// ------------------------------------------------------------------ film overlays
const Grain: React.FC<{ frame: number; amount: number }> = ({ frame, amount }) => (
  <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: amount, pointerEvents: "none" }}>
    <svg width="1080" height="1920"><filter id={"g" + frame}><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={frame} /><feColorMatrix type="saturate" values="0" /></filter>
      <rect width="1080" height="1920" filter={`url(#g${frame})`} /></svg>
  </AbsoluteFill>
);
const CUTS = [T.c2, T.c3, T.arrive, T.refuse, T.selfish, T.leave + 0.1, T.work, T.night1, T.past, T.again, T.again2, T.again3, T.think, T.because, T.watch2, T.thought, T.feet, T.find, T.ask, T.rich, T.fate, T.loss, T.goAsk,
  T.said, T.need, T.why2, T.back, T.hurt, T.years, T.forgot, T.theft, T.salt, T.mantra, T.flow, T.sink, T.hidden, T.refuse2, T.mem3, T.follow];

export const Chakki3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const mode = modeAt(t);
  const sub = SUBS.find(([a, b]) => t >= a && t < b);
  const old = mode === "classic" || mode === "world";
  const rewinding = t >= T.rewind && t < T.truth;
  const past = isPast(t);
  const flick = old ? 0.94 + 0.06 * Math.sin(frame * 2.7) * Math.sin(frame * 1.3) : 1;
  const filter = old ? `sepia(0.55) saturate(0.7) contrast(1.12) brightness(${flick})` : past ? "sepia(0.25) saturate(0.85) contrast(1.02) brightness(1.04)" : "saturate(1.06) contrast(1.05)";
  const jitter = old ? `translate(${(Math.sin(frame * 7.1) * 2) | 0}px, ${(Math.sin(frame * 3.3) * 2) | 0}px)` : rewinding ? `translateX(${(Math.sin(frame * 11) * 8) | 0}px) skewX(${Math.sin(frame * 5) * 2}deg)` : "none";
  let dip = 0; for (const c of CUTS) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.08);
  const dream = Math.max(0, 1 - Math.abs(t - T.past) / 0.35, 1 - Math.abs(t - T.think) / 0.3, 1 - Math.abs(t - T.life) / 0.35, 1 - Math.abs(t - T.forgot2) / 0.3);
  const whiteFlash = Math.max(0, 1 - Math.abs(t - T.truth) / 0.12, 1 - Math.abs(t - T.flashRich) / 0.15, 1 - Math.abs(t - T.world) / 0.12);
  const blackDip = Math.max(0, 1 - Math.abs(t - T.sea) / 0.3, 1 - Math.abs(t - T.hidden) / 0.3, 1 - Math.abs(t - T.theft) / 0.25, 1 - Math.abs(t - T.fate) / 0.2);
  const fade = Math.min(clamp(t / 0.4), clamp((END - t) / 1.4));
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter: `${filter} blur(${(dream * 6 + (rewinding ? 1 : 0)).toFixed(2)}px)`, transform: jitter }}>
        <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
          <Scene t={t} />
        </ThreeCanvas>
      </AbsoluteFill>
      {past ? <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(255,220,160,0) 45%, rgba(120,70,20,0.45) 100%)" }} /> : null}
      {old ? (
        <>
          {Array.from({ length: 3 }, (_, k) => { const r = rng(frame * 7 + k); return r() < 0.5 ? <div key={k} style={{ position: "absolute", left: r() * 1080, top: 0, width: 1 + r() * 2, height: 1920, background: "rgba(40,30,20,0.35)" }} /> : null; })}
          <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 40%, rgba(30,18,8,0.7) 100%)" }} />
        </>
      ) : null}
      {rewinding ? (
        <>
          <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, rgba(255,255,255,0.06) 0px, rgba(255,255,255,0.06) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px)" }} />
          {Array.from({ length: 3 }, (_, k) => { const r = rng(frame * 13 + k); return <div key={k} style={{ position: "absolute", left: 0, right: 0, top: r() * 1900, height: 8 + r() * 40, background: "rgba(255,255,255,0.18)", transform: `translateX(${(r() - 0.5) * 60}px)` }} />; })}
          <div style={{ position: "absolute", top: 140, left: 80, fontSize: 70, color: "rgba(255,255,255,0.9)", fontFamily: "sans-serif", fontWeight: 900, letterSpacing: -8 }}>◀◀</div>
        </>
      ) : null}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 58%, rgba(0,0,0,0.42) 100%)" }} />
      <Grain frame={frame} amount={old ? 0.22 : 0.08} />
      {sub ? (
        <div style={{ position: "absolute", top: 1300, left: 60, right: 60, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 54, lineHeight: 1.4, color: "#faf6ee", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill", textShadow: "0 4px 14px rgba(0,0,0,0.75)" }}>{sub[2]}</div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: whiteFlash * 0.85 }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.35, blackDip) }} />
    </AbsoluteFill>
  );
};
