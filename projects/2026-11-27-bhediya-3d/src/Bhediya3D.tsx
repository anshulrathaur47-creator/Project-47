import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, getInputProps, useCurrentFrame } from "remotion";
import {
  Branch, HLook, HPose, Human, SPose, Sheep, SkyEnv, SkyPreset, WPose, Wolf, barkTex, basicMat, clamp, dirtTex, hRest, lerp, mat, mudTex,
  nightSkyMat, plainMat, rng, sRest, seg, smooth, strawTex, sunDir, useGrass, useLeaves, wRest, woodTex,
} from "./Real";

// "उस मशहूर कहानी में वो लड़का बार-बार चिल्लाता था कि भेड़िया आया…" (ReelAudio-95086): the boy who cried wolf, the true version.
// The wolf came every time; it only ran because the villagers came. The day they stopped coming, it did not need to run.
export const DURATION = 3750; // 125 s (narration ends 123.2 s, then a held last shot)
const FPS = 30;
const END = DURATION / FPS;
// the 3D canvas size (CSS-scaled to 1080x1920; subtitles and overlays stay at full resolution)
const CW = Number((getInputProps() as { cw?: number }).cw ?? 1080); const CH = Math.round(CW * 16 / 9);
type V = [number, number, number];

const SUBS: [number, number, string][] = [
  [0.0, 4.36, "उस मशहूर कहानी में वो लड़का बार-बार चिल्लाता था कि भेड़िया आया।"],
  [4.36, 7.98, "सबने बोला कि वो झूठ बोलकर गाँव वालों को परेशान करता था,"],
  [7.98, 10.2, "पर सच्चाई तो कुछ और ही थी।"],
  [10.2, 13.7, "दरअसल, जब भी वो चिल्लाता था कि भेड़िया आया,"],
  [13.7, 17.4, "उस वक्त भेड़िया सच में उसकी भेड़ों पर हमला करने आता था।"],
  [17.45, 21.6, "लेकिन गाँव वालों को अपनी तरफ आते देख भेड़िया जंगल में भाग जाता था"],
  [21.65, 23.7, "और उसकी भेड़ें बच जाती थीं।"],
  [23.72, 26.16, "पहली बार जब गाँव वालों ने उसकी आवाज़ सुनी,"],
  [26.18, 29.56, "तो सब अपना काम छोड़कर उसकी मदद करने दौड़े चले आए।"],
  [29.58, 32.38, "लेकिन जब उन्होंने देखा कि भेड़िया वहाँ नहीं है,"],
  [32.4, 35.32, "तो उन्हें लगा कि लड़का उनके साथ मज़ाक कर रहा है।"],
  [35.34, 39.52, "किसी ने कहा कि इस लड़के को काम नहीं है, इसलिए दूसरों को परेशान करता है,"],
  [39.54, 43.52, "तो किसी ने कहा कि अगली बार इसकी बातों पर बिल्कुल भरोसा मत करना।"],
  [43.54, 47.6, "दूसरी बार भी जब लड़के ने चिल्लाया, तो गाँव वाले फिर दौड़कर आए।"],
  [47.7, 50.7, "लेकिन भेड़िया इस बार भी उन्हें देखकर भाग चुका था।"],
  [50.78, 55.4, "अब गाँव वालों को यकीन हो गया था कि वो लड़का सिर्फ उनका समय बर्बाद कर रहा है।"],
  [55.48, 57.3, "उन्होंने आपस में तय कर लिया"],
  [57.32, 59.48, "कि अब चाहे वो कितनी भी जोर से चिल्लाए,"],
  [59.5, 61.5, "कोई उसकी मदद करने नहीं जाएगा।"],
  [61.58, 63.88, "लेकिन जिस दिन भेड़िया दोबारा आया"],
  [63.92, 66.2, "और उसकी सारी भेड़ों पर टूट पड़ा,"],
  [66.3, 69.3, "तो उस दिन लड़का पहले से भी ज़्यादा जोर से चिल्लाया।"],
  [69.36, 70.86, "उसने गाँव की तरफ देखा।"],
  [70.9, 74.15, "उसे उम्मीद थी कि इस बार भी लोग उसकी मदद करने आएंगे।"],
  [74.2, 77.25, "लेकिन गाँव वाले अपने घरों में बैठे सोच रहे थे"],
  [77.6, 79.5, "कि वो फिर से कोई मज़ाक कर रहा होगा।"],
  [79.9, 82.95, "किसी ने कहा, \"आज इसे खुद ही अपनी शरारत का मज़ा लेने दो।\""],
  [83.0, 86.6, "तो किसी ने उसकी आवाज़ सुनकर भी दरवाज़ा बंद कर लिया।"],
  [86.66, 90.94, "उधर भेड़िया एक-एक करके उसकी सारी भेड़ों को मारता जा रहा था"],
  [90.96, 94.54, "और लड़का बेबस होकर उन्हें बचाने की कोशिश कर रहा था।"],
  [94.56, 97.9, "लेकिन जब उसे समझ आया कि इस बार कोई नहीं आने वाला,"],
  [97.92, 101.88, "तो वो एक पत्थर पर बैठकर अपनी भेड़ों को मरते हुए देखने लगा।"],
  [101.9, 106.66, "पूरी दुनिया ने कहानी बनाई कि उस लड़के को उसके झूठ की सज़ा मिली।"],
  [106.68, 110.4, "लेकिन सच तो ये था कि उसने हर बार सच बोला था।"],
  [110.92, 112.46, "भेड़िया हर बार आया था।"],
  [112.48, 116.28, "बस हर बार गाँव वालों को आते देखकर भाग जाता था"],
  [116.3, 120.24, "और जिस दिन गाँव वालों ने उसकी बातों पर विश्वास करना छोड़ दिया,"],
  [120.26, 123.4, "उस दिन भेड़िए को भागने की ज़रूरत ही नहीं पड़ी।"],
];
// story beats (Whisper times)
const T = {
  c2: 2.2, c3: 4.36, c4: 6.3, c5: 8.0, rewind: 8.7, truth: 9.4,
  boy1: 10.2, shout1: 12.0, stalk1: 13.7, snarl1: 15.6, vill1: 17.5, flee1: 19.6, safe1: 21.7,
  hear: 23.72, run: 26.18, arrive: 29.58, noWolf: 32.4, scold: 35.34, trust: 39.54,
  second: 43.54, run2: 45.6, flee2: 47.6, decide: 50.78, elder: 55.48, nobody: 59.5,
  dusk: 61.58, attack: 63.92, scream: 66.3, look: 69.36, hope: 70.9, homes: 74.2, joke: 77.6, letHim: 79.9, door: 83.0,
  kill: 86.66, helpless: 90.96, nobodyCame: 94.56, rock: 97.92, world: 101.9, truth2: 106.68, came: 110.92, fled: 112.48, fled2: 114.4,
  night: 116.3, noNeed: 120.26, last: 123.3,
};

// ------------------------------------------------------------------ the people (new faces for this reel)
const BOY: HLook = { skin: "#8e5a3a", hair: "#16110d", hairStyle: "kid", top: "#2a6a8a", topStyle: "shirt", bottom: "#6a5038", bottomStyle: "shorts", turban: "#d8402a", worn: 0.6 };
const FARMER: HLook = { skin: "#7c4e30", hair: "#1a1612", hairStyle: "short", top: "#8a8466", topStyle: "shirt", bottom: "#e8e0cc", bottomStyle: "dhoti", turban: "#f0ece0", moustache: "#1e1a16", stubble: "#2e2a26", chappal: "plain", worn: 0.5 };
const WOMAN: HLook = { skin: "#93603e", hair: "#141010", hairStyle: "bun", top: "#2a6a3a", topStyle: "blouse", bottom: "#d89a20", bottomStyle: "saree", pallu: "#e0a830", bindi: true, chappal: "plain", lip: "#7a3a34" };
const YOUNG: HLook = { skin: "#8a5a3a", hair: "#1a1612", hairStyle: "short", top: "#a8342a", topStyle: "shirt", bottom: "#3a3a48", bottomStyle: "pants", chappal: "plain" };
const OLD: HLook = { skin: "#7a4e34", hair: "#d8d4cc", hairStyle: "bald", top: "#c8b090", topStyle: "kurta", bottom: "#ece6d6", bottomStyle: "dhoti", turban: "#e8e4d8", stubble: "#d8d4cc", moustache: "#e0dcd4", chappal: "plain" };
const ELDER2: HLook = { skin: "#80553a", hair: "#d8d4cc", hairStyle: "short", top: "#e8e8e0", topStyle: "kurta", bottom: "#e8e2d2", bottomStyle: "dhoti", turban: "#d87a20", moustache: "#d8d4cc", chappal: "plain" };
const S_BOY = 0.74;

// ------------------------------------------------------------------ places: pasture at the origin, forest to +x, village ~28 m down the path at +z
const ROCK: V = [-1.8, 0, -0.6]; const ROCK_TOP = 0.44;
const VILLAGE_EYE: V = [-1.4, 1.3, 29];
const BOY_A: V = [-0.5, 0, 1.0]; const BOY_B: V = [-0.45, 0, 1.55]; const BOY_C: V = [0.3, 0, -1.9]; const BOY_D: V = [-1.1, 0, 0.1];
const WB1: V = [5.0, 0, -1.3]; const STALK1: V = [2.9, 0, -1.1]; const FLEE1: V = [8.8, 0, 0.9]; const FLEE1_GAP: V = [4.3, 0, 0.7];
const WB2: V = [3.7, 0, -5.3]; const STALK2: V = [2.3, 0, -3.5]; const FLEE2: V = [5.6, 0, -9.0];
const PATH_V: V = [-1.3, 0, 23.0]; const PATH_P: V = [-0.6, 0, 4.2];
const HUTS: V[] = [[-5.5, 0, 29.5], [-1.2, 0, 30.5], [3.2, 0, 29.6]];
const FAR_HUTS: [number, number, number][] = [[-9.5, 32.5, 0.5], [7.2, 33, -0.5], [-3.5, 35, 0.2], [11, 29, -0.9], [-12.5, 27.5, 1.0]];
const doorOf = (k: number): V => [HUTS[k][0] + 0.4, 0, HUTS[k][2] - 1.2];
const NEEM: V = [-3.6, 0, 25.0];
const WELL: V = [-4.7, 0, 24.5];
const CHARPAI_P: V = [-3.2, 0, 23.75];     // panchayat charpai
const CHARPAI_H1: V = [-3.3, 0, 27.6];     // farmer's charpai at dusk
const fwd = (yaw: number, d: number): [number, number] => [Math.sin(yaw) * d, Math.cos(yaw) * d];
const side = (yaw: number, d: number): [number, number] => [Math.cos(yaw) * d, -Math.sin(yaw) * d];
const add = (a: V, b: V): V => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const lerp3 = (a: V, b: V, k: number): V => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
const orbit = (c: V, yaw: number, off: number, d: number, h: number): V => [c[0] + Math.sin(yaw + off) * d, c[1] + h, c[2] + Math.cos(yaw + off) * d];
const yawTo = (from: V, to: V) => Math.atan2(to[0] - from[0], to[2] - from[2]);
const dist = (a: V, b: V) => Math.hypot(a[0] - b[0], a[2] - b[2]);
const angLerp = (a: number, b: number, k: number) => { let d = b - a; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2; return a + d * k; };
const YAW_V = (p: V) => yawTo(p, VILLAGE_EYE);

// piecewise-linear walk along points, constant speed
function along(pts: V[], k: number): { pos: V; yaw: number } {
  const lens = pts.slice(1).map((p, i) => dist(pts[i], p)); const total = lens.reduce((a, b) => a + b, 0) || 1;
  let d = clamp(k) * total; let i = 0;
  while (i < lens.length - 1 && d > lens[i]) { d -= lens[i]; i++; }
  const u = lens[i] > 0 ? d / lens[i] : 0;
  return { pos: lerp3(pts[i], pts[i + 1] ?? pts[i], u), yaw: yawTo(pts[i], pts[i + 1] ?? pts[i]) };
}

// ------------------------------------------------------------------ sheep
const SHEEP: { base: V; yaw: number; face: string; s: number }[] = [
  { base: [0.2, 0, 0.15], yaw: 0.4, face: "#3a302a", s: 1 }, { base: [1.15, 0, -0.45], yaw: -1.2, face: "#e0d4c0", s: 1 },
  { base: [-0.25, 0, -0.95], yaw: 2.2, face: "#3a302a", s: 0.95 }, { base: [1.55, 0, 0.75], yaw: 0.9, face: "#3a302a", s: 1.05 },
  { base: [0.65, 0, 1.35], yaw: -0.3, face: "#e0d4c0", s: 0.95 }, { base: [-0.95, 0, -0.15], yaw: 1.6, face: "#3a302a", s: 1 },
  { base: [2.0, 0, -1.05], yaw: -2.4, face: "#e0d4c0", s: 1 }, { base: [-0.2, 0, 0.85], yaw: 0.2, face: "#e0d4c0", s: 0.6 },
];
const ENTRY: V = [1.0, 0, -0.4];
const SCATTER: V[] = SHEEP.map((sh) => { const d = Math.hypot(sh.base[0] - ENTRY[0], sh.base[2] - ENTRY[2]) || 1; const k = 2.0 / d;
  return [clamp(sh.base[0] + (sh.base[0] - ENTRY[0]) * k, -3.5, 3.8), 0, clamp(sh.base[2] + (sh.base[2] - ENTRY[2]) * k, -3.6, 3.2)] as V; });
const KILL_ORDER = [6, 1, 3, 4, 0, 7, 5, 2];
const KILL_T = (k: number) => 87.4 + k * 1.3;
const WOLF_KILL_PATH: V[] = [[1.6, 0, -0.9], ...KILL_ORDER.map((i) => { const s = SCATTER[i]; return [s[0] + 0.35, 0, s[2] - 0.25] as V; })];
function wolfKillPos(t: number): { pos: V; yaw: number; moving: boolean } {
  if (t < KILL_T(0) - 0.7) return { pos: WOLF_KILL_PATH[0], yaw: yawTo(WOLF_KILL_PATH[0], WOLF_KILL_PATH[1]), moving: false };
  for (let k = 0; k < KILL_ORDER.length; k++) {
    const t1 = KILL_T(k), t0 = t1 - 0.7;
    const a = WOLF_KILL_PATH[k], b = WOLF_KILL_PATH[k + 1];
    if (t < t0) return { pos: a, yaw: yawTo(a, b), moving: false };
    if (t < t1) return { pos: lerp3(a, b, smooth((t - t0) / 0.7)), yaw: yawTo(a, b), moving: true };
  }
  const last = WOLF_KILL_PATH[WOLF_KILL_PATH.length - 1];
  return { pos: last, yaw: yawTo(last, SCATTER[KILL_ORDER[KILL_ORDER.length - 1]]), moving: false };
}

// ------------------------------------------------------------------ modes and story time
const modeAt = (t: number) => t < T.truth ? "classic" : t < T.world ? "story" : t < T.truth2 ? "world" : t < T.night ? "reveal" : "night";
function storyTime(t: number): number {
  if (t >= T.rewind && t < T.truth) return Math.max(1.0, T.rewind - (t - T.rewind) * 11);
  if (t >= T.truth2 && t < T.came) return 13.2 + (t - T.truth2) * 0.9;
  if (t >= T.came && t < T.fled) return 43.8 + (t - T.came);
  if (t >= T.fled && t < T.fled2) return 19.0 + (t - T.fled);
  if (t >= T.fled2 && t < T.night) return 47.4 + (t - T.fled2);
  return t;
}

// ------------------------------------------------------------------ props
const STICK = (k = 0) => <mesh key={"stick" + k} material={mat("stickm", () => new THREE.MeshStandardMaterial({ map: woodTex(), roughness: 0.85 }))} position={[0, -0.12, 0.02]} castShadow><cylinderGeometry args={[0.016, 0.019, 1.25, 8]} /></mesh>;
const HOE = <group><mesh material={plainMat("#6a4a2a", 0.9)} position={[0, -0.2, 0.02]} castShadow><cylinderGeometry args={[0.016, 0.018, 1.2, 8]} /></mesh><mesh material={plainMat("#5a5a5c", 0.45, 0.7)} position={[0, -0.78, 0.1]} castShadow><boxGeometry args={[0.16, 0.02, 0.15]} /></mesh></group>;
const POT = <mesh material={plainMat("#9a5030", 0.85)} position={[0.05, 0.02, 0.1]} castShadow><sphereGeometry args={[0.15, 18, 12]} /></mesh>;
const HAY = <mesh material={mat("haym", () => new THREE.MeshStandardMaterial({ map: strawTex(1), roughness: 1 }))} position={[0, 0.06, 0]} castShadow><cylinderGeometry args={[0.2, 0.24, 0.28, 12]} /></mesh>;

// ------------------------------------------------------------------ who does what, when
type Act = { look: HLook; pos: V; yaw: number; p: HPose; s: number };
const shout = (p: HPose, t: number, k = 1) => { p.armL = [-1.2, 0.5]; p.armR = [-1.2, -0.5]; p.elbowL = -2.3; p.elbowR = -2.3; p.mouth = (0.65 + 0.3 * Math.abs(Math.sin(t * 7))) * k; p.headPitch = -0.18; p.brow = 1; p.eyes = 1.12; p.smile = -0.3; };
const run = (p: HPose, t: number, speed = 11) => { p.walk = 1; p.phase = t * speed; p.spine = 0.22; p.mouth = 0.25; p.armL = [-0.2, 0.1]; p.armR = [-0.2, -0.1]; p.elbowL = -1.3; p.elbowR = -1.3; };
const walkP = (p: HPose, t: number) => { p.walk = 1; p.phase = t * 6.5; };
const wag = (p: HPose, t: number) => { p.armR = [-1.45, -0.1]; p.elbowR = -1.35 + 0.28 * Math.sin(t * 10); p.anger = 1; p.mouth = 0.3 + 0.25 * Math.abs(Math.sin(t * 8)); p.brow = 0; p.smile = -0.4; };
const crossArms = (p: HPose) => { p.armL = [-0.55, 0.32]; p.elbowL = -1.85; p.armR = [-0.55, -0.32]; p.elbowR = -1.85; };
const hips = (p: HPose) => { p.armL = [0.25, -0.6]; p.elbowL = -1.25; p.armR = [0.25, 0.6]; p.elbowR = -1.25; };
const laugh = (p: HPose, t: number) => { p.smile = 1; p.mouth = 0.35 + 0.2 * Math.abs(Math.sin(t * 9)); p.eyes = 0.3; p.headPitch = -0.15 + 0.05 * Math.sin(t * 9); };
const onTop = (p: V, h: number, s: number): V => [p[0], h - 0.2 * s, p[2]];   // seat a sitting rig on a surface of height h

function boyAt(t: number, st: number, mode: string): Act {
  const p = hRest(); p.handR = STICK();
  const S = S_BOY;
  if (mode === "classic") {   // the version everyone tells: a grinning prankster on the rock
    const pos: V = [ROCK[0], ROCK_TOP - 0.02, ROCK[2]]; const yaw = YAW_V(ROCK);
    p.handR = null;
    if (st < T.c2) { shout(p, st); p.smile = 0.6; p.brow = 0.3; p.eyes = 1; }
    else { laugh(p, st); p.armL = [-0.7, 0.35]; p.elbowL = -1.6; if (st > T.c3) { p.armR = [-1.4, -0.15]; p.elbowR = -0.1; } }
    return { look: BOY, pos, yaw, p, s: S };
  }
  if (mode === "night" || (mode === "world") || st >= T.rock + 1.6) {   // on the rock, alone
    const k = mode === "night" ? 1 : seg(st, T.rock + 1.6, T.rock + 2.3);
    p.handR = null; p.sit = k; p.spine = lerp(0.1, 0.55, k) + 0.03 * Math.sin(st * 7); p.headPitch = mode === "night" ? 0.55 : 0.3; p.brow = 1; p.eyes = mode === "night" ? 0.05 : 0.35;
    p.smile = -0.8; p.mouth = mode === "night" ? 0 : 0.15 + 0.12 * Math.abs(Math.sin(st * 4)); p.tear = 1;
    p.armL = [-1.0, 0.3]; p.armR = [-1.0, -0.3]; p.elbowL = 0.9; p.elbowR = 0.9;
    return { look: BOY, pos: lerp3([ROCK[0], 0, ROCK[2] + 0.55], onTop(ROCK, ROCK_TOP, S), k), yaw: 0.35, p, s: S };
  }
  // the truth, first time
  if (st < T.hear) {
    if (st < T.shout1) {   // idle with his flock, then notices something at the forest edge
      const notice = seg(st, 11.2, 11.6); p.headYaw = lerp(0.3 * Math.sin(st * 0.8), -0.9, notice); p.smile = lerp(0.3, -0.2, notice); p.eyes = lerp(0.9, 1.15, notice); p.brow = notice;
      p.elbowR = -0.5;
      return { look: BOY, pos: BOY_A, yaw: 0.9, p, s: S };
    }
    if (st < T.stalk1) { shout(p, st); p.handR = null; return { look: BOY, pos: BOY_A, yaw: angLerp(0.9, YAW_V(BOY_A), seg(st, T.shout1, T.shout1 + 0.3)), p, s: S }; }
    if (st < T.vill1) {   // faces the wolf, stick up, still shouting
      p.armR = [-2.5, -0.25]; p.elbowR = -0.4 + 0.25 * Math.sin(st * 6); p.brow = 1; p.eyes = 1.12; p.mouth = 0.55 + 0.3 * Math.abs(Math.sin(st * 6)); p.smile = -0.4; p.armL = [-0.6, -0.3]; p.elbowL = -0.4;
      return { look: BOY, pos: BOY_A, yaw: yawTo(BOY_A, STALK1), p, s: S };
    }
    if (st < T.safe1) {   // looks back: the villagers are coming; the wolf runs
      p.headYaw = st < T.flee1 ? -1.3 : -0.2; p.brow = 0.6; p.eyes = 1.05; p.smile = st < T.flee1 ? 0 : 0.5; p.mouth = st < T.flee1 ? 0.3 : 0.2;
      if (st > T.flee1) { p.armL = [-1.4, -0.9]; p.elbowL = -0.1; }
      return { look: BOY, pos: BOY_A, yaw: yawTo(BOY_A, STALK1), p, s: S };
    }
    // relief: pats the lamb
    p.spine = 0.35; p.armL = [-0.75, 0.1]; p.elbowL = -0.3 + 0.12 * Math.sin(st * 5); p.smile = 0.8; p.eyes = 0.75; p.headPitch = 0.2;
    return { look: BOY, pos: BOY_A, yaw: yawTo(BOY_A, SHEEP[7].base) + 0.3, p, s: S };
  }
  if (st < T.second) {   // the villagers arrive; he points at the forest, pleads, gets scolded
    const yaw = yawTo(BOY_B, [-0.1, 0, 3.0]);
    if (st < T.noWolf) { p.armL = [-0.35, -1.45]; p.elbowL = -0.1; p.mouth = 0.4 + 0.2 * Math.sin(st * 8); p.brow = 1; p.eyes = 1.1; p.headYaw = st < 31 ? -0.9 : -0.2; }
    else if (st < T.scold) { p.armL = [-1.0, -0.45]; p.armR = [-1.0, 0.45]; p.elbowL = -0.5; p.elbowR = -0.5; p.brow = 1; p.mouth = 0.35 + 0.15 * Math.sin(st * 7); p.smile = -0.4; }
    else if (st < T.trust) { p.headPitch = 0.35; p.eyes = 0.55; p.brow = 1; p.smile = -0.5; p.spine = 0.12; }
    else { p.headPitch = 0.2; p.eyes = 0.7; p.brow = 1; p.smile = -0.6; p.tear = seg(st, 40.5, 42.5) * 0.7; p.headYaw = -0.4 * seg(st, 41.4, 43); }
    return { look: BOY, pos: BOY_B, yaw, p, s: S };
  }
  if (st < T.decide) {   // the second time
    if (st < T.run2) { shout(p, st); p.handR = null; return { look: BOY, pos: BOY_C, yaw: YAW_V(BOY_C), p, s: S }; }
    if (st < 49.4) { p.armR = [-2.6, -0.2]; p.elbowR = -0.4 + 0.3 * Math.sin(st * 7); p.brow = 1; p.eyes = 1.12; p.mouth = 0.5 + 0.3 * Math.abs(Math.sin(st * 6)); return { look: BOY, pos: BOY_C, yaw: yawTo(BOY_C, STALK2), p, s: S }; }
    p.armL = [-0.3, -1.45]; p.elbowL = -0.1; p.brow = 1; p.mouth = 0.45 + 0.2 * Math.sin(st * 9); p.headYaw = 1.2;
    return { look: BOY, pos: BOY_C, yaw: yawTo(BOY_C, STALK2), p, s: S };
  }
  if (st < T.dusk) { p.elbowR = -0.5; return { look: BOY, pos: BOY_A, yaw: 0.6, p, s: S }; }   // (not seen: the village decides)
  // the last day
  if (st < T.attack) { const k = seg(st, 62.4, 63.0); p.headYaw = lerp(0, -0.8, k); p.brow = k; p.eyes = lerp(0.9, 1.15, k); p.mouth = 0.3 * k; return { look: BOY, pos: BOY_D, yaw: 0.8, p, s: S }; }
  if (st < T.scream) { p.armR = [-2.6, -0.25]; p.elbowR = -0.3; p.brow = 1; p.eyes = 1.15; p.mouth = 0.7; p.smile = -0.5; return { look: BOY, pos: BOY_D, yaw: yawTo(BOY_D, ENTRY), p, s: S }; }
  if (st < T.look) { shout(p, st, 1.15); p.handR = null; p.tear = seg(st, 67, 68.5); return { look: BOY, pos: BOY_D, yaw: YAW_V(BOY_D), p, s: S }; }
  if (st < T.kill) { p.brow = 0.7; p.eyes = 1.1; p.smile = 0.05; p.mouth = 0.12; p.tear = 1; p.headPitch = -0.08; p.elbowR = -0.4; return { look: BOY, pos: BOY_D, yaw: YAW_V(BOY_D), p, s: S }; }
  if (st < T.nobodyCame) {   // runs after the wolf, waving the stick
    const w = wolfKillPos(st - 1.0).pos; const dir = yawTo(w, BOY_D); const f = fwd(dir, 1.1); const target: V = [w[0] + f[0], 0, w[2] + f[1]];
    const k = seg(st, T.kill, T.kill + 0.8); const pos = lerp3(BOY_D, target, k);
    run(p, st, 12); p.armR = [-2.4, -0.2]; p.elbowR = -0.5 + 0.6 * Math.sin(st * 9); p.mouth = 0.6; p.brow = 1; p.tear = 1; p.smile = -0.5;
    return { look: BOY, pos, yaw: yawTo(pos, wolfKillPos(st).pos), p, s: S };
  }
  // stops, looks at the empty path, drops the stick, walks to the rock
  const stop = (() => { const w = wolfKillPos(T.nobodyCame - 1.0).pos; const f = fwd(yawTo(w, BOY_D), 1.1); return [w[0] + f[0], 0, w[2] + f[1]] as V; })();
  if (st < T.rock) {
    const k = seg(st, T.nobodyCame, T.nobodyCame + 0.6); p.brow = 1; p.eyes = lerp(1.1, 0.8, seg(st, 95.6, 96.6)); p.tear = 1; p.smile = -0.7; p.mouth = 0.15;
    p.handR = st < 96.2 ? STICK() : null; p.armR = st < 96.2 ? [lerp(-2.4, -0.2, k), -0.1] : [0, -0.1];
    return { look: BOY, pos: stop, yaw: angLerp(yawTo(stop, wolfKillPos(st).pos), YAW_V(stop), k), p, s: S };
  }
  const k = seg(st, T.rock, T.rock + 1.5); walkP(p, st); p.walk = k < 1 ? 1 : 0; p.handR = null; p.headPitch = 0.3; p.brow = 1; p.eyes = 0.5; p.tear = 1; p.smile = -0.7;
  const seat: V = [ROCK[0], 0, ROCK[2] + 0.55];
  return { look: BOY, pos: lerp3(stop, seat, k), yaw: k < 1 ? yawTo(stop, seat) : 0.35, p, s: S };
}

function villagersAt(t: number, st: number, mode: string): Act[] {
  const out: Act[] = [];
  const P = () => hRest();
  if (mode === "classic") {
    if (st < T.c3) return out;
    const spots: V[] = [[-1.2, 0, 1.0], [-0.3, 0, 1.3], [-2.25, 0, 1.15]];
    const looks = [FARMER, WOMAN, YOUNG];
    spots.forEach((sp, i) => {
      const p = P(); const start: V = [-0.6 + (i - 1) * 0.5, 0, 4.4];
      const k = seg(st, T.c3, T.c3 + 1.3); let pos = lerp3(start, sp, k); let yaw = k < 1 ? yawTo(start, sp) : yawTo(sp, ROCK);
      if (k < 1) { walkP(p, st); p.handR = i === 1 ? null : STICK(i); }
      else if (st < T.c5) { wag(p, st + i); p.handL = i === 1 ? null : null; }
      else { const k2 = seg(st, T.c5, T.c5 + 0.4); yaw = angLerp(yawTo(sp, ROCK), yawTo(sp, start), k2); walkP(p, st); pos = lerp3(sp, start, seg(st, T.c5 + 0.3, T.c5 + 3)); p.anger = 0.6; p.headYaw = 0.6 * (1 - k2); }
      out.push({ look: looks[i], pos, yaw, p, s: i === 1 ? 0.92 : 0.98 });
    });
    return out;
  }
  if (mode === "night") return out;
  if (mode === "world") {   // the story the world tells: smug, arms crossed
    const spots: [HLook, V, number][] = [[FARMER, [-0.5, 0, 3.4], 0.98], [WOMAN, [0.45, 0, 3.7], 0.92], [YOUNG, [-1.45, 0, 3.75], 0.98], [OLD, [1.2, 0, 4.4], 0.95]];
    spots.forEach(([look, pos], i) => { const p = P(); crossArms(p); p.smile = 0.45; p.brow = -0.2; p.headYaw = 0.12 * Math.sin(t * 2.5 + i); p.headPitch = -0.05;
      if (i === 0 && t > 103.5) { wag(p, t); p.smile = 0.3; p.anger = 0.5; }
      out.push({ look, pos, yaw: yawTo(pos, ROCK), p, s: spots[i][2] }); });
    return out;
  }
  // first time, seen from the pasture: coming up the path
  if (st >= T.vill1 && st < T.hear) {
    [FARMER, WOMAN, YOUNG].forEach((look, i) => { const p = P(); const k = seg(st, T.vill1 + i * 0.2, T.hear - 0.6);
      const pos: V = [lerp(-1.25, -0.7, k) + (i - 1) * 0.55, 0, lerp(15.5, 4.6, k) + i * 0.5];
      if (k < 1) { run(p, st + i); p.handR = i === 1 ? null : STICK(i); p.armR = i === 1 ? p.armR : [-0.5, -0.1]; } else { hips(p); }
      out.push({ look, pos, yaw: Math.PI, p, s: i === 1 ? 0.92 : 0.98 }); });
    return out;
  }
  // in the village: at work, they hear, drop everything and run
  if (st >= T.hear && st < T.arrive) {
    const work: [HLook, V, number, number][] = [[FARMER, [1.7, 0, 23.4], -1.3, 0.98], [WOMAN, [-4.05, 0, 23.85], 0.9, 0.92], [YOUNG, [-0.6, 0, 25.7], 0.3, 0.98]];
    work.forEach(([look, w, wy, s], i) => {
      const p = P();
      if (st < T.run) {
        const hearK = i === 0 ? seg(st, 24.3, 24.7) : seg(st, 25.15 + (i - 1) * 0.2, 25.55 + (i - 1) * 0.2);
        if (i === 0) { p.handR = HOE; p.armR = [lerp(-0.9 + 0.55 * Math.sin(st * 4), -0.4, hearK), -0.2]; p.elbowR = -0.6; p.spine = lerp(0.3 + 0.08 * Math.sin(st * 4), 0.05, hearK); }
        if (i === 1) { p.handL = POT; p.armL = [0.05, -0.45]; p.elbowL = -1.3; }
        if (i === 2) { p.handR = HAY; p.armR = [-2.9, -0.35]; p.elbowR = -2.2; }
        p.headYaw = lerp(0, angLerp(0, yawTo(w, PATH_P) - wy, 1), hearK) * 0.9; p.brow = hearK; p.eyes = lerp(0.9, 1.12, hearK); p.mouth = 0.2 * hearK;
        out.push({ look, pos: w, yaw: wy, p, s });
      } else {
        const k = (st - T.run - i * 0.15) / 3.2; const route = along([w, [PATH_V[0] + (i - 1) * 0.6, 0, PATH_V[2] - i * 0.7], [PATH_V[0] + (i - 1) * 0.6 + 0.3, 0, 10]], clamp(k));
        if (k > 0) run(p, st + i, 12); else p.brow = 1;
        out.push({ look, pos: route.pos, yaw: k > 0 ? route.yaw : wy, p, s });
      }
    });
    return out;
  }
  // first time: arrival at the pasture, no wolf, scolding, leaving
  if (st >= T.arrive && st < T.second) {
    const spots: [HLook, V, number][] = [[FARMER, [-0.2, 0, 2.75], 0.98], [WOMAN, [0.55, 0, 3.05], 0.92], [YOUNG, [-1.05, 0, 3.0], 0.98]];
    spots.forEach(([look, sp, s], i) => {
      const p = P(); const start: V = [sp[0] - 0.2, 0, 5.2 + i * 0.4];
      const k = seg(st, T.arrive, T.arrive + 1.1 + i * 0.15);
      let pos = lerp3(start, sp, k); let yaw = yawTo(sp, BOY_B);
      if (k < 1) { run(p, st + i, 9); p.walk = 1 - k * 0.5; }
      else if (st < T.noWolf) { p.headYaw = 0.6 * Math.sin((st - i) * 1.3); p.spine = 0.1; p.mouth = 0.3; p.brow = 0.5; hips(p); }
      else if (st < T.scold) { p.brow = -0.2; p.anger = 0.5; p.smile = -0.2; p.eyes = 0.8; hips(p); if (i === 2) { crossArms(p); p.smile = 0.3; } }
      else if (st < T.trust) { if (i === 0) wag(p, st); else { crossArms(p); p.anger = 0.4; } }
      else {
        if (i === 1) { p.armR = [-1.0, 0.3]; p.elbowR = -0.6 + 0.2 * Math.sin(st * 6); p.mouth = 0.3 + 0.2 * Math.abs(Math.sin(st * 8)); p.anger = 0.5; p.headYaw = -0.6; }
        const kk = seg(st, 41.4 + i * 0.2, 43.4); if (kk > 0) { walkP(p, st); yaw = angLerp(yaw, yawTo(sp, start), seg(st, 41.4, 41.8)); pos = lerp3(sp, [sp[0], 0, sp[2] + 3], kk); }
      }
      out.push({ look, pos, yaw, p, s });
    });
    return out;
  }
  // second time: two of them come running again, slower, annoyed
  if (st >= T.run2 && st < T.decide) {
    [FARMER, YOUNG].forEach((look, i) => { const p = P(); const k = seg(st, T.run2 + i * 0.3, 49.6);
      const pos: V = [lerp(-1.2, -0.3, k) + i * 0.7, 0, lerp(13.5, 3.2, k)];
      if (k < 1) run(p, st + i, 9.5); else { hips(p); p.anger = 0.7; p.smile = -0.4; p.headYaw = 0.5 * Math.sin(st * 1.5 + i); }
      out.push({ look, pos, yaw: k < 1 ? Math.PI : yawTo(pos, BOY_C), p, s: 0.98 }); });
    return out;
  }
  // the panchayat under the neem
  if (st >= T.decide && st < T.dusk) {
    const old = P(); old.sit = 1; old.spine = 0.1; old.armL = [-0.9, 0.2]; old.elbowL = 0.9; old.brow = 0.4; old.anger = 0.35;
    if (st > T.elder - 0.3 && st < T.nobody + 1.5) { old.armR = [-1.2, -0.25]; old.elbowR = -1.1 + 0.35 * Math.sin(st * 5); old.mouth = 0.25 + 0.25 * Math.abs(Math.sin(st * 10)); }
    if (st > T.nobody) { old.armR = [-1.0, -0.6]; old.elbowR = -0.2; old.headYaw = 0.25 * Math.sin(st * 3); }
    out.push({ look: OLD, pos: onTop([CHARPAI_P[0] - 0.4, 0, CHARPAI_P[2]], 0.43, 0.95), yaw: Math.PI, p: old, s: 0.95 });
    const e2 = P(); e2.sit = 1; e2.spine = 0.12; e2.armL = [-0.9, 0.2]; e2.armR = [-0.9, -0.2]; e2.elbowL = 0.9; e2.elbowR = 0.9; e2.headPitch = 0.08 + (st > T.nobody ? 0.12 * Math.max(0, Math.sin(st * 6)) : 0); e2.brow = 0.3;
    out.push({ look: ELDER2, pos: onTop([CHARPAI_P[0] + 0.45, 0, CHARPAI_P[2]], 0.43, 0.95), yaw: Math.PI - 0.2, p: e2, s: 0.95 });
    const stand: [HLook, V, number][] = [[FARMER, [-2.2, 0, 22.85], 0.98], [WOMAN, [-4.2, 0, 22.9], 0.92], [YOUNG, [-2.55, 0, 22.15], 0.98]];
    stand.forEach(([look, pos, s], i) => { const p = P(); p.brow = 0.2; p.anger = 0.5; p.smile = -0.3;
      if (st < T.elder) { if (i === 0) { p.armR = [-1.1, -0.2]; p.elbowR = -0.9 + 0.3 * Math.sin(st * 6); p.mouth = 0.3 + 0.2 * Math.abs(Math.sin(st * 9)); } else hips(p); }
      else { crossArms(p); p.headPitch = st > T.nobody - 1 ? 0.08 + 0.14 * Math.max(0, Math.sin(st * 6 + i)) : 0; }
      out.push({ look, pos, yaw: yawTo(pos, [CHARPAI_P[0], 0, CHARPAI_P[2]]), p, s }); });
    return out;
  }
  // the last evening, at home
  if (st >= T.homes - 0.2 && st < T.kill) {
    const f = P(); f.sit = 1; f.spine = 0.12; f.armL = [-0.9, 0.2]; f.armR = [-0.9, -0.2]; f.elbowL = 0.9; f.elbowR = 0.9; f.headYaw = st > 75.3 ? -0.5 : 0; f.brow = st > 75.3 ? 0.3 : 0;
    if (st > T.joke) { f.smile = 0.6; f.headYaw = -0.2 + 0.28 * Math.sin(st * 6); f.mouth = 0.12; f.brow = -0.2; }
    out.push({ look: FARMER, pos: onTop(CHARPAI_H1, 0.43, 0.98), yaw: Math.PI - 0.15, p: f, s: 0.98 });
    const y = P(); y.sit = 1; y.spine = 0.15; y.armL = [-0.9, 0.2]; y.elbowL = 0.9; y.headYaw = 0.5;
    if (st > T.letHim && st < T.door + 0.5) { laugh(y, st); y.armR = [-1.25, 0.35]; y.elbowR = -0.9 + 0.45 * Math.sin(st * 8); y.headYaw = 0.6; }
    out.push({ look: YOUNG, pos: [-0.55, 0, 28.6], yaw: Math.PI - 0.6, p: y, s: 0.98 });
    const w = P(); w.sit = 1; w.spine = 0.2; w.armL = [-1.1, 0.2]; w.elbowL = 0.6; w.armR = [-1.1, -0.2]; w.elbowR = 0.6; w.headYaw = -0.6; w.smile = st > T.letHim ? 0.6 : 0.1; w.eyes = 0.8;
    out.push({ look: WOMAN, pos: [-1.65, 0, 28.55], yaw: Math.PI + 0.5, p: w, s: 0.92 });
    {   // the old man in his doorway, who shuts the door
      const o = P(); o.headYaw = st < 83.9 ? -0.45 : 0; o.brow = 0.5; o.anger = st > 83.6 ? 0.6 : 0.2; o.smile = -0.3; o.mouth = st > 83.3 && st < 83.9 ? 0.2 : 0;
      const d = doorOf(2); const turn = seg(st, 83.9, 84.3); const k = seg(st, 84.3, 84.95);
      if (k > 0 && k < 1) walkP(o, st);
      if (st < 84.92) out.push({ look: OLD, pos: [d[0] + 0.05, 0, d[2] - 0.45 + 0.42 * k], yaw: angLerp(Math.PI, 0, turn), p: o, s: 0.95 });
    }
    return out;
  }
  return out;
}
const doorAngle = (st: number, mode: string) => mode === "night" ? 0 : st >= T.homes - 0.2 && st < T.kill ? lerp(-1.45, 0, seg(st, 84.95, 85.7)) : st >= T.kill && st < T.world + 5 ? 0 : -1.45;

function wolfAt(t: number, st: number, mode: string): { pos: V; yaw: number; p: WPose; glow: number } | null {
  const p = wRest();
  if (mode === "classic" || mode === "world") return null;
  if (mode === "night") {
    if (t < T.noNeed - 0.3) return null;
    const a: V = [2.6, 0, -2.3], b: V = [0.75, 0, 0.55];
    const k = seg(t, T.noNeed - 0.3, 122.6); p.walk = k < 1 ? 1 : 0; p.phase = t * 5; p.tail = 0.15; p.headPitch = 0.05;
    if (t > 122.4) p.headYaw = 0.9 * seg(t, 122.4, 122.9);
    return { pos: lerp3(a, b, k), yaw: yawTo(a, b), p, glow: 1.1 };
  }
  // first time
  if (st >= T.truth - 0.1 && st < T.safe1) {
    if (st < T.stalk1) { p.crouch = 1; p.headPitch = -0.1; p.ears = 0; p.eyes = 0.8; return { pos: add(WB1, [0.15, 0, 0]), yaw: yawTo(WB1, [2.4, 0, 0.3]), p, glow: st < T.boy1 ? 0.8 : 0.25 }; }
    if (st < T.snarl1) { const k = seg(st, T.stalk1, T.snarl1); p.crouch = 0.85; p.walk = 0.8; p.phase = st * 5.5; p.headPitch = 0.05; return { pos: lerp3(add(WB1, [0.15, 0, 0]), STALK1, k), yaw: yawTo(WB1, STALK1), p, glow: 0.25 }; }
    if (st < T.vill1) { p.crouch = 0.6; p.mouth = 0.85; p.ears = 0.6; p.headPitch = -0.1; p.tail = -0.3; const k = seg(st, T.snarl1, T.vill1); return { pos: lerp3(STALK1, add(STALK1, [-0.25, 0, 0.05]), k), yaw: yawTo(STALK1, SHEEP[6].base), p, glow: 0.25 }; }
    if (st < T.flee1) { const k = seg(st, T.vill1 + 0.6, T.vill1 + 1.2); p.crouch = 0.3; p.headYaw = 1.1 * k; p.ears = 1; p.mouth = 0.3 * (1 - k); p.tail = -0.8; return { pos: add(STALK1, [-0.25, 0, 0.05]), yaw: yawTo(STALK1, SHEEP[6].base), p, glow: 0.25 }; }
    const k = clamp((st - T.flee1) / 1.7); p.run = 1; p.phase = st * 13; p.tail = -0.5; p.ears = 1;
    const from = add(STALK1, [-0.25, 0, 0.05]); const turn = seg(st, T.flee1, T.flee1 + 0.35); const r = along([from, FLEE1_GAP, FLEE1], smooth(k) * 0.85 + k * 0.15);
    return { pos: r.pos, yaw: angLerp(yawTo(STALK1, SHEEP[6].base), r.yaw, turn), p, glow: 0.25 };
  }
  // second time
  if (st >= T.second && st < T.decide - 1.5) {
    if (st < 46.5) { const k = seg(st, T.second, 46.5); p.crouch = 0.8; p.walk = 0.8; p.phase = st * 5.5; return { pos: lerp3(WB2, STALK2, k), yaw: yawTo(WB2, STALK2), p, glow: 0.2 }; }
    if (st < T.flee2) { p.crouch = 0.6; p.mouth = 0.8; p.ears = 0.6; return { pos: STALK2, yaw: yawTo(STALK2, BOY_C), p, glow: 0.2 }; }
    const k = clamp((st - T.flee2 - 0.3) / 1.8); const turn = seg(st, T.flee2, T.flee2 + 0.5); p.crouch = 0.3 * (1 - turn); p.headYaw = 0.9 * (1 - turn) * seg(st, T.flee2, T.flee2 + 0.2); p.ears = 1; p.tail = -0.6;
    if (k > 0) { p.run = 1; p.phase = st * 13; }
    return { pos: lerp3(STALK2, FLEE2, smooth(k)), yaw: angLerp(yawTo(STALK2, BOY_C), yawTo(STALK2, FLEE2), turn), p, glow: 0.2 };
  }
  // the last day: walks out boldly, charges, takes them one by one
  if (st >= T.dusk && st < T.world) {
    if (st < T.attack) { const k = seg(st, T.dusk, T.attack); p.walk = 1; p.phase = st * 5; p.headPitch = -0.05; p.tail = 0.1; return { pos: lerp3(WB1, [3.0, 0, -0.9], k), yaw: yawTo(WB1, [3.0, 0, -0.9]), p, glow: 0.9 }; }
    if (st < T.attack + 1.4) { const k = seg(st, T.attack, T.attack + 1.4); p.run = 1; p.phase = st * 13; p.mouth = 0.7; p.ears = 0.6; return { pos: lerp3([3.0, 0, -0.9], ENTRY, k), yaw: yawTo([3.0, 0, -0.9], ENTRY), p, glow: 0.9 }; }
    if (st < KILL_T(0) - 0.7) { const k = seg(st, T.attack + 1.4, KILL_T(0) - 0.7); p.crouch = 0.4; p.walk = 0.6; p.phase = st * 4; p.mouth = 0.5; p.ears = 0.5; return { pos: lerp3(ENTRY, WOLF_KILL_PATH[0], k), yaw: yawTo(ENTRY, WOLF_KILL_PATH[0]) + 0.6 * Math.sin(st * 0.4), p, glow: 0.9 }; }
    const w = wolfKillPos(st); if (w.moving) { p.run = 1; p.phase = st * 13; p.mouth = 0.6; } else { p.crouch = 0.25; p.headPitch = 0.35; p.mouth = 0.2; }
    return { pos: w.pos, yaw: w.yaw, p, glow: 0.9 };
  }
  return null;
}

function sheepAt(i: number, t: number, st: number, mode: string): SPose & { pos: V; yaw: number } {
  const sh = SHEEP[i]; const p = sRest();
  const lift = Math.pow(Math.max(0, Math.sin(st * 0.7 + i * 1.9)), 4);
  p.graze = 0.85 - 0.75 * lift; p.headYaw = 0.25 * Math.sin(st * 0.5 + i); p.mouth = p.graze > 0.6 ? Math.abs(Math.sin(st * 6 + i)) : 0;
  let pos: V = [sh.base[0] + 0.06 * Math.sin(st * 0.2 + i), 0, sh.base[2] + 0.06 * Math.cos(st * 0.17 + i)]; let yaw = sh.yaw + 0.15 * Math.sin(st * 0.3 + i);
  if (mode === "classic") return { ...p, pos, yaw };
  const startle = (a: number, b: number, from: V) => { const k = seg(st, a, a + 0.3) * (1 - seg(st, b, b + 1.5)); if (k <= 0) return;
    p.startle = k; p.graze = lerp(p.graze, -0.1, k); p.mouth = 0; const away = yawTo(from, sh.base); const d = 0.45 * seg(st, a, a + 1.0); const f = fwd(away, d);
    pos = [pos[0] + f[0], 0, pos[2] + f[1]]; yaw = angLerp(yaw, away, k); if (st < a + 1.0) { p.walk = 1; p.phase = st * 10; } };
  if (st < T.second) startle(T.snarl1 - 0.1, T.safe1, STALK1);
  else if (st < T.dusk) startle(46.4, 49.5, STALK2);
  if (st >= T.attack || mode === "night" || mode === "world") {
    const at = T.attack + 0.15 * i; const k = mode === "night" || mode === "world" ? 1 : seg(st, at, at + 1.6);
    const away = yawTo(ENTRY, sh.base);
    pos = lerp3(pos, SCATTER[i], k); yaw = angLerp(yaw, away, Math.min(1, k * 3));
    if (k > 0 && k < 1) { p.walk = 1; p.phase = st * 13; }
    p.startle = 1; p.graze = -0.15; p.mouth = 0;
    if (k >= 1) { p.headYaw = 0.5 * Math.sin(st * 3 + i); yaw += 0.08 * Math.sin(st * 9 + i); }   // trembling, huddled
    const order = KILL_ORDER.indexOf(i); const kt = KILL_T(order);
    if (mode === "night" || mode === "world" || st >= kt) { p.fallen = mode === "night" || mode === "world" ? 1 : seg(st, kt, kt + 0.35); p.eyes = 1 - p.fallen; p.walk = 0; p.headYaw = 0; p.startle = 0; }
  }
  return { ...p, pos, yaw };
}

// ------------------------------------------------------------------ light presets
const NOON: SkyPreset = { sunElev: 58, sunAz: 205, turbidity: 3, rayleigh: 2.2, exposure: 0.5, env: 0.9 };
const MORN: SkyPreset = { sunElev: 22, sunAz: 300, turbidity: 4, rayleigh: 1.3, exposure: 0.5, env: 0.9 };
const GOLD: SkyPreset = { sunElev: 10, sunAz: 200, turbidity: 8, rayleigh: 2.4, exposure: 0.48, env: 0.75 };
const DUSK: SkyPreset = { sunElev: 3, sunAz: 95, turbidity: 10, rayleigh: 3.0, exposure: 0.8, env: 0.7 };
const presetAt = (st: number, mode = "") => mode === "world" ? NOON : st < T.truth ? NOON : st < T.second ? MORN : st < T.decide ? NOON : st < T.dusk ? GOLD : DUSK;
const presetName = (p: SkyPreset) => p === NOON ? "noon" : p === MORN ? "morn" : p === GOLD ? "gold" : "dusk";

// ------------------------------------------------------------------ the world
const FOREST: [number, number, number][] = [[7.2, -3.5, 1.0], [8.6, 0.8, 1.15], [9.4, -6.8, 1.1], [7.6, 3.6, 0.95], [10.8, -2.0, 1.2], [11.6, 3.4, 1.05], [12.4, -8.6, 1.15],
  [6.8, -9.2, 1.0], [13.6, 0.2, 1.2], [10.2, 6.8, 1.0], [3.0, -11.5, 1.1], [-1.5, -12.5, 1.05], [-5.0, -11.0, 1.15], [0.8, -14.5, 1.2], [-8.5, -9.5, 1.0], [15.5, -4.5, 1.25]];
const BUSH_BLOBS = [{ c: [5.25, 0.45, -1.55] as V, r: 0.75, n: 200 }, { c: [5.55, 0.55, -0.55] as V, r: 0.7, n: 180 }, { c: [5.0, 0.4, -2.45] as V, r: 0.65, n: 160 }, { c: [5.9, 0.6, -1.2] as V, r: 0.8, n: 200 },
  { c: [4.0, 0.45, -5.65] as V, r: 0.7, n: 180 }, { c: [4.6, 0.55, -5.0] as V, r: 0.7, n: 170 }, { c: [3.15, 0.4, -6.0] as V, r: 0.65, n: 150 }, { c: [6.2, 0.5, 2.4] as V, r: 0.7, n: 160 }];

const Hut: React.FC<{ p: V; r?: number; door?: number; lit?: number; wall: THREE.Material; thatch: THREE.Material; wood: THREE.Material }> = ({ p, r = 0, door, lit = 0, wall, thatch, wood }) => (
  <group position={p} rotation={[0, r, 0]}>
    <mesh position={[0, 0.9, 0]} material={wall} castShadow receiveShadow><boxGeometry args={[3, 1.8, 2.4]} /></mesh>
    <mesh position={[0, 2.3, 0]} rotation={[0, Math.PI / 4, 0]} material={thatch} castShadow receiveShadow><coneGeometry args={[2.4, 1.3, 4]} /></mesh>
    <mesh position={[0.4, 0.78, -1.205]} rotation={[0, Math.PI, 0]} material={lit > 0.5 ? basicMat("#e8a050") : basicMat("#0c0906")}><planeGeometry args={[0.8, 1.55]} /></mesh>
    <mesh position={[-0.85, 1.15, -1.205]} rotation={[0, Math.PI, 0]} material={lit > 0 ? basicMat("#d88a3a") : basicMat("#0c0906")}><planeGeometry args={[0.36, 0.32]} /></mesh>
    {door !== undefined ? (
      <group position={[0.0, 0, -1.22]} rotation={[0, door, 0]}>
        <mesh position={[0.4, 0.78, 0]} material={wood} castShadow receiveShadow><boxGeometry args={[0.8, 1.55, 0.05]} /></mesh>
      </group>
    ) : null}
  </group>
);

const Charpai: React.FC<{ p: V; r?: number; wood: THREE.Material; rope: THREE.Material }> = ({ p, r = 0, wood, rope }) => (
  <group position={p} rotation={[0, r, 0]}>
    {[[-0.9, -0.42], [0.9, -0.42], [-0.9, 0.42], [0.9, 0.42]].map(([x, z], k) => <mesh key={k} position={[x, 0.2, z]} material={wood} castShadow><cylinderGeometry args={[0.035, 0.03, 0.4, 8]} /></mesh>)}
    {[-0.44, 0.44].map((z, k) => <mesh key={"l" + k} position={[0, 0.4, z]} material={wood} castShadow><boxGeometry args={[1.9, 0.06, 0.06]} /></mesh>)}
    {[-0.92, 0.92].map((x, k) => <mesh key={"w" + k} position={[x, 0.4, 0]} material={wood} castShadow><boxGeometry args={[0.06, 0.06, 0.9]} /></mesh>)}
    <mesh position={[0, 0.41, 0]} rotation={[-Math.PI / 2, 0, 0]} material={rope} castShadow receiveShadow><planeGeometry args={[1.8, 0.84]} /></mesh>
  </group>
);

const World: React.FC<{ t: number; st: number; mode: string; focus: V }> = ({ t, st, mode, focus }) => {
  const { scene, gl } = useThree();
  const night = mode === "night";
  const preset = presetAt(st, mode);
  const bark = useMemo(() => new THREE.MeshStandardMaterial({ map: barkTex(1, 2), roughness: 0.95, color: "#ffffff" }), []);
  const ground = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(70, "#6c7038"), roughness: 1, color: "#ffffff" }), []);
  const villageGround = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(24, "#a08060"), roughness: 1, color: "#ffffff" }), []);
  const pathM = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(16, "#9c8062"), roughness: 1, color: "#ffffff" }), []);
  const wall = useMemo(() => new THREE.MeshStandardMaterial({ map: mudTex(2), roughness: 1 }), []);
  const thatch = useMemo(() => new THREE.MeshStandardMaterial({ map: strawTex(3), roughness: 1 }), []);
  const wood = useMemo(() => new THREE.MeshStandardMaterial({ map: woodTex(), roughness: 0.9 }), []);
  const rope = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(8, "#b49a64"), roughness: 1 }), []);
  const rockM = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(3, "#8a8478"), roughness: 0.95, color: "#ffffff" }), []);
  const nightSky = useMemo(() => nightSkyMat(), []);
  const leaves = useLeaves(([] as { c: V; r: number; n: number }[]).concat(...FOREST.map(([x, z, s]) => [{ c: [x, 3.6 * s, z] as V, r: 1.5 * s, n: 260 }, { c: [x + 0.6 * s, 4.6 * s, z - 0.4] as V, r: 1.2 * s, n: 180 }, { c: [x - 0.5 * s, 4.4 * s, z + 0.5] as V, r: 1.1 * s, n: 160 }])), 31, 0.42);
  const neem = useLeaves([{ c: [NEEM[0], 4.2, NEEM[2]], r: 2.0, n: 1100 }, { c: [NEEM[0] + 1.4, 3.7, NEEM[2] + 0.3], r: 1.2, n: 420 }, { c: [NEEM[0] - 1.3, 3.8, NEEM[2] - 0.2], r: 1.2, n: 420 }], 33, 0.2);
  const bushes = useLeaves(BUSH_BLOBS.map((b) => ({ ...b, n: Math.round(b.n * 1.8) })), 41, 0.15);
  const grass = useGrass(3400, 7, (r) => { const x = -11 + r() * 24, z = -11 + r() * 25;
    if (Math.abs(x - lerp(PATH_P[0], PATH_V[0], (z - 4) / 19)) < 0.9 && z > 3.5) return null; if (Math.hypot(x - ROCK[0], z - ROCK[2]) < 0.7) return null; if (Math.hypot(x + 1.5, z - 27.5) < 11) return null; return [x, z]; }, 0.3, "#8a9a48");
  // light: a directional sun (or moon) whose shadow box follows the area in shot
  const light = useMemo(() => { const l = new THREE.DirectionalLight(); l.castShadow = true; l.shadow.mapSize.set(2048, 2048); const c = l.shadow.camera; c.left = -10; c.right = 10; c.top = 10; c.bottom = -10; c.near = 1; c.far = 90; l.shadow.bias = -0.0004; l.shadow.normalBias = 0.02; return l; }, []);
  const sd = night ? new THREE.Vector3(-0.45, 0.8, -0.4).normalize() : sunDir(preset);
  light.position.set(focus[0] + sd.x * 35, focus[1] + sd.y * 35, focus[2] + sd.z * 35); light.target.position.set(...focus); light.target.updateMatrixWorld();
  const dusk = preset === DUSK, gold = preset === GOLD;
  light.intensity = night ? 2.6 : dusk ? 2.4 : gold ? 3.0 : preset === NOON ? 3.4 : 2.8;
  light.color.set(night ? "#9ab0e0" : dusk ? "#ff9a58" : gold ? "#ffc890" : preset === NOON ? "#fff6ea" : "#ffe8d0");
  if (night) { scene.environment = null; gl.toneMappingExposure = 1.2; }
  const dusky = dusk && !night;
  const lampsOn = night || (dusky && st > 70);
  const smoke = (x: number, z: number, k: number) => Array.from({ length: 6 }, (_, q) => { const u = ((t * 0.12 + q / 6 + k * 0.3) % 1);
    return <mesh key={"sm" + k + q} position={[x + u * 0.8, 2.6 + u * 4, z + u * 0.3]} scale={0.3 + u * 0.9}><sphereGeometry args={[1, 10, 8]} /><meshStandardMaterial color="#c8c4c0" transparent opacity={0.16 * (1 - u)} depthWrite={false} /></mesh>; });
  return (
    <group>
      {night ? (
        <>
          <mesh material={nightSky} scale={500}><sphereGeometry args={[1, 32, 16]} /></mesh>
          <mesh position={[160, 120, -360]}><sphereGeometry args={[12, 24, 16]} /><meshBasicMaterial color="#f2eedc" fog={false} /></mesh>
          <mesh position={[160, 120, -361]}><sphereGeometry args={[32, 24, 16]} /><meshBasicMaterial color="#5a6a9a" transparent opacity={0.18} fog={false} depthWrite={false} /></mesh>
          <fog attach="fog" args={["#141a2c", 12, 60]} />
          <ambientLight intensity={0.8} color="#6a7aaa" />
          <hemisphereLight args={["#5a6a9a", "#20180c", 0.6]} />
        </>
      ) : (
        <>
          <SkyEnv preset={preset} name={presetName(preset)} />
          <fog attach="fog" args={[dusk ? "#c88a68" : gold ? "#e8c8a0" : preset === NOON ? "#d8dce0" : "#c8d4e0", dusk ? 10 : 16, dusk ? 70 : 95]} />
          <directionalLight position={[focus[0] - 6, 4, focus[2] + 9]} intensity={dusk ? 0.45 : 0.35} color={dusk ? "#ffb890" : "#e8f0ff"} />
          <hemisphereLight args={[dusk ? "#c87a6a" : gold ? "#ffd8b0" : "#b8d0f0", "#5a4a30", dusk ? 0.75 : 0.35]} />
        </>
      )}
      <primitive object={light} /><primitive object={light.target} />
      {/* ground, path, village yard, grass */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} material={ground} receiveShadow><planeGeometry args={[220, 220]} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, -Math.atan2(PATH_V[0] - PATH_P[0], PATH_V[2] - PATH_P[2])]} position={[(PATH_V[0] + PATH_P[0]) / 2, 0.003, (PATH_V[2] + PATH_P[2]) / 2]} material={pathM} receiveShadow><planeGeometry args={[1.3, dist(PATH_V, PATH_P) + 2]} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-1.5, 0.004, 27.5]} material={villageGround} receiveShadow><circleGeometry args={[10.5, 48]} /></mesh>
      <primitive object={grass} />
      {/* the boy's rock and scattered stones */}
      <mesh position={[ROCK[0], 0.05, ROCK[2]]} scale={[0.55, 0.4, 0.45]} rotation={[0, 0.4, 0]} material={rockM} castShadow receiveShadow><dodecahedronGeometry args={[1, 1]} /></mesh>
      {useMemo(() => { const r = rng(19); return Array.from({ length: 36 }, (_, k) => { const x = -8 + r() * 14, z = -7 + r() * 12; if (Math.hypot(x, z) < 2.2) return null;
        return <mesh key={k} position={[x, 0.02, z]} rotation={[r() * 3, r() * 3, 0]} scale={[0.06 + r() * 0.16, 0.04 + r() * 0.08, 0.06 + r() * 0.12]} material={rockM} castShadow receiveShadow><dodecahedronGeometry args={[1, 1]} /></mesh>; }); }, [rockM])}
      {/* forest edge and bushes */}
      {FOREST.map(([x, z, s], k) => <mesh key={"tr" + k} position={[x, 1.7 * s, z]} material={bark} castShadow receiveShadow><cylinderGeometry args={[0.16 * s, 0.26 * s, 3.4 * s, 10]} /></mesh>)}
      <primitive object={leaves} />
      <primitive object={neem} />
      <primitive object={bushes} />
      {/* the neem in the village */}
      <mesh position={[NEEM[0], 1.5, NEEM[2]]} material={bark} castShadow receiveShadow><cylinderGeometry args={[0.24, 0.38, 3.0, 14]} /></mesh>
      <Branch a={[NEEM[0], 2.6, NEEM[2]]} b={[NEEM[0] + 1.4, 3.5, NEEM[2] + 0.3]} r0={0.13} r1={0.06} m={bark} />
      <Branch a={[NEEM[0], 2.7, NEEM[2]]} b={[NEEM[0] - 1.3, 3.6, NEEM[2] - 0.2]} r0={0.12} r1={0.06} m={bark} />
      {/* huts */}
      {HUTS.map((h, k) => <Hut key={"h" + k} p={h} door={k === 2 || night ? doorAngle(st, mode) : undefined} lit={lampsOn ? (k === 2 ? (doorAngle(st, mode) > -0.2 ? 0.3 : 1) : night ? 0.3 : 1) : 0} wall={wall} thatch={thatch} wood={wood} />)}
      {FAR_HUTS.map(([x, z, r], k) => <Hut key={"fh" + k} p={[x, 0, z]} r={r} lit={lampsOn ? 0.4 : 0} wall={wall} thatch={thatch} wood={wood} />)}
      <Charpai p={CHARPAI_P} wood={wood} rope={rope} />
      <Charpai p={CHARPAI_H1} r={0.1} wood={wood} rope={rope} />
      {/* well, haystack, field */}
      <group position={WELL}>
        <mesh position={[0, 0.4, 0]} material={wall} castShadow receiveShadow><cylinderGeometry args={[0.75, 0.8, 0.8, 24, 1, true]} /></mesh>
        <mesh position={[0, 0.8, 0]} rotation={[Math.PI / 2, 0, 0]} material={wall} castShadow><torusGeometry args={[0.76, 0.08, 8, 24]} /></mesh>
        <mesh position={[0, 0.78, 0]} rotation={[-Math.PI / 2, 0, 0]} material={basicMat("#0a0806")}><circleGeometry args={[0.7, 24]} /></mesh>
        {[-0.7, 0.7].map((x, k) => <mesh key={k} position={[x, 1.25, 0]} material={wood} castShadow><cylinderGeometry args={[0.04, 0.04, 1.0, 8]} /></mesh>)}
        <mesh position={[0, 1.7, 0]} rotation={[0, 0, Math.PI / 2]} material={wood} castShadow><cylinderGeometry args={[0.035, 0.035, 1.5, 8]} /></mesh>
      </group>
      <mesh position={[-0.1, 0.7, 26.9]} material={thatch} castShadow receiveShadow><coneGeometry args={[1.0, 1.6, 14]} /></mesh>
      <mesh position={[-0.1, 0.25, 26.9]} material={thatch} castShadow receiveShadow><cylinderGeometry args={[0.95, 1.0, 0.5, 14]} /></mesh>
      {Array.from({ length: 9 }, (_, k) => <mesh key={"fu" + k} position={[3.4, 0.03, 21.6 + k * 0.42]} material={mat("furrow", () => new THREE.MeshStandardMaterial({ map: dirtTex(6, "#6a4a32"), roughness: 1 }))} receiveShadow><boxGeometry args={[3.6, 0.06, 0.2]} /></mesh>)}
      {/* dropped work: hoe, pot and hay lie where they fell after the first call */}
      {st >= T.run && st < T.arrive ? (
        <>
          <group position={[1.75, 0.03, 23.0]} rotation={[0, 0.4, Math.PI / 2]}>{HOE}</group>
          <mesh position={[-3.8, 0.15, 23.55]} material={plainMat("#9a5030", 0.85)} castShadow><sphereGeometry args={[0.15, 18, 12]} /></mesh>
          <mesh position={[-0.45, 0.14, 25.25]} rotation={[Math.PI / 2, 0, 0.3]} material={mat("haym", () => new THREE.MeshStandardMaterial({ map: strawTex(1), roughness: 1 }))} castShadow><cylinderGeometry args={[0.2, 0.24, 0.28, 12]} /></mesh>
        </>
      ) : null}
      {/* lamps in the village at dusk and night */}
      {lampsOn ? (
        <>
          <pointLight position={[CHARPAI_H1[0] - 1.05, 0.55, CHARPAI_H1[2] - 0.2]} intensity={night ? 0 : 2.2} distance={5} decay={1.5} color="#ffb060" />
          <mesh position={[CHARPAI_H1[0] - 1.05, 0.45, CHARPAI_H1[2] - 0.2]}><sphereGeometry args={[0.03, 10, 8]} /><meshBasicMaterial color="#ffd080" /></mesh>
          <pointLight position={[HUTS[1][0] + 0.4, 0.9, HUTS[1][2] - 1.5]} intensity={night ? 0.8 : 2.4} distance={5} decay={1.5} color="#ffa850" />
          <pointLight position={[doorOf(2)[0], 1.1, doorOf(2)[2] + 0.7]} intensity={doorAngle(st, mode) < -0.2 ? 2.6 : 0} distance={4} decay={1.5} color="#ffa850" />
        </>
      ) : null}
      {!night ? <>{smoke(HUTS[0][0] - 0.6, HUTS[0][2], 0)}{smoke(FAR_HUTS[2][0], FAR_HUTS[2][1], 1)}</> : null}
      {/* far hills */}
      {[[-60, -90, 34], [5, -110, 44], [70, -85, 30], [95, 20, 36], [-90, 30, 40]].map(([x, z, r], k) => <mesh key={"hill" + k} position={[x, -r * 0.72, z]} scale={[r * 1.6, r, r]} material={plainMat(night ? "#1a2018" : "#6a7a48", 1)}><sphereGeometry args={[1, 24, 12]} /></mesh>)}
      {/* golden motes in the low sun */}
      {dusky || gold ? Array.from({ length: 50 }, (_, k) => { const r = rng(300 + k); const x = focus[0] - 3 + r() * 6, z = focus[2] - 3 + r() * 6, y = 0.3 + ((r() * 2.4 + t * 0.06 * (0.5 + r())) % 2.4);
        return <mesh key={"mo" + k} position={[x + 0.1 * Math.sin(t * 0.5 + k), y, z]} scale={0.006 + r() * 0.006} material={mat("mote", () => new THREE.MeshBasicMaterial({ color: "#ffe8c0", transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false }))}><sphereGeometry args={[1, 6, 4]} /></mesh>; }) : null}
    </group>
  );
};

// ------------------------------------------------------------------ camera
type Cam = { pos: V; target: V; fov: number; roll?: number };
const headOf = (a: Act): V => { const f = fwd(a.yaw, 0.02); return [a.pos[0] + f[0], a.pos[1] + (lerp(1.6, 0.92, a.p.sit) - 0.06 * a.p.spine) * a.s, a.pos[2] + f[1]]; };
function camAt(t: number, st: number, mode: string): Cam {
  const boy = boyAt(t, st, mode);
  const bh = headOf(boy);
  if (mode === "classic") {
    if (st < T.c2) { const k = seg(st, 0, T.c2); return { pos: lerp3([1.2, 1.0, 2.7], [0.9, 0.95, 2.2], k), target: [ROCK[0] + 0.2, 1.15, ROCK[2] + 0.2], fov: 42 }; }
    if (st < T.c3) return { pos: orbit(bh, boy.yaw, 0.35, 1.05, -0.1), target: add(bh, [0, -0.04, 0]), fov: 34 };
    if (st < T.c4) return { pos: [ROCK[0] - 0.55, 2.0, ROCK[2] - 1.05], target: [-1.0, 1.0, 2.3], fov: 44 };
    if (st < T.c5) return { pos: [-2.75, 1.55, -1.0], target: [-1.0, 1.15, 1.2], fov: 46 };
    return { pos: [-0.8, 2.6, -4.2], target: [-1.0, 0.8, 1.6], fov: 46 };
  }
  if (mode === "world") { const k = seg(t, T.world, T.truth2); return { pos: lerp3([-0.9, 1.8, 6.6], [-1.0, 1.65, 5.7], k), target: [-1.6, 0.8, -0.3], fov: 42 }; }
  if (mode === "reveal") {
    const w = wolfAt(t, st, mode);
    if (t < T.came) return { pos: [-2.2, 1.4, 3.2], target: [2.0, 0.5, -0.8], fov: 50 };
    if (t < T.fled) return { pos: [2.2, 0.55, -2.4], target: w ? add(w.pos, [0, 0.45, 0]) : [3.2, 0.4, -4.6], fov: 38 };
    if (t < T.fled2) return { pos: [4.1, 0.75, -3.0], target: [0.2, 0.8, 7.0], fov: 46 };
    return { pos: [0.6, 0.65, -5.8], target: w ? add(w.pos, [0, 0.4, 0]) : [3.0, 0.5, -4.6], fov: 42 };
  }
  if (mode === "night") {
    if (t < T.noNeed) { const k = seg(t, T.night, T.noNeed); return { pos: lerp3([-0.9, 1.65, 20.6], [-1.1, 1.5, 22.6], k), target: [-0.6, 1.1, 30], fov: 46 }; }
    if (t < T.last) { const w = wolfAt(t, st, mode); return { pos: [1.1, 0.42, 2.9], target: w ? add(w.pos, [0, 0.45, 0]) : [1.5, 0.45, -1], fov: 42 }; }
    const k = seg(t, T.last, END); return { pos: lerp3([-0.4, 2.2, 6.4], [-0.5, 2.9, 7.6], k), target: [-0.6, 0.7, -0.6], fov: 44 };
  }
  // the story
  if (st < T.boy1) { const k = seg(st, T.truth, T.boy1); return { pos: [2.3, 0.45, 0.35], target: [4.7, 0.5, -1.05], fov: lerp(22, 18, k) }; }
  if (st < T.shout1) { const k = seg(st, T.boy1, T.shout1); return { pos: lerp3([1.1, 1.0, 3.6], [0.8, 0.95, 3.2], k), target: [-0.4, 0.75, 1.0], fov: 38 }; }
  if (st < T.stalk1) return { pos: orbit(bh, boy.yaw, 0.35, 1.35, -0.2), target: add(bh, [0, -0.12, 0]), fov: 38 };
  if (st < T.snarl1) { const w = wolfAt(t, st, mode)!; return { pos: [2.65, 0.55, 1.5], target: add(w.pos, [0, 0.35, 0]), fov: 40 }; }
  if (st < T.vill1) { const w = wolfAt(t, st, mode)!; const hd: V = add(w.pos, [Math.sin(w.yaw) * 0.45, 0.72, Math.cos(w.yaw) * 0.45]); return { pos: orbit(hd, w.yaw, 0.55, 0.95, -0.05), target: hd, fov: 34, roll: 0.12 }; }
  if (st < T.flee1) return { pos: [-0.35, 1.05, 3.6], target: [-0.9, 1.0, 12], fov: 40 };
  if (st < T.safe1) { const w = wolfAt(t, st, mode)!; return { pos: [1.0, 1.05, 3.4], target: add(w.pos, [0, 0.45, 0]), fov: 42 }; }
  if (st < T.hear) { const k = seg(st, T.safe1, T.hear); return { pos: lerp3([2.4, 1.7, 4.6], [2.0, 1.6, 4.3], k), target: [-0.1, 0.4, 0.5], fov: 44 }; }
  if (st < 24.95) return { pos: [1.0, 1.4, 20.9], target: [1.7, 1.0, 23.4], fov: 40 };
  if (st < T.run) return { pos: [-3.3, 1.45, 21.5], target: [-3.9, 1.0, 23.95], fov: 42 };
  if (st < T.arrive) { const vs = villagersAt(t, st, mode); const lead = vs[0].pos; const k = seg(st, T.run, T.arrive);
    return { pos: [lead[0] + 1.1, 1.25, Math.min(lead[2] - 3.4, 21.5 - 3 * k)], target: add(lead, [0, 1.0, 0]), fov: 42 }; }
  if (st < T.noWolf) return { pos: [-0.65, 1.6, 5.4], target: [0.6, 0.75, 0.0], fov: 44 };
  if (st < T.scold) return { pos: [-0.8, 1.32, 0.3], target: [0.15, 1.42, 2.9], fov: 44 };
  if (st < T.trust) return { pos: [3.2, 1.45, 1.43], target: [-0.32, 1.12, 2.15], fov: 40 };
  if (st < T.second) return { pos: [-1.55, 1.2, 0.55], target: [0.2, 1.25, 3.0], fov: 42 };
  if (st < T.run2) return { pos: [-1.0, 0.95, 1.4], target: [1.8, 0.75, -3.9], fov: 44 };
  if (st < T.flee2) return { pos: [0.6, 1.0, 5.4], target: [-0.6, 1.0, 12.5], fov: 40 };
  if (st < T.decide) { const w = wolfAt(t, st, mode); return { pos: [4.3, 0.55, -2.1], target: w ? add(w.pos, [0, 0.4, 0]) : [3.2, 0.4, -5.5], fov: 44 }; }
  if (st < T.elder) { const k = seg(st, T.decide, T.elder); return { pos: lerp3([-3.15, 1.75, 18.4], [-3.15, 1.65, 19.0], k), target: [-3.2, 1.0, 23.2], fov: 44 }; }
  if (st < T.nobody) { const old = villagersAt(t, st, mode)[0]; const h = headOf(old); return { pos: orbit(h, old.yaw, 0.3, 1.0, -0.05), target: h, fov: 32 }; }
  if (st < T.dusk) { const k = seg(st, T.nobody, T.dusk); return { pos: lerp3([-3.6, 1.6, 24.5], [-3.5, 1.55, 24.2], k), target: [-2.35, 1.35, 22.5], fov: 42 }; }
  if (st < T.attack) { const w = wolfAt(t, st, mode)!; return { pos: [1.2, 0.45, 0.45], target: add(w.pos, [0, 0.5, 0]), fov: 40 }; }
  if (st < T.scream) { const sh = 0.025 * Math.sin(st * 40) * Math.exp(-(st - T.attack) * 1.5); return { pos: [-1.6, 2.2 + sh, 3.7], target: [0.9, 0.3, -0.5], fov: 48 }; }
  if (st < T.look) return { pos: orbit(bh, boy.yaw, 0.2, 0.95, -0.12), target: add(bh, [0, -0.05, 0]), fov: 34 };
  if (st < T.hope) { const b = fwd(boy.yaw, -0.6), sdd = side(boy.yaw, 0.22); return { pos: [boy.pos[0] + b[0] + sdd[0], 1.2, boy.pos[2] + b[1] + sdd[1]], target: VILLAGE_EYE, fov: 30 }; }
  if (st < T.homes) return { pos: orbit(bh, boy.yaw, -0.3, 0.85, -0.12), target: bh, fov: 32 };
  if (st < T.joke) return { pos: [-2.35, 1.5, 23.5], target: [-2.6, 0.8, 28.0], fov: 46 };
  if (st < T.letHim) { const f = villagersAt(t, st, mode)[0]; const h = headOf(f); return { pos: orbit(h, f.yaw, -0.25, 0.95, 0.0), target: h, fov: 32 }; }
  if (st < T.door) { return { pos: [-1.1, 1.05, 25.4], target: [-1.1, 0.72, 28.57], fov: 46 }; }
  if (st < T.kill) { const d = doorOf(2); return { pos: [d[0] - 0.6, 1.45, d[2] - 3.4], target: [d[0] - 0.1, 1.0, d[2]], fov: 40 }; }
  if (st < T.helpless) { const k = seg(st, T.kill, T.helpless); return { pos: lerp3([-3.0, 0.45, 0.9], [-2.7, 0.5, 0.5], k), target: [1.8, 0.55, -0.6], fov: 46 }; }
  if (st < T.nobodyCame) return { pos: add(boy.pos, [0.2, 1.0, 3.1]), target: add(boy.pos, [0, 0.75, 0]), fov: 42 };
  if (st < T.rock) { const b = fwd(boy.yaw, -0.7), sdd = side(boy.yaw, 0.25); return { pos: [boy.pos[0] + b[0] + sdd[0], 1.15, boy.pos[2] + b[1] + sdd[1]], target: [-1.0, 1.0, 13], fov: 36 }; }
  const k = seg(st, T.rock, T.world); return { pos: lerp3([0.8, 1.35, 2.5], [0.25, 1.1, 1.7], k), target: [ROCK[0] + 0.2, 0.7, ROCK[2] + 0.2], fov: 42 };
}
const CameraRig: React.FC<{ cam: Cam }> = ({ cam }) => {
  const { camera } = useThree();
  const c = camera as THREE.PerspectiveCamera;
  c.position.set(...cam.pos); c.fov = cam.fov; c.near = 0.03; c.far = 2000;
  c.up.set(Math.sin(cam.roll ?? 0), Math.cos(cam.roll ?? 0), 0); c.lookAt(new THREE.Vector3(...cam.target)); c.updateProjectionMatrix();
  return null;
};

const Scene: React.FC<{ t: number }> = ({ t }) => {
  const mode = modeAt(t);
  const st = storyTime(t);
  const cam = camAt(t, st, mode);
  const focus: V = cam.target[2] > 14 ? [-1.8, 0, 26.8] : [0.6, 0, 0];
  const boy = boyAt(t, st, mode);
  const wolf = wolfAt(t, st, mode);
  // the stick he dropped, lying in the grass
  const stickDown = mode !== "classic" && st >= 96.2 && st < T.world ? (() => { const s = boyAt(t, 95.0, "story"); return s.pos; })() : mode === "night" || mode === "world" ? [-0.2, 0, 0.9] as V : null;
  return (
    <>
      <CameraRig cam={cam} />
      <World t={t} st={st} mode={mode} focus={focus} />
      <group position={boy.pos} rotation={[0, boy.yaw, 0]} scale={boy.s}><Human look={boy.look} p={boy.p} /></group>
      {stickDown ? <group position={[stickDown[0] + 0.25, 0.02, stickDown[2] + 0.1]} rotation={[Math.PI / 2, 0, 0.7]}>{STICK(9)}</group> : null}
      {villagersAt(t, st, mode).map((v, k) => <group key={"v" + k} position={v.pos} rotation={[0, v.yaw, 0]} scale={v.s}><Human look={v.look} p={v.p} /></group>)}
      {wolf ? <group position={wolf.pos} rotation={[0, wolf.yaw, 0]} scale={1.05}><Wolf p={wolf.p} glow={wolf.glow} /></group> : null}
      {SHEEP.map((sh, i) => { const s = sheepAt(i, t, st, mode); return <group key={"s" + i} position={s.pos} rotation={[0, s.yaw, 0]} scale={sh.s}><Sheep p={s} face={sh.face} /></group>; })}
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

const CUTS = [T.c2, T.c3, T.c4, T.c5, T.boy1, T.shout1, T.stalk1, T.snarl1, T.vill1, T.flee1, T.safe1, T.hear, T.run, T.arrive, T.noWolf, T.scold, T.trust, T.second, T.run2, T.flee2, T.decide,
  T.elder, T.nobody, T.dusk, T.attack, T.scream, T.look, T.hope, T.homes, T.joke, T.letHim, T.door, T.kill, T.helpless, T.nobodyCame, T.rock, T.world, T.came, T.fled, T.fled2, T.noNeed, T.last];

export const Bhediya3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const mode = modeAt(t);
  const sub = SUBS.find(([a, b]) => t >= a && t < b);
  const old = mode === "classic" || mode === "world";
  const rewinding = t >= T.rewind && t < T.truth;
  const flash = mode === "reveal";
  const flick = old ? 0.94 + 0.06 * Math.sin(frame * 2.7) * Math.sin(frame * 1.3) : 1;
  const filter = old ? `sepia(0.55) saturate(0.7) contrast(1.12) brightness(${flick})` : flash ? "saturate(0.4) contrast(1.08) brightness(0.98)" : mode === "night" ? "contrast(1.06) saturate(1.05)" : "saturate(1.06) contrast(1.05)";
  const jitter = old ? `translate(${(Math.sin(frame * 7.1) * 2) | 0}px, ${(Math.sin(frame * 3.3) * 2) | 0}px)` : rewinding ? `translateX(${(Math.sin(frame * 11) * 8) | 0}px) skewX(${Math.sin(frame * 5) * 2}deg)` : "none";
  let dip = 0; for (const c of CUTS) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.08);
  const whiteFlash = Math.max(0, 1 - Math.abs(t - T.truth) / 0.12, 1 - Math.abs(t - T.truth2) / 0.12, 1 - Math.abs(t - T.world) / 0.12);
  const blackDip = Math.max(0, 1 - Math.abs(t - T.night) / 0.3, 1 - Math.abs(t - T.dusk) / 0.25);
  const fade = Math.min(clamp(t / 0.4), clamp((END - t) / 1.4));
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter: `${filter} blur(${rewinding ? 1 : 0}px)`, transform: jitter }}>
        <div style={{ width: CW, height: CH, transform: `scale(${1080 / CW})`, transformOrigin: "0 0" }}>
          <ThreeCanvas width={CW} height={CH} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
            <Scene t={t} />
          </ThreeCanvas>
        </div>
      </AbsoluteFill>
      {flash ? <AbsoluteFill style={{ background: "rgba(70,100,150,0.18)", mixBlendMode: "multiply" }} /> : null}
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
