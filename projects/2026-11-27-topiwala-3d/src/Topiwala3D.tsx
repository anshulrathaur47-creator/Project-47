import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import {
  Branch, CAP_COLORS, Cap, HLook, HPose, Human, MLook, MPose, Monkey, SkyEnv, SkyPreset, barkTex, basicMat, clamp, clothMat, dirtTex,
  flameTex, hRest, lerp, mRest, mat, mudTex, nightSkyMat, plainMat, rng, ropeTex, seg, smooth, strawTex, sunDir, useGrass, useLeaves, woodTex,
} from "./Real";

// "टोपीवाला और बंदर की कहानी…" (ReelAudio-36643): the cap-seller and the monkeys, the true version.
// The monkeys never copied him: the chief saw a poor man crying and dropped the caps to help him.
export const DURATION = 1395; // 46.5 s (narration ends 45.1 s, then a held last shot)
const FPS = 30;
const END = DURATION / FPS;
type V = [number, number, number];

const SUBS: [number, number, string][] = [
  [0.0, 2.86, "टोपीवाला और बंदर की कहानी तो आपने सुनी ही होगी,"],
  [2.88, 5.9, "जिसमें सब कहते हैं कि बंदर बड़े बेवकूफ थे।"],
  [5.92, 9.5, "टोपीवाले की नकल की और सारी टोपियां नीचे फेंक दीं।"],
  [9.94, 13.0, "पर असल में उन बंदरों ने कोई नकल की ही नहीं थी।"],
  [13.02, 16.62, "पेड़ पर बैठे सरदार बंदर ने नीचे रोते हुए"],
  [16.66, 21.1, "उस गरीब टोपीवाले की फटी चप्पल और सूखा चेहरा देख लिया था।"],
  [21.38, 24.5, "वो समझ गया था कि अगर आज ये टोपियां नहीं बिकीं,"],
  [24.56, 27.2, "तो इसके छोटे बच्चे आज फिर भूखे सो जाएंगे।"],
  [27.22, 32.0, "बस इसीलिए जब टोपीवाले ने गुस्से में अपनी टोपी जमीन पर मारी,"],
  [32.06, 34.1, "तो उन बंदरों ने मजाक में नहीं,"],
  [34.12, 37.25, "बल्कि उसकी मदद करने के लिए सारी टोपियां नीचे गिरा दीं।"],
  [37.3, 41.7, "जिन इंसानों ने सुबह से उसकी एक टोपी नहीं खरीदी थी,"],
  [41.78, 46.0, "उन बेजुबान जानवरों ने उसके घर का चूल्हा जला दिया।"],
];
// story beats (Whisper times)
const T = { mock: 2.88, throwSeq: 5.92, rewind: 9.34, truth: 10.0, tree: 13.02, cry: 15.5, poor: 16.9, chappal: 18.1, face: 19.3, knew: 20.9, caps: 22.9,
  kids: 24.5, hungry: 25.9, rise: 27.22, anger: 29.9, dirt: 31.45, notJoke: 32.0, help: 34.1, drop: 35.8, people: 37.3, close: 39.5, night: 41.7, chulha: 43.3, crane: 44.9 };

// ------------------------------------------------------------------ the people
const SELLER: HLook = { skin: "#86563a", hair: "#2a2622", hairStyle: "short", top: "#c4b89e", topStyle: "kurta", bottom: "#d2c9b4", bottomStyle: "dhoti",
  stubble: "#3a3532", moustache: "#26221e", cap: "#f2efe6", chappal: "torn", worn: 0.4 };
const WIFE: HLook = { skin: "#96643f", hair: "#141010", hairStyle: "bun", top: "#6a1a2a", topStyle: "blouse", bottom: "#b8462a", bottomStyle: "saree", pallu: "#c0502e", bindi: true, lip: "#7a3a34" };
const BOY: HLook = { skin: "#8c5c3e", hair: "#16110d", hairStyle: "kid", top: "#3a6aa0", topStyle: "shirt", bottom: "#4a4038", bottomStyle: "shorts", worn: 1 };
const GIRL: HLook = { skin: "#926042", hair: "#18120e", hairStyle: "kidgirl", top: "#d06a88", topStyle: "frock", bottom: "#d06a88", bottomStyle: "shorts", worn: 1 };
const V_WOMAN: HLook = { skin: "#9a6a48", hair: "#151010", hairStyle: "bun", top: "#2a5a48", topStyle: "blouse", bottom: "#2a7a5a", bottomStyle: "saree", pallu: "#3a8a68", chappal: "plain" };
const V_MAN: HLook = { skin: "#8a5a3c", hair: "#1a1612", hairStyle: "short", top: "#5a6a8a", topStyle: "shirt", bottom: "#4a4a4c", bottomStyle: "pants", chappal: "plain" };
const V_OLD: HLook = { skin: "#7e5236", hair: "#d8d4cc", hairStyle: "bald", top: "#ece6d6", topStyle: "kurta", bottom: "#e8e2d2", bottomStyle: "dhoti", stubble: "#d8d4cc", chappal: "plain" };
const S_SELLER = 0.94;

// ------------------------------------------------------------------ places (tree set: banyan at the origin, road along x at z≈3.4)
const SIT: V = [0.4, 0, 0.72]; const SIT_YAW = 0.52;      // sitting against the trunk, crying
const SLAM: V = [0.95, 0, 1.6]; const SLAM_YAW = 3.0;     // standing, facing the tree
const ROAD: V = [-0.7, 0, 2.5]; const ROAD_YAW = 0;       // the morning, by the road
const fwd = (yaw: number, d: number): [number, number] => [Math.sin(yaw) * d, Math.cos(yaw) * d];
const add = (a: V, b: V): V => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const lerp3 = (a: V, b: V, k: number): V => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
const orbit = (c: V, yaw: number, off: number, d: number, h: number): V => [c[0] + Math.sin(yaw + off) * d, c[1] + h, c[2] + Math.cos(yaw + off) * d];

const BRANCHES: { a: V; b: V; r0: number; r1: number }[] = [
  { a: [0.2, 2.4, 0.05], b: [2.8, 3.3, 0.7], r0: 0.16, r1: 0.07 },      // B1: the chief's branch
  { a: [-0.2, 2.55, 0.05], b: [-2.5, 3.45, 0.85], r0: 0.15, r1: 0.07 },
  { a: [-0.1, 2.75, 0.2], b: [-0.9, 3.7, 2.0], r0: 0.12, r1: 0.05 },
  { a: [-0.1, 2.9, -0.2], b: [-0.9, 4.0, -1.9], r0: 0.13, r1: 0.05 },
  { a: [0.15, 3.1, -0.15], b: [1.9, 4.3, -1.3], r0: 0.12, r1: 0.05 },
  { a: [0, 3.0, 0], b: [0.2, 4.9, 0.1], r0: 0.28, r1: 0.1 },
  { a: [0, 3.6, 0], b: [-2.4, 4.7, -0.5], r0: 0.12, r1: 0.05 },
  { a: [0, 3.6, 0], b: [2.6, 4.6, -0.1], r0: 0.12, r1: 0.05 },
];
const onBranch = (bi: number, s: number): V => { const b = BRANCHES[bi]; const r = lerp(b.r0, b.r1, s); return [lerp(b.a[0], b.b[0], s), lerp(b.a[1], b.b[1], s) + r * 0.9, lerp(b.a[2], b.b[2], s)]; };

// ------------------------------------------------------------------ the monkeys
const RHESUS: MLook = { fur: "#8a7a64", furLow: "#a87c50", chest: "#b8a488", face: "#d48a7a" };
const SARDAR_LOOK: MLook = { fur: "#7c766c", furLow: "#8c7a62", chest: "#a89e8e", face: "#c47a6c", scar: true };
type MDef = { b: number; s: number; sc: number; cap: string; look: MLook; sardar?: boolean; overEyes?: boolean; scratch?: boolean; drop: number };
const MONKEYS: MDef[] = [
  { b: 0, s: 0.38, sc: 1.25, cap: CAP_COLORS[0], look: SARDAR_LOOK, sardar: true, drop: 36.15 },
  { b: 0, s: 0.72, sc: 1.0, cap: CAP_COLORS[1], look: RHESUS, scratch: true, drop: 34.35 },
  { b: 1, s: 0.38, sc: 1.0, cap: CAP_COLORS[2], look: { ...RHESUS, fur: "#867460" }, drop: 34.6 },
  { b: 1, s: 0.68, sc: 0.95, cap: CAP_COLORS[3], look: { ...RHESUS, fur: "#927e66", furLow: "#b08454" }, drop: 34.85 },
  { b: 2, s: 0.55, sc: 0.9, cap: CAP_COLORS[4], look: RHESUS, scratch: true, drop: 35.15 },
  { b: 3, s: 0.5, sc: 1.0, cap: CAP_COLORS[5], look: { ...RHESUS, fur: "#806e5a" }, drop: 35.45 },
  { b: 4, s: 0.5, sc: 0.95, cap: CAP_COLORS[6], look: RHESUS, drop: 35.75 },
];
const SEATS = MONKEYS.map((m) => onBranch(m.b, m.s));
const yawTo = (from: V, to: V) => Math.atan2(to[0] - from[0], to[2] - from[2]);
const SARDAR_YAW = yawTo(SEATS[0], SIT);
const SARDAR_HEAD: V = (() => { const f = fwd(SARDAR_YAW, 0.15); return [SEATS[0][0] + f[0], SEATS[0][1] + 0.45, SEATS[0][2] + f[1]]; })();
const SARDAR_YAW2 = yawTo(SEATS[0], SLAM);
const SARDAR_HEAD2: V = (() => { const f = fwd(SARDAR_YAW2, 0.15); return [SEATS[0][0] + f[0], SEATS[0][1] + 0.45, SEATS[0][2] + f[1]]; })();
const heldCapWorld = (i: number, yaw: number): V => { const m = MONKEYS[i]; const f = fwd(yaw, 0.2 * m.sc); return [SEATS[i][0] + f[0], SEATS[i][1] + 0.12 * m.sc, SEATS[i][2] + f[1]]; };
const headWorld = (i: number, yaw: number): V => { const m = MONKEYS[i]; const f = fwd(yaw, 0.1 * m.sc); return [SEATS[i][0] + f[0], SEATS[i][1] + 0.42 * m.sc, SEATS[i][2] + f[1]]; };

// ------------------------------------------------------------------ falling caps
type Fall = { color: string; from: V; to: V; t0: number; dur: number; spin: number };
const CAP_LAND = (k: number, c: V, rad: number): V => { const a = k * 2.39 + 0.4; const r = rad * (0.35 + 0.65 * ((k * 37) % 10) / 10); return [c[0] + Math.cos(a) * r, 0, c[2] + Math.sin(a) * r]; };
const SELLER_CAP_TRUE_LAND: V = (() => { const f = fwd(SLAM_YAW, 0.42); return [SLAM[0] + f[0], 0, SLAM[2] + f[1]]; })();
const CLASSIC_FALLS: Fall[] = [
  { color: SELLER.cap!, from: add(SLAM, [0.25, 1.75, -0.1]), to: (() => { const f = fwd(SLAM_YAW, 0.55); return [SLAM[0] + f[0], 0, SLAM[2] + f[1]] as V; })(), t0: 6.66, dur: 0.3, spin: 1 },
  ...MONKEYS.map((m, i): Fall => { const y = yawTo(SEATS[i], SLAM); return { color: m.cap, from: headWorld(i, y), to: CAP_LAND(i, SLAM, 0.9), t0: 7.2 + i * 0.13, dur: 1.0, spin: 2 + i }; }),
];
const TRUE_FALLS: Fall[] = [
  { color: SELLER.cap!, from: add(SLAM, [0.2, 1.95, -0.05]), to: SELLER_CAP_TRUE_LAND, t0: 31.38, dur: 0.17, spin: 0.4 },
  ...MONKEYS.map((m, i): Fall => { const y = yawTo(SEATS[i], SLAM); return { color: m.cap, from: heldCapWorld(i, y), to: m.sardar ? add(SLAM, [0.05, 0, -0.32]) : CAP_LAND(i + 2, SLAM, 0.75), t0: m.drop, dur: m.sardar ? 1.15 : 1.5, spin: 1.5 + i * 0.7 }; }),
];
function capPose(f: Fall, t: number): { p: V; r: V } | null {
  if (t < f.t0) return null;
  const u = clamp((t - f.t0) / f.dur);
  const k = u * u * (1.6 - 0.6 * u);   // eases in, floats a little
  const sway = Math.sin(u * Math.PI * 2.2 + f.spin) * 0.18 * (1 - u) * (f.dur > 0.5 ? 1 : 0);
  const p: V = [lerp(f.from[0], f.to[0], u) + sway, lerp(f.from[1], f.to[1] + 0.0, k), lerp(f.from[2], f.to[2], u) + sway * 0.6];
  const fl = (1 - u) * (f.dur > 0.5 ? 1 : 0.3);
  return { p, r: [Math.sin(u * 9 + f.spin) * 0.8 * fl, f.spin * u * 3, Math.cos(u * 7 + f.spin) * 0.7 * fl] };
}

// ------------------------------------------------------------------ who does what, when
type Act = { look: HLook; pos: V; yaw: number; p: HPose; s: number };
function sellerAt(t: number): Act | null {
  const p = hRest(); p.capOnHead = true;
  if (t < T.truth) {   // the version everyone tells
    p.headPitch = -0.45; p.brow = 0.2;
    if (t < T.mock) { p.anger = 1; p.mouth = 0.45 + 0.25 * Math.sin(t * 9); p.armR = [-2.75, -0.3]; p.elbowR = -0.9 + 0.35 * Math.sin(t * 13); p.armL = [-0.3, 0.35]; p.elbowL = -1.2; }
    else if (t < T.throwSeq) { p.brow = 1; p.mouth = 0.35; p.armL = [-2.6, 0.55]; p.armR = [-2.6, -0.55]; p.elbowL = -2.0; p.elbowR = -2.0; p.headRoll = 0.15 * Math.sin(t * 3); }
    else if (t < 6.66) {   // takes off his cap and flings it down
      const k = seg(t, T.throwSeq, 6.3); p.armR = [lerp(-0.2, -2.9, k), -0.25]; p.elbowR = lerp(-0.2, -1.6, k); p.anger = 0.8; p.mouth = 0.3;
      if (t > 6.3) { p.capOnHead = false; p.handR = <Cap color={SELLER.cap!} r={[1.4, 0, 0]} />; const k2 = seg(t, 6.3, 6.66); p.armR = [lerp(-2.9, -0.5, k2), -0.2]; p.elbowR = lerp(-1.6, 0, k2); p.spine = 0.25 * k2; }
    } else if (t < 7.6) { p.capOnHead = false; p.armL = [-0.3, 0.6]; p.armR = [-0.3, -0.6]; p.elbowL = -1.7; p.elbowR = -1.7; p.headPitch = -0.6; p.smile = 0.2; }
    else { p.capOnHead = false; const k = seg(t, 7.6, 8.2); p.armL = [-1.1 * k, 0.4 + 0.6 * k]; p.armR = [-1.1 * k, -0.4 - 0.6 * k]; p.elbowL = -0.3; p.elbowR = -0.3; p.smile = 1; p.mouth = 0.35; p.headPitch = -0.55; }
    return { look: SELLER, pos: SLAM, yaw: SLAM_YAW, p, s: S_SELLER };
  }
  if (t < T.rise) {   // sitting against the trunk, crying; nobody bought, now the monkeys have his caps too
    p.capOnHead = true; p.sit = 1; p.spine = 0.45 + 0.03 * Math.sin(t * 8.5); p.headPitch = 0.28; p.brow = 1; p.eyes = 0.32; p.smile = -0.75; p.mouth = 0.18 + 0.1 * Math.abs(Math.sin(t * 4));
    p.tear = clamp((t - 14) / 2); p.armL = [-1.0, 0.25]; p.armR = [-1.0, -0.25]; p.elbowL = 0.9; p.elbowR = 0.9;
    if (t > T.face && t < T.knew) { p.headPitch = 0.1; p.eyes = 0.45; }
    return { look: SELLER, pos: SIT, yaw: SIT_YAW, p, s: S_SELLER };
  }
  if (t < T.people) {
    if (t < 28.4) {   // gets up
      const k = seg(t, T.rise, 28.4); p.sit = 1 - k; p.spine = lerp(0.45, 0.15, k); p.brow = 0.8; p.anger = 0.4 * k; p.smile = -0.6; p.armL = [-1.0 * (1 - k), 0.2]; p.armR = [lerp(-1.0, -2.2, Math.sin(k * Math.PI)), -0.25]; p.elbowR = lerp(0.9, -2.0, Math.sin(k * Math.PI));
      return { look: SELLER, pos: SIT, yaw: SIT_YAW, p, s: S_SELLER };
    }
    if (t < 29.6) {   // walks out from under the tree, turns to face the monkeys
      const k = seg(t, 28.4, 29.6); p.walk = t < 29.4 ? 1 : 0; p.phase = t * 7; p.anger = 0.7; p.brow = 0.3; p.smile = -0.6; p.headPitch = -0.2;
      return { look: SELLER, pos: lerp3(SIT, SLAM, k), yaw: k < 0.75 ? lerp(SIT_YAW, 0.47, k) : lerp(0.47, SLAM_YAW, seg(k, 0.75, 1)), p, s: S_SELLER };
    }
    p.headPitch = -0.35; p.anger = 1; p.brow = 0.2; p.smile = -0.8; p.mouth = 0.25;
    if (t < 30.5) { p.armL = [-0.2, 0.2]; p.armR = [-0.2, -0.2]; p.elbowL = -0.4; p.elbowR = -0.4; p.mouth = 0.4 + 0.2 * Math.sin(t * 10); }
    else if (t < 31.3) {   // rips the cap off, raises it high
      const k = seg(t, 30.5, 30.85); p.armR = [lerp(-0.2, -3.0, k), -0.2]; p.elbowR = lerp(-0.3, -1.5, k);
      if (t > 30.8) { p.capOnHead = false; p.handR = <Cap color={SELLER.cap!} r={[1.4, 0, 0]} />; p.elbowR = lerp(-1.5, -0.4, seg(t, 30.85, 31.2)); }
      p.mouth = 0.7; p.headPitch = -0.15;
    } else if (t < T.dirt) {   // and slams it into the dirt
      const k = seg(t, 31.3, T.dirt); p.capOnHead = false; if (t < 31.38) p.handR = <Cap color={SELLER.cap!} r={[1.4, 0, 0]} />; p.armR = [lerp(-3.0, -0.7, k), -0.2]; p.elbowR = lerp(-0.4, 0, k); p.spine = 0.55 * k; p.mouth = 0.8;
    } else if (t < T.help + 0.4) {   // bent over, spent
      p.capOnHead = false; p.spine = lerp(0.55, 0.3, seg(t, 31.6, 33)) + 0.03 * Math.sin(t * 7); p.headPitch = 0.3; p.anger = 0.2; p.brow = 1; p.eyes = 0.4; p.smile = -0.6; p.mouth = 0.2; p.tear = 1;
      p.armL = [-0.15, 0.15]; p.armR = [-0.4, -0.15]; p.elbowR = -0.1;
    } else {   // caps start floating down: he looks up, stunned, arms opening
      p.capOnHead = false; const k = seg(t, T.help + 0.4, T.drop + 0.4); p.spine = lerp(0.3, 0, k); p.headPitch = lerp(0.3, -0.7, k); p.anger = 0; p.brow = lerp(1, 0.5, k); p.eyes = lerp(0.5, 1.15, k);
      p.mouth = lerp(0.2, 0.55, k); p.smile = lerp(-0.4, 0.2, seg(t, 36.4, 37.2)); p.tear = 1;
      p.armL = [lerp(-0.15, -0.9, k), lerp(0.15, 0.85, k)]; p.armR = [lerp(-0.4, -0.9, k), lerp(-0.15, -0.85, k)]; p.elbowL = -0.35; p.elbowR = -0.35;
    }
    return { look: SELLER, pos: SLAM, yaw: SLAM_YAW, p, s: S_SELLER };
  }
  if (t < T.night) {   // flashback, that morning: holding out a cap to people who walk past
    const giveUp = seg(t, 40.7, 41.3);
    p.armR = [lerp(-1.35, -0.25, giveUp), -0.1]; p.elbowR = lerp(-0.2, -0.2, giveUp); p.handR = <Cap color={CAP_COLORS[2]} r={[1.2, 0, 0]} />;
    p.smile = lerp(0.45, -0.5, giveUp); p.brow = lerp(0.25, 1, giveUp); p.headPitch = lerp(-0.05, 0.35, giveUp); p.mouth = t < 39 ? 0.25 + 0.15 * Math.sin(t * 8) : 0;
    p.headYaw = t < 39.5 ? 0.5 * Math.sin((t - T.people) * 1.1) : lerp(0.5, 0.0, giveUp);
    return { look: SELLER, pos: ROAD, yaw: ROAD_YAW, p, s: S_SELLER };
  }
  return null;
}
// villagers who walked past him that morning
function villagersAt(t: number): Act[] {
  if (t < T.people || t >= T.night) return [];
  const u = t - T.people;
  const w = hRest(); w.walk = 1; w.phase = t * 6.5; w.armR = [-2.9, -0.35]; w.elbowR = -2.2; w.headYaw = 0; w.smile = 0;
  const m = hRest(); m.walk = 1; m.phase = t * 7; m.headYaw = u > 1.2 && u < 1.9 ? 0.5 : 0; m.smile = -0.1; m.armL = [-1.2, 0.1]; m.elbowL = -1.5;
  const o = hRest(); o.walk = 0.7; o.phase = t * 5; o.spine = 0.18; o.armR = [-0.5, -0.1]; o.elbowR = -0.4;
  return [
    { look: V_WOMAN, pos: [1.4 - 1.2 * u, 0, 3.55], yaw: -Math.PI / 2, p: w, s: 0.9 },
    { look: V_MAN, pos: [-2.6 + 1.3 * u, 0, 3.15], yaw: Math.PI / 2, p: m, s: 0.98 },
    { look: V_OLD, pos: [2.2 - 0.8 * u, 0, 3.9], yaw: -Math.PI / 2, p: o, s: 0.92 },
  ];
}
function monkeyAt(i: number, t: number): { pos: V; yaw: number; p: MPose; sc: number } | null {
  const m = MONKEYS[i]; const p = mRest();
  if (t >= T.people) return null;   // not there in the morning flashback
  p.tail = t * 1.3 + i;
  if (t < T.truth) {   // the version everyone tells: silly monkeys in caps, laughing
    const y = yawTo(SEATS[i], SLAM);
    p.lean = 0.3; p.headPitch = 0.45; p.capWorn = m.cap; p.capAskew = 0.35 * Math.sin(i * 2.1); p.capOverEyes = m.overEyes;
    const laugh = Math.max(0, Math.sin(t * 2.2 + i * 1.7)); p.grin = laugh; p.mouth = laugh * 0.6; p.eyes = laugh > 0.7 ? 0.25 : 1; p.headTilt = 0.15 * Math.sin(t * 5 + i);
    if (m.scratch && t < T.throwSeq) { p.armR = [-2.5, -0.5]; p.elbowR = -1.8 + 0.3 * Math.sin(t * 14 + i); p.headTilt = 0.3; }
    const tr = 7.2 + i * 0.13;
    if (t > 6.7 && t < tr) { const k = seg(t, 6.75, tr - 0.05); p.armR = [lerp(-0.5, -2.8, k), -0.3]; p.elbowR = lerp(-0.7, -1.4, k); }
    if (t >= tr) { p.capWorn = null; const k = seg(t, tr, tr + 0.25); p.armR = [lerp(-2.8, -1.2, k), -0.2]; p.elbowR = -0.3; p.grin = 1; p.mouth = 0.6; p.eyes = 0.3; }
    return { pos: SEATS[i], yaw: y, p, sc: m.sc };
  }
  // the true version: they hold the caps, calm and quiet; the chief watches the man below
  const target = t < T.rise ? SIT : SLAM;
  let y = yawTo(SEATS[i], target);
  p.lean = 0.32; p.headPitch = 0.5; p.capHeld = m.cap; p.armL = [-0.55, 0.38]; p.armR = [-0.55, -0.38]; p.elbowL = -0.85; p.elbowR = -0.85; p.brow = 0.25; p.eyes = 1;
  if (!m.sardar && t > T.notJoke && t < T.help) { y = yawTo(SEATS[i], SEATS[0]); p.headPitch = 0.15; }   // they all look to the chief
  if (m.sardar) {
    p.brow = t > T.knew ? 0.75 : 0.35; p.headPitch = t < T.tree || (t > T.knew && t < T.caps) ? 0.32 : 0.55;
    if (Math.abs(t - 21.7) < 0.12 || Math.abs(t - 12.2) < 0.1) p.eyes = 0.05;            // blinks
    if (t > T.knew && t < T.caps) p.headTilt = 0.18 * seg(t, T.knew, 21.6);
    if (t > T.caps && t < T.kids) { p.headPitch = 0.95; p.eyes = 0.6; }                     // looks at the cap in his hands
    if (t > T.notJoke && t < T.help) {                                                        // turns to the troop and nods
      p.headYaw = t < 32.9 ? 0.7 * seg(t, 32.0, 32.4) : lerp(0.7, -0.2, seg(t, 32.9, 33.2));
      p.headPitch = 0.25 + (t > 33.3 ? 0.22 * Math.max(0, Math.sin((t - 33.3) * 11)) : 0);
    }
  }
  if (t >= m.drop - 0.35) {   // leans forward and lets the cap go, gently
    const k = seg(t, m.drop - 0.35, m.drop); p.lean = 0.32 + 0.25 * k; p.armL = [lerp(-0.55, -1.5, k), lerp(0.38, 0.25, k)]; p.armR = [lerp(-0.55, -1.5, k), lerp(-0.38, -0.25, k)]; p.elbowL = lerp(-0.85, -0.3, k); p.elbowR = lerp(-0.85, -0.3, k);
    if (t >= m.drop) { p.capHeld = null; p.headPitch = 0.75; }
  }
  return { pos: SEATS[i], yaw: y, p, sc: m.sc };
}

// ------------------------------------------------------------------ light presets
const NOON: SkyPreset = { sunElev: 58, sunAz: 205, turbidity: 3, rayleigh: 2.2, exposure: 0.5, env: 0.9 };
const GOLD: SkyPreset = { sunElev: 12, sunAz: 158, turbidity: 9, rayleigh: 2.6, exposure: 0.48, env: 0.75 };
const MORN: SkyPreset = { sunElev: 18, sunAz: 72, turbidity: 4, rayleigh: 1.2, exposure: 0.5, env: 0.9 };

// ------------------------------------------------------------------ the tree set
const TreeSet: React.FC<{ t: number; preset: SkyPreset }> = ({ t, preset }) => {
  const bark = useMemo(() => new THREE.MeshStandardMaterial({ map: barkTex(2, 3), roughness: 0.95, color: "#ffffff" }), []);
  const barkFine = useMemo(() => new THREE.MeshStandardMaterial({ map: barkTex(1, 2), roughness: 0.95, color: "#ffffff" }), []);
  const ground = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(40), roughness: 1, color: "#ffffff" }), []);
  const road = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(30, "#a48464"), roughness: 1, color: "#ffffff" }), []);
  const leaves = useLeaves([
    { c: [2.9, 4.35, 0.8], r: 1.15, n: 480 }, { c: [-2.6, 4.5, 1.0], r: 1.15, n: 480 }, { c: [-1.0, 4.55, 2.2], r: 0.85, n: 280 },
    { c: [-0.9, 4.7, -1.9], r: 1.3, n: 520 }, { c: [1.9, 4.95, -1.3], r: 1.3, n: 520 }, { c: [0.1, 5.5, 0.0], r: 1.8, n: 950 },
    { c: [1.4, 5.0, 0.9], r: 0.95, n: 320 }, { c: [-1.3, 5.0, 0.4], r: 1.0, n: 360 }, { c: [2.8, 5.0, -0.2], r: 1.1, n: 380 }, { c: [-2.7, 5.1, -0.6], r: 1.1, n: 380 },
    { c: [0.5, 5.1, -2.4], r: 1.0, n: 320 }, { c: [-1.6, 5.6, -1.0], r: 1.0, n: 320 },
], 11);
  const far = useLeaves(Array.from({ length: 14 }, (_, k) => { const a = k * 0.45 + 2.2, d = 16 + (k % 4) * 5; return { c: [Math.cos(a) * d, 3.2 + (k % 3), -Math.abs(Math.sin(a)) * d - 6] as V, r: 2.2 + (k % 3) * 0.5, n: 160 }; }), 23, 0.6);
  const grass = useGrass(2600, 5, (r) => { const x = -18 + r() * 36, z = -16 + r() * 26; if (Math.abs(z - 3.4) < 1.9) return null; if (x * x + z * z < 2.6) return null; if (Math.hypot(x - 0.7, z - 1.2) < 1.3) return null; return [x, z]; });
  const sun = sunDir(preset);
  const sway = Math.sin(t * 0.9) * 0.006;
  const gold = preset === GOLD;
  return (
    <group>
      <SkyEnv preset={preset} name={preset === GOLD ? "gold" : preset === NOON ? "noon" : "morn"} />
      <fog attach="fog" args={[gold ? "#e8c8a0" : preset === NOON ? "#d8dce0" : "#c8d4e0", 14, 80]} />
      <directionalLight position={[sun.x * 25, sun.y * 25, sun.z * 25]} intensity={gold ? 3.2 : preset === NOON ? 3.4 : 2.6} color={gold ? "#ffc890" : preset === NOON ? "#fff6ea" : "#ffe6cc"} castShadow
        shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-camera-left={-8} shadow-camera-right={8} shadow-camera-top={8} shadow-camera-bottom={-8} shadow-camera-near={1} shadow-camera-far={60} shadow-bias={-0.0004} shadow-normalBias={0.02} />
      <directionalLight position={[2, 3, 8]} intensity={gold ? 0.55 : 0.35} color={gold ? "#ffe0c0" : "#e8f0ff"} />
      <hemisphereLight args={[gold ? "#ffd8b0" : "#b8d0f0", "#6a5034", 0.35]} />
      {/* ground, road, grass, rocks */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} material={ground} receiveShadow><planeGeometry args={[160, 160]} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.003, 3.4]} material={road} receiveShadow><planeGeometry args={[160, 3.2]} /></mesh>
      <primitive object={grass} />
      {useMemo(() => { const r = rng(9); return Array.from({ length: 40 }, (_, k) => { const x = -9 + r() * 18, z = -6 + r() * 12; if (Math.abs(z - 3.4) < 1.5 || Math.hypot(x - 0.7, z - 1.2) < 1.2) return null;
        return <mesh key={k} position={[x, 0.02, z]} rotation={[r() * 3, r() * 3, 0]} scale={[0.06 + r() * 0.12, 0.04 + r() * 0.06, 0.06 + r() * 0.1]} material={plainMat("#8a8274", 0.95)} castShadow receiveShadow><dodecahedronGeometry args={[1, 1]} /></mesh>; }); }, [])}
      {/* the banyan */}
      <mesh position={[0, 1.7, 0]} material={bark} castShadow receiveShadow><cylinderGeometry args={[0.34, 0.52, 3.4, 22]} /></mesh>
      {[0, 1.3, 2.5, 3.7, 5.0].map((a, k) => <Branch key={k} a={[Math.cos(a) * 0.3, 0.0, Math.sin(a) * 0.3]} b={[Math.cos(a) * 0.22, 3.0, Math.sin(a) * 0.22]} r0={0.2} r1={0.12} m={barkFine} />)}
      {[0.4, 1.5, 2.6, 3.6, 4.6, 5.6].map((a, k) => <Branch key={"r" + k} a={[Math.cos(a) * 0.35, 0.55, Math.sin(a) * 0.35]} b={[Math.cos(a) * 1.05, -0.02, Math.sin(a) * 1.05]} r0={0.17} r1={0.05} m={barkFine} />)}
      {BRANCHES.map((b, k) => <Branch key={"b" + k} a={b.a} b={b.b} r0={b.r0} r1={b.r1} m={barkFine} />)}
      {/* aerial roots hanging from the branches (banyan), kept off the camera side */}
      {[[-1.6, 3.15, 0.6], [-2.1, 3.3, 0.75], [-0.6, 3.5, -1.2], [1.2, 3.75, -0.85], [1.6, 3.95, -1.1], [-0.4, 3.3, -0.9], [2.4, 3.15, 0.6]].map(([x, y, z], k) => (
        <mesh key={"a" + k} position={[x, (y + 0.6 + (k % 3) * 0.4) / 2, z]} material={barkFine} castShadow><cylinderGeometry args={[0.012 + (k % 2) * 0.01, 0.02, y - 0.6 - (k % 3) * 0.4, 6]} /></mesh>
      ))}
      <group rotation={[sway, 0, sway * 0.7]}><primitive object={leaves} /></group>
      {/* the far line of trees, huts and hills */}
      <primitive object={far} />
      {Array.from({ length: 14 }, (_, k) => { const a = k * 0.45 + 2.2, d = 16 + (k % 4) * 5; return <mesh key={"ft" + k} position={[Math.cos(a) * d, 1.5, -Math.abs(Math.sin(a)) * d - 6]} material={bark}><cylinderGeometry args={[0.18, 0.28, 3, 8]} /></mesh>; })}
      {[[-9, -14, 0.2], [-5.5, -17, -0.3], [8, -15, 0.5], [13, -11, 0.1]].map(([x, z, r], k) => (
        <group key={"h" + k} position={[x, 0, z]} rotation={[0, r, 0]}>
          <mesh position={[0, 0.9, 0]} material={mat("mudw", () => new THREE.MeshStandardMaterial({ map: mudTex(2), roughness: 1 }))} castShadow receiveShadow><boxGeometry args={[3, 1.8, 2.4]} /></mesh>
          <mesh position={[0, 2.3, 0]} rotation={[0, Math.PI / 4, 0]} material={mat("thatch", () => new THREE.MeshStandardMaterial({ map: strawTex(3), roughness: 1 }))} castShadow><coneGeometry args={[2.4, 1.3, 4]} /></mesh>
        </group>
      ))}
      {[[-40, -70, 26], [10, -80, 34], [55, -65, 24]].map(([x, z, r], k) => <mesh key={"hill" + k} position={[x, -r * 0.72, z]} scale={[r * 1.6, r, r]} material={plainMat("#6a7a48", 1)}><sphereGeometry args={[1, 24, 12]} /></mesh>)}
      {/* the cap-seller's empty cloth in the true version; his stack of caps in the morning */}
      {t >= T.truth && t < T.people ? <mesh position={[1.05, 0.006, 1.05]} rotation={[-Math.PI / 2, 0, 0.4]} material={clothMat("#8a2a24", 1)} receiveShadow><planeGeometry args={[0.9, 0.8]} /></mesh> : null}
      {t >= T.people ? (
        <group position={[-1.25, 0, 2.55]}>
          <mesh position={[0, 0.006, 0]} rotation={[-Math.PI / 2, 0, 0.2]} material={clothMat("#8a2a24", 1)} receiveShadow><planeGeometry args={[0.8, 0.7]} /></mesh>
          {Array.from({ length: 9 }, (_, k) => <Cap key={k} color={CAP_COLORS[(k + 3) % CAP_COLORS.length]} p={[(k % 3 - 1) * 0.2, 0.002 + Math.floor(k / 3) * 0.035, (Math.floor(k / 3) - 1) * 0.08]} r={[0, k, 0]} />)}
        </group>
      ) : null}
      {/* god rays through the canopy in the golden light */}
      {gold ? [[-1.2, 0.2], [0.3, -0.6], [1.4, 0.1], [-0.3, 0.9], [0.9, -1.2]].map(([x, z], k) => {
        const len = 7; const d = sun.clone().multiplyScalar(-1); const a = new THREE.Vector3(x, 5.2, z); const c = a.clone().addScaledVector(d, len / 2);
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d);
        return <mesh key={"ray" + k} position={c} quaternion={q}><cylinderGeometry args={[0.18 + k * 0.03, 0.5, len, 10, 1, true]} /><meshBasicMaterial color="#ffd8a0" transparent opacity={0.045 + 0.015 * Math.sin(t * 0.7 + k)} blending={THREE.AdditiveBlending} depthWrite={false} side={THREE.DoubleSide} fog={false} /></mesh>;
      }) : null}
      {gold ? Array.from({ length: 70 }, (_, k) => { const r = rng(100 + k); const x = -1.5 + r() * 3.5, z = 0.2 + r() * 3.2, y = 0.3 + ((r() * 2.6 + t * 0.06 * (0.5 + r())) % 2.6);
        return <mesh key={"m" + k} position={[x + 0.1 * Math.sin(t * 0.5 + k), y, z]} scale={0.006 + r() * 0.006} material={mat("mote", () => new THREE.MeshBasicMaterial({ color: "#ffe8c0", transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }))}><sphereGeometry args={[1, 6, 4]} /></mesh>; }) : null}
    </group>
  );
};

// dust kicked up where the cap hits the dirt
const Dust: React.FC<{ at: V; t0: number; t: number; big?: number }> = ({ at, t0, t, big = 1 }) => {
  const u = (t - t0) / 1.1; if (u < 0 || u > 1) return null;
  return <group position={at}>{Array.from({ length: 12 }, (_, k) => { const a = k * 0.52, r = (0.08 + 0.45 * Math.sqrt(u)) * big * (0.7 + (k % 3) * 0.2);
    return <mesh key={k} position={[Math.cos(a) * r, 0.04 + u * 0.25 * big * (0.5 + (k % 2)), Math.sin(a) * r]} scale={(0.05 + u * 0.16) * big}><sphereGeometry args={[1, 10, 8]} /><meshStandardMaterial color="#b89a74" transparent opacity={0.4 * (1 - u)} depthWrite={false} roughness={1} /></mesh>; })}</group>;
};

// ------------------------------------------------------------------ the hut at night (its own set, at the origin)
const HutSet: React.FC<{ t: number }> = ({ t }) => {
  const { scene, gl } = useThree();
  scene.environment = null; gl.toneMappingExposure = 1.0;
  const sky = useMemo(() => nightSkyMat(), []);
  const wall = useMemo(() => new THREE.MeshStandardMaterial({ map: mudTex(2), roughness: 1 }), []);
  const floor = useMemo(() => new THREE.MeshStandardMaterial({ map: mudTex(6, "#a88660"), roughness: 1 }), []);
  const groundM = useMemo(() => new THREE.MeshStandardMaterial({ map: dirtTex(30), roughness: 1 }), []);
  const thatch = useMemo(() => new THREE.MeshStandardMaterial({ map: strawTex(4), roughness: 1 }), []);
  const rope = useMemo(() => new THREE.MeshStandardMaterial({ map: ropeTex(4), roughness: 1 }), []);
  const wood = useMemo(() => new THREE.MeshStandardMaterial({ map: woodTex(), roughness: 0.9 }), []);
  const steel = plainMat("#d8d8dc", 0.22, 0.95);
  const fireOn = t >= T.night;
  const flick = 0.75 + 0.15 * Math.sin(t * 23) + 0.1 * Math.sin(t * 37 + 1);
  const roar = fireOn ? lerp(0.7, 1.25, seg(t, 44.1, 44.7)) : 0;
  const diyaDying = t < T.night ? lerp(1, 0.45, seg(t, 25.9, 27.1)) * (0.8 + 0.2 * Math.sin(t * 31)) : 0;
  const CH: V = [1.3, 0, 0.0];
  const kidsSleep = t < T.night;
  // characters
  const sleeper = (look: HLook, z: number, side: number) => { const p = hRest(); p.sit = 0.35; p.eyes = 0; p.brow = 0.35; p.smile = -0.15; p.armL = [-0.9, 0.2]; p.armR = [-0.9, -0.2]; p.elbowL = -1.3; p.elbowR = -1.3; p.spine = 0.15;
    return <group position={[-0.95, 0.5, z]} rotation={[0, 0.25 + Math.PI / 2, 0]}><group rotation={[0, 0, (Math.PI / 2) * side]}><group rotation={[-Math.PI / 2, 0, 0]} scale={0.56}><Human look={look} p={p} /></group></group></group>; };
  const fam = () => {
    const w = hRest(); w.sit = 1; w.spine = 0.25; w.smile = 0.75; w.eyes = 0.8; w.headPitch = 0.2; w.armR = [-1.3, -0.1]; w.elbowR = -0.4 + 0.2 * Math.sin(t * 3); w.armL = [-1.0, 0.2]; w.elbowL = -0.6;
    const b = hRest(); b.sit = 1; b.spine = 0.2; b.smile = 1; b.mouth = 0.25 * Math.abs(Math.sin(t * 5)); b.eyes = 0.2; b.armR = [-1.6, -0.1]; b.elbowR = -1.5 + 0.4 * Math.sin(t * 4);
    const g = hRest(); g.sit = 1; g.spine = 0.2; g.smile = 1; g.eyes = 0.9; g.armR = [-1.4, -0.1]; g.elbowR = -1.6; g.headYaw = 0.3; g.headRoll = 0.1 * Math.sin(t * 2);
    const s = hRest(); s.sit = 1; s.spine = 0.15; s.smile = 0.9; s.eyes = 0.55; s.headPitch = 0.05; s.armL = [-1.0, 0.25]; s.armR = [-1.0, -0.25]; s.elbowL = 0.9; s.elbowR = 0.9; s.capOnHead = true;
    return (
      <>
        <group position={[1.95, 0, 0.12]} rotation={[0, -Math.PI / 2, 0]} scale={0.9}><Human look={WIFE} p={w} /></group>
        <group position={[0.55, 0, 0.4]} rotation={[0, Math.PI / 2 - 0.2, 0]} scale={0.58}><Human look={BOY} p={b} /></group>
        <group position={[0.55, 0, 0.95]} rotation={[0, 2.1, 0]} scale={0.55}><Human look={GIRL} p={g} /></group>
        <group position={[0.05, 0, -0.25]} rotation={[0, 1.1, 0]} scale={S_SELLER}><Human look={SELLER} p={s} /></group>
      </>
    );
  };
  const sardar = { ...mRest(), lean: 0.4, headPitch: 0.55, capWorn: CAP_COLORS[0], eyes: t > 45.3 ? 0.1 : 1, brow: 0.1, tail: t };
  return (
    <group>
      <mesh material={sky} scale={500}><sphereGeometry args={[1, 32, 16]} /></mesh>
      <mesh position={[-140, 150, -380]}><sphereGeometry args={[13, 24, 16]} /><meshBasicMaterial color="#f2eedc" fog={false} /></mesh>
      <mesh position={[-140, 150, -381]}><sphereGeometry args={[34, 24, 16]} /><meshBasicMaterial color="#5a6a9a" transparent opacity={0.18} fog={false} depthWrite={false} /></mesh>
      <fog attach="fog" args={["#141a2c", 10, 45]} />
      <ambientLight intensity={0.5} color="#6a7aaa" />
      <hemisphereLight args={["#4a5a8a", "#20180c", 0.35]} />
      <directionalLight position={[-6, 9, -7]} intensity={2.0} color="#9ab0e0" castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-6} shadow-camera-right={6} shadow-camera-top={6} shadow-camera-bottom={-6} shadow-bias={-0.0005} />
      {fireOn ? <pointLight position={[CH[0], 0.35, CH[2] + 0.15]} intensity={roar * flick * 14} distance={11} decay={1.5} color="#ff9440" /> : null}
      {diyaDying > 0 ? <pointLight position={[-0.35, 0.14, 0.6]} intensity={diyaDying * 3.2} distance={4.5} decay={1.6} color="#ffb060" /> : null}
      <pointLight position={[0.4, 1.5, -0.7]} intensity={fireOn ? 0.8 : 0.0} distance={4} color="#ffb070" />
      {/* ground, courtyard, hut */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} material={groundM} receiveShadow><planeGeometry args={[120, 120]} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.004, 0.3]} material={floor} receiveShadow><circleGeometry args={[4.2, 40]} /></mesh>
      <mesh position={[0, 1.0, -2.3]} material={wall} castShadow receiveShadow><boxGeometry args={[3.4, 2.0, 2.8]} /></mesh>
      <mesh position={[0.4, 0.78, -0.895]} material={basicMat("#0a0806")}><planeGeometry args={[0.8, 1.55]} /></mesh>
      <mesh position={[-1.0, 1.2, -0.895]} material={fireOn ? basicMat("#c8702a") : basicMat("#0a0806")}><planeGeometry args={[0.4, 0.35]} /></mesh>
      <mesh position={[0, 2.75, -2.3]} rotation={[0, Math.PI / 4, 0]} material={thatch} castShadow receiveShadow><coneGeometry args={[2.75, 1.5, 4, 1]} /></mesh>
      {/* the charpai */}
      <group position={[-1.5, 0, 0.3]} rotation={[0, 0.25, 0]}>
        {[[-0.9, -0.42], [0.9, -0.42], [-0.9, 0.42], [0.9, 0.42]].map(([x, z], k) => <mesh key={k} position={[x, 0.2, z]} material={wood} castShadow><cylinderGeometry args={[0.035, 0.03, 0.4, 8]} /></mesh>)}
        {[-0.44, 0.44].map((z, k) => <mesh key={"l" + k} position={[0, 0.4, z]} material={wood} castShadow><boxGeometry args={[1.9, 0.06, 0.06]} /></mesh>)}
        {[-0.92, 0.92].map((x, k) => <mesh key={"w" + k} position={[x, 0.4, 0]} material={wood} castShadow><boxGeometry args={[0.06, 0.06, 0.9]} /></mesh>)}
        <mesh position={[0, 0.41, 0]} rotation={[-Math.PI / 2, 0, 0]} material={rope} castShadow receiveShadow><planeGeometry args={[1.8, 0.84]} /></mesh>
        <mesh position={[-0.75, 0.47, 0]} rotation={[Math.PI / 2, 0, 0]} material={clothMat("#7a6a8a", 1)} castShadow><cylinderGeometry args={[0.07, 0.07, 0.7, 12]} /></mesh>
      </group>
      {kidsSleep ? <>{sleeper(BOY, 0.12, 1)}{sleeper(GIRL, 0.45, 1)}</> : fam()}
      {/* the empty thali, the upturned pot, the diya */}
      {kidsSleep ? (
        <>
          <group position={[-0.5, 0.0, 0.95]}><mesh position={[0, 0.008, 0]} material={steel} castShadow receiveShadow><cylinderGeometry args={[0.17, 0.16, 0.016, 32]} /></mesh>
            <mesh position={[0, 0.018, 0]} rotation={[Math.PI / 2, 0, 0]} material={steel}><torusGeometry args={[0.165, 0.008, 6, 32]} /></mesh></group>
          <mesh position={[-0.85, 0.11, 1.18]} rotation={[Math.PI, 0, 0]} material={plainMat("#8a4a2a", 0.85)} castShadow><sphereGeometry args={[0.14, 20, 12, 0, Math.PI * 2, 0, Math.PI * 0.62]} /></mesh>
          <group position={[-0.35, 0, 0.6]}>
            <mesh position={[0, 0.02, 0]} material={plainMat("#9a5a30", 0.9)} castShadow><sphereGeometry args={[0.045, 14, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2]} /></mesh>
            <mesh position={[0.02, 0.055 + 0.005 * Math.sin(t * 29), 0]} scale={[0.012, 0.03 * diyaDying, 0.012]}><sphereGeometry args={[1, 10, 8]} /><meshBasicMaterial color="#ffd080" /></mesh>
          </group>
        </>
      ) : (
        <group position={[0.95, 0.0, 0.72]}>
          <mesh position={[0, 0.008, 0]} material={steel} castShadow receiveShadow><cylinderGeometry args={[0.17, 0.16, 0.016, 32]} /></mesh>
          {[0, 1, 2].map((k) => <mesh key={k} position={[0.03, 0.02 + k * 0.006, -0.02]} material={plainMat("#d8a860", 0.9)} castShadow><cylinderGeometry args={[0.09, 0.09, 0.006, 24]} /></mesh>)}
          <mesh position={[-0.09, 0.03, 0.07]} material={steel}><sphereGeometry args={[0.045, 16, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2]} /></mesh>
          <mesh position={[-0.09, 0.028, 0.07]} rotation={[-Math.PI / 2, 0, 0]} material={plainMat("#c8901a", 0.6)}><circleGeometry args={[0.04, 16]} /></mesh>
        </group>
      )}
      {/* the chulha: clay U, wood, fire, tawa and roti */}
      <group position={CH}>
        {[[-0.25, 0, 0.12, 0.42], [0.25, 0, 0.12, 0.42], [0, -0.18, 0.5, 0.1]].map(([x, z, w, d], k) => <mesh key={k} position={[x, 0.15, z]} material={wall} castShadow receiveShadow><boxGeometry args={[w, 0.3, d]} /></mesh>)}
        {[-0.1, 0.05, 0.12].map((x, k) => <mesh key={"w" + k} position={[x, 0.05, 0.25]} rotation={[Math.PI / 2 - 0.15, 0, x * 2]} material={wood} castShadow><cylinderGeometry args={[0.025, 0.03, 0.5, 6]} /></mesh>)}
        <mesh position={[0, 0.315, 0]} material={plainMat("#26221e", 0.45, 0.6)} castShadow receiveShadow><cylinderGeometry args={[0.21, 0.19, 0.02, 32]} /></mesh>
        {fireOn ? <mesh position={[0, 0.33 + 0.02 * seg(t, 44.0, 45.0), 0]} scale={[1, 1 + 2.5 * seg(t, 44.2, 45.0), 1]} material={plainMat("#e0b070", 0.9)} castShadow><cylinderGeometry args={[0.12, 0.12, 0.008, 24]} /></mesh> : null}
        {fireOn ? Array.from({ length: 9 }, (_, k) => { const h = (0.22 + 0.08 * Math.sin(t * (8 + k) + k * 1.7)) * roar; return (
          <mesh key={"f" + k} position={[((k % 3) - 1) * 0.05, 0.02 + h / 2, 0.02 + 0.015 * Math.sin(k)]} rotation={[0, (k * Math.PI) / 3 + 0.2 * Math.sin(t * 3 + k), 0.08 * Math.sin(t * 6 + k)]} scale={[0.16 - (k % 3) * 0.02, h, 1]}>
            <planeGeometry args={[1, 1]} /><meshBasicMaterial map={flameTex()} transparent opacity={0.9} blending={THREE.AdditiveBlending} depthWrite={false} side={THREE.DoubleSide} />
          </mesh>); }) : null}
        {fireOn ? Array.from({ length: 10 }, (_, k) => { const u = ((t * 0.6 + k * 0.137) % 1); return <mesh key={"e" + k} position={[0.1 * Math.sin(k * 3 + t), 0.35 + u * 0.9, 0.05 + 0.08 * Math.cos(k)]} scale={0.006}><sphereGeometry args={[1, 5, 4]} /><meshBasicMaterial color="#ffb050" transparent opacity={1 - u} blending={THREE.AdditiveBlending} depthWrite={false} /></mesh>; }) : null}
        {fireOn ? Array.from({ length: 6 }, (_, k) => { const u = ((t * 0.25 + k / 6) % 1); return <mesh key={"s" + k} position={[0.05 * Math.sin(k + t), 0.45 + u * 1.6, -0.05 + u * 0.2]} scale={0.08 + u * 0.25}><sphereGeometry args={[1, 10, 8]} /><meshStandardMaterial color="#6a6a70" transparent opacity={0.12 * (1 - u)} depthWrite={false} /></mesh>; }) : null}
      </group>
      {/* the chief, on the roof, wearing the red cap the man gave him */}
      {fireOn ? <group position={[0.95, 2.2, -0.6]} rotation={[0, -0.15, 0]} scale={1.25}><Monkey look={SARDAR_LOOK} p={sardar} /></group> : null}
      {/* a low mud boundary and dark trees beyond */}
      {Array.from({ length: 9 }, (_, k) => { const a = -0.3 + k * 0.42; return <mesh key={"bw" + k} position={[Math.cos(a) * 5.2, 0.3, Math.sin(a) * 5.2 + 0.3]} rotation={[0, -a, 0]} material={wall} receiveShadow><boxGeometry args={[0.2, 0.6, 2.25]} /></mesh>; })}
      {[[-7, -6], [6, -8], [-3, -11], [9, -3]].map(([x, z], k) => <group key={"nt" + k} position={[x, 0, z]}><mesh position={[0, 1.5, 0]} material={plainMat("#1a1610", 1)}><cylinderGeometry args={[0.15, 0.25, 3, 8]} /></mesh><mesh position={[0, 3.6, 0]} material={plainMat("#0e1410", 1)}><sphereGeometry args={[1.8, 14, 10]} /></mesh></group>)}
    </group>
  );
};

// ------------------------------------------------------------------ camera
type Cam = { pos: V; target: V; fov: number; roll?: number };
const SELLER_HEAD_SIT: V = (() => { const f = fwd(SIT_YAW, 0.29); return [SIT[0] + f[0], 0.8, SIT[2] + f[1]]; })();
const CHAPPAL: V = (() => { const c = Math.cos(SIT_YAW), sn = Math.sin(SIT_YAW); const x = 0.34, z = 0.6; return [SIT[0] + x * c + z * sn, 0, SIT[2] - x * sn + z * c]; })();
function camAt(t: number): Cam {
  const side = (yaw: number, d: number): [number, number] => [Math.cos(yaw) * d, -Math.sin(yaw) * d];
  // the classic tale (t is the story time, so the rewind runs back through these shots)
  if (t < T.mock) { const k = seg(t, 0, T.mock); return { pos: lerp3([2.6, 3.4, 4.8], [2.3, 1.1, 5.0], k), target: lerp3([0.8, 3.1, 0.4], [0.9, 1.25, 1.5], k), fov: 46 }; }
  if (t < 4.4) { const y = yawTo(SEATS[1], SLAM); return { pos: orbit(SEATS[1], y, 0.25, 1.3, 0.15), target: add(SEATS[1], [0, 0.28, 0]), fov: 34 }; }
  if (t < T.throwSeq) { const y = yawTo(SEATS[2], SLAM); return { pos: orbit(SEATS[2], y, 0.35, 1.3, 0.12), target: add(SEATS[2], [0, 0.28, 0]), fov: 34 }; }
  if (t < 7.5) return { pos: [3.0, 0.9, 1.9], target: [0.9, 1.3, 1.3], fov: 46 };
  if (t < T.truth) { const k = seg(t, 7.5, T.truth); return { pos: lerp3([2.4, 0.9, 0.3], [2.25, 0.9, 0.45], k), target: [0.9, 1.45, 1.4], fov: 50 }; }
  // the truth
  if (t < T.tree) { const k = seg(t, T.truth, T.tree); return { pos: orbit(SARDAR_HEAD, SARDAR_YAW, 0.45, lerp(1.6, 0.9, k), -0.22), target: add(SARDAR_HEAD, [0, -0.02, 0]), fov: 34 }; }
  if (t < T.cry) { const k = seg(t, T.tree, T.cry); return { pos: lerp3([3.6, 0.45, 5.4], [3.0, 0.45, 5.6], k), target: [0.4, 2.7, 0.3], fov: 52 }; }
  if (t < T.poor) { const f = fwd(SARDAR_YAW, 0.1); return { pos: [SARDAR_HEAD[0] + f[0], SARDAR_HEAD[1] + 0.04, SARDAR_HEAD[2] + f[1]], target: add(SELLER_HEAD_SIT, [0, -0.1, 0]), fov: lerp(44, 36, seg(t, T.cry, T.poor)) }; }   // his eyes
  if (t < T.chappal) return { pos: orbit(SIT, SIT_YAW, -0.45, 1.75, 1.05), target: add(SELLER_HEAD_SIT, [0, -0.18, 0]), fov: 38 };
  if (t < T.face) return { pos: orbit(CHAPPAL, SIT_YAW, 0.9, 0.5, 0.2), target: add(CHAPPAL, [-0.04, 0.02, 0]), fov: 34 };
  if (t < T.knew) { const k = seg(t, T.face, T.knew); const f = fwd(SIT_YAW, lerp(0.6, 0.48, k)); return { pos: [SELLER_HEAD_SIT[0] + f[0], 0.62, SELLER_HEAD_SIT[2] + f[1]], target: add(SELLER_HEAD_SIT, [0, -0.02, 0]), fov: 32 }; }
  if (t < T.caps) return { pos: orbit(SARDAR_HEAD, SARDAR_YAW, 0.15, 0.55, -0.1), target: SARDAR_HEAD, fov: 28 };
  if (t < T.kids) { const c = heldCapWorld(0, SARDAR_YAW); return { pos: orbit(SARDAR_HEAD, SARDAR_YAW, -0.35, 0.85, -0.32), target: lerp3(SARDAR_HEAD, c, 0.5), fov: 34 }; }
  // what he imagines: the man's children sleeping hungry (hut set)
  if (t < T.hungry) { const k = seg(t, T.kids, T.hungry); return { pos: lerp3([-1.4, 1.65, 1.3], [-1.5, 1.45, 1.1], k), target: [-1.6, 0.45, 0.35], fov: 38 }; }
  if (t < T.rise) return { pos: [-0.22, 0.24, 1.55], target: [-0.5, 0.06, 0.9], fov: 36 };
  // back at the tree
  if (t < T.anger) { const k = seg(t, T.rise, T.anger); return { pos: [2.4, 1.1, 2.9], target: lerp3([0.5, 0.75, 0.8], [0.95, 1.25, 1.6], k), fov: 40 }; }
  if (t < T.dirt) { const f = fwd(SLAM_YAW, 1.45), sd = side(SLAM_YAW, 0.35); return { pos: [SLAM[0] + f[0] + sd[0], 0.95, SLAM[2] + f[1] + sd[1]], target: [SLAM[0], 1.38, SLAM[2]], fov: 42, roll: 0.15 }; }
  if (t < T.notJoke) { const sh = 0.02 * Math.exp(-(t - T.dirt) * 6) * Math.sin(t * 90); const c = SELLER_CAP_TRUE_LAND; return { pos: [c[0] + 0.45, 0.12 + sh, c[2] + 0.38], target: [c[0], 0.04, c[2]], fov: 36 }; }
  if (t < T.help) return { pos: orbit(SARDAR_HEAD2, SARDAR_YAW2, -0.4, 1.2, -0.15), target: add(SARDAR_HEAD2, [0, -0.08, 0]), fov: 36 };
  if (t < T.drop) return { pos: [-0.55, 1.75, 1.75], target: [-1.3, 3.05, 0.5], fov: 44 };
  if (t < T.people) { const k = seg(t, T.drop, T.people); return { pos: lerp3([2.45, 0.42, 0.25], [2.3, 0.4, 0.4], k), target: [0.85, 1.75, 1.4], fov: 52 }; }
  // that morning
  if (t < T.close) return { pos: [-0.4, 1.15, 6.4], target: [-0.6, 1.0, 2.6], fov: 38 };
  if (t < T.night) return { pos: orbit(ROAD, ROAD_YAW, 0.9, 1.4, 1.3), target: [-0.65, 1.2, 2.75], fov: 38 };
  // that night (hut set)
  if (t < T.chulha) return { pos: [1.35, 1.25, 1.2], target: [0.95, 2.35, -0.6], fov: 36 };
  if (t < T.crane) return { pos: [1.68, 0.78, 0.9], target: [1.3, 0.24, 0.04], fov: 38 };
  const k = smooth((t - T.crane) / (END - T.crane));
  return { pos: lerp3([2.6, 1.0, 2.6], [2.2, 3.2, 4.4], k), target: lerp3([0.8, 0.4, 0.4], [0.6, 2.0, -0.6], k), fov: 46 };
}
const CameraRig: React.FC<{ t: number }> = ({ t }) => {
  const { camera } = useThree();
  const k = camAt(t);
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(...k.pos); cam.fov = k.fov; cam.near = 0.02; cam.far = 2000;
  cam.up.set(Math.sin(k.roll ?? 0), Math.cos(k.roll ?? 0), 0); cam.lookAt(new THREE.Vector3(...k.target)); cam.updateProjectionMatrix();
  return null;
};

// which set and light a moment belongs to
const isNight = (t: number) => (t >= T.kids && t < T.rise) || t >= T.night;
const storyTime = (t: number) => (t >= T.rewind && t < T.truth ? Math.max(1.0, T.rewind - (t - T.rewind) * 11) : t);

const Scene: React.FC<{ t: number }> = ({ t }) => {
  const ts = storyTime(t);
  if (isNight(t)) return (<><CameraRig t={t} /><HutSet t={t} /></>);
  const preset = ts < T.truth ? NOON : t < T.people ? GOLD : MORN;
  const seller = sellerAt(ts);
  const falls = ts < T.truth ? CLASSIC_FALLS : t < T.people ? TRUE_FALLS : [];
  return (
    <>
      <CameraRig t={ts} />
      <TreeSet t={ts} preset={preset} />
      {seller ? <group position={seller.pos} rotation={[0, seller.yaw, 0]} scale={seller.s}><Human look={seller.look} p={seller.p} /></group> : null}
      {villagersAt(t).map((v, k) => (
        <group key={"v" + k} position={v.pos} rotation={[0, v.yaw, 0]} scale={v.s}>
          <Human look={v.look} p={{ ...v.p, handR: k === 0 ? <group position={[0.05, 0.05, -0.06]}><mesh material={plainMat("#8a6a3a", 1)} castShadow><cylinderGeometry args={[0.2, 0.13, 0.14, 16, 1, true]} /></mesh>{[0, 1, 2, 3].map((q) => <mesh key={q} position={[(q - 1.5) * 0.07, 0.07, 0.03 * (q % 2)]} material={plainMat(q % 2 ? "#3a8a2a" : "#c84a20", 0.7)}><sphereGeometry args={[0.05, 10, 8]} /></mesh>)}</group>
            : k === 1 ? <group><mesh position={[0, 0.35, 0]} material={plainMat("#2a2a2a", 0.6)} castShadow><cylinderGeometry args={[0.008, 0.008, 0.75, 6]} /></mesh></group> : <mesh position={[0, -0.4, 0.04]} material={plainMat("#6a4a2a", 0.9)} castShadow><cylinderGeometry args={[0.012, 0.012, 0.9, 6]} /></mesh> }} />
        </group>
      ))}
      {MONKEYS.map((_, i) => { const m = monkeyAt(i, ts); if (!m || (i === 0 && t >= T.cry && t < T.poor)) return null;
        return <group key={"m" + i} position={m.pos} rotation={[0, m.yaw, 0]} scale={m.sc}><Monkey look={MONKEYS[i].look} p={m.p} /></group>; })}
      {falls.map((f, k) => { const c = capPose(f, ts); if (!c) return null; return <Cap key={"c" + k} color={f.color} p={c.p} r={c.r} />; })}
      <Dust at={SELLER_CAP_TRUE_LAND} t0={31.55} t={t} />
      {t >= T.truth && t < T.rise ? (
        <group position={CHAPPAL} rotation={[0, SIT_YAW + 0.6, 0]}>
          <mesh position={[0, 0.009, 0.075]} rotation={[0, 0.12, 0]} material={plainMat("#5a4a3c", 0.9)} castShadow receiveShadow><boxGeometry args={[0.1, 0.018, 0.13]} /></mesh>
          <mesh position={[0.02, 0.008, -0.08]} rotation={[0, -0.22, 0.06]} material={plainMat("#5a4a3c", 0.9)} castShadow receiveShadow><boxGeometry args={[0.092, 0.016, 0.13]} /></mesh>
          <mesh position={[0.0, 0.012, 0.0]} rotation={[0, 0.1, 0]} material={plainMat("#3a2e26", 1)}><boxGeometry args={[0.07, 0.004, 0.03]} /></mesh>
          <mesh position={[-0.035, 0.03, 0.06]} rotation={[0.3, 0, 0.9]} material={plainMat("#7a4a2a", 0.8)} castShadow><boxGeometry args={[0.01, 0.06, 0.012]} /></mesh>
          <mesh position={[0.07, 0.012, 0.02]} rotation={[0.1, 0.6, 1.45]} material={plainMat("#7a4a2a", 0.8)} castShadow><boxGeometry args={[0.01, 0.06, 0.012]} /></mesh>
        </group>
      ) : null}
      {ts < T.truth ? <Dust at={CLASSIC_FALLS[0].to} t0={6.96} t={ts} big={0.6} /> : null}
    </>
  );
};

// ------------------------------------------------------------------ film overlays (grain, the old-tale look, the rewind, the flashback)
const Grain: React.FC<{ frame: number; amount: number }> = ({ frame, amount }) => (
  <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: amount, pointerEvents: "none" }}>
    <svg width="1080" height="1920"><filter id={"g" + frame}><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={frame} /><feColorMatrix type="saturate" values="0" /></filter>
      <rect width="1080" height="1920" filter={`url(#g${frame})`} /></svg>
  </AbsoluteFill>
);

export const Topiwala3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const sub = SUBS.find(([a, b]) => t >= a && t < b);
  const classic = t < T.truth;
  const rewinding = t >= T.rewind && t < T.truth;
  const flash = t >= T.people && t < T.night;
  const night = isNight(t);
  const flick = classic ? 0.94 + 0.06 * Math.sin(frame * 2.7) * Math.sin(frame * 1.3) : 1;
  const filter = classic ? `sepia(0.5) saturate(0.7) contrast(1.12) brightness(${flick})` : flash ? "saturate(0.42) contrast(1.06) brightness(0.98)" : night ? "contrast(1.06) saturate(1.05)" : "saturate(1.06) contrast(1.05)";
  const jitter = classic ? `translate(${(Math.sin(frame * 7.1) * 2) | 0}px, ${(Math.sin(frame * 3.3) * 2) | 0}px)` : rewinding ? `translateX(${(Math.sin(frame * 11) * 8) | 0}px) skewX(${Math.sin(frame * 5) * 2}deg)` : "none";
  // cuts: brief dips; a blur ramp into and out of the imagined night
  const cuts = [T.mock, 4.4, T.throwSeq, 7.5, T.tree, T.cry, T.poor, T.chappal, T.face, T.knew, T.caps, T.hungry, T.anger, T.dirt, T.notJoke, T.help, T.drop, T.close, T.chulha, T.crane];
  let dip = 0; for (const c of cuts) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.08);
  const dream = Math.max(1 - Math.abs(t - T.kids) / 0.35, 1 - Math.abs(t - T.rise) / 0.3, 0);
  const whiteFlash = Math.max(0, 1 - Math.abs(t - T.truth) / 0.12, 1 - Math.abs(t - T.people) / 0.12);
  const blackDip = Math.max(0, 1 - Math.abs(t - T.night) / 0.25);
  const fade = Math.min(clamp(t / 0.4), clamp((END - t) / 1.2));
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter: `${filter} blur(${(dream * 6 + (rewinding ? 1 : 0)).toFixed(2)}px)`, transform: jitter }}>
        <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
          <Scene t={t} />
        </ThreeCanvas>
      </AbsoluteFill>
      {flash ? <AbsoluteFill style={{ background: "rgba(70,100,150,0.16)", mixBlendMode: "multiply" }} /> : null}
      {classic ? (
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
      <Grain frame={frame} amount={classic ? 0.22 : 0.08} />
      {sub ? (
        <div style={{ position: "absolute", top: 1300, left: 60, right: 60, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 54, lineHeight: 1.4, color: "#faf6ee", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill", textShadow: "0 4px 14px rgba(0,0,0,0.75)" }}>{sub[2]}</div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: whiteFlash * 0.85 }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.35, blackDip) }} />
    </AbsoluteFill>
  );
};
