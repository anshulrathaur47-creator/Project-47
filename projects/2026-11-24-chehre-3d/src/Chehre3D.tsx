import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { G, Look, Person, Pose, Toon, restPose } from "./Character";
import { Buildings, Lamp, Street, Tree, rng, skyMat } from "./World";

// "ये चेहरे पे चेहरा लगा लेते हैं…" (ReelAudio-64225), 3D.
export const DURATION = 1187; // 39.57 s
const FPS = 30;
const END = DURATION / FPS;

const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (x: number) => {
  const t = clamp(x);
  return t * t * (3 - 2 * t);
};
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: number[], b: number[], t: number) => a.map((v, i) => lerp(v, b[i], t)) as [number, number, number];
const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

// Whisper word timings (chunked alignment)
const LINES: [number, number, string][] = [
  [0.0, 2.62, "ये चेहरे पे चेहरा लगा लेते हैं"],
  [2.7, 5.1, "ये दुश्मन को तेरे वफ़ा देते हैं"],
  [5.15, 7.62, "ये तेरे हैं अपने परायों से बदतर"],
  [7.66, 9.92, "ये तेरे ग़मों का मज़ा लेते हैं"],
  [10.0, 12.35, "ज़माने में मुश्किल वफ़ा हो गई"],
  [12.4, 15.0, "ये दुनिया है फ़ोन में तन्हा हो गई"],
  [15.1, 17.5, "लोग जो अपनों पे जान देते थे"],
  [17.55, 19.75, "वो नस्लें पुरानी फ़ना हो गई"],
  [19.8, 23.7, "तेरे गिरने के पीछे कोई तेरा अपना होगा"],
  [23.85, 28.9, "ये जानकर भी रिश्ता तुझको रखना होगा"],
  [29.1, 33.7, "तेरे गिरने के पीछे कोई तेरा अपना होगा"],
  [33.9, 38.7, "ये जानकर भी रिश्ता तुझको रखना होगा"],
];
const CUTS = [2.7, 5.15, 7.66, 10.0, 12.4, 15.1, 19.8, 21.25, 22.1, 23.85, 25.8, 27.3, 29.1, 33.9];

// ------------------------------------------------------------------------------------ looks (all new)
const HER: Look = { skin: "#c98a62", hair: "#3a2016", hairStyle: "bun", shirt: "#d9a23a", inner: "#7a1f2b", pants: "#2a2f45", shoes: "#f4f4f4", face: true };
const F1: Look = { skin: "#d9a07c", hair: "#1a1210", hairStyle: "ponytail", shirt: "#2f8f8a", inner: "#efe6d6", pants: "#d8ccb4", shoes: "#3a3a44", face: true };
const F2: Look = { skin: "#b97c58", hair: "#16110e", hairStyle: "curly", shirt: "#5a6f96", inner: "#f0f0f0", pants: "#30323a", shoes: "#c84a3a", face: true };
const F3: Look = { skin: "#d4976e", hair: "#24180f", hairStyle: "short", shirt: "#b8343c", inner: "#202024", pants: "#4a5a6a", shoes: "#f0f0f0", face: true };
const ENEMY: Look = { skin: "#7a5a48", hair: "#0c0c10", hairStyle: "long", shirt: "#16161c", inner: "#0c0c10", pants: "#121218", shoes: "#0c0c10", face: false };
const OLD_M: Look = { skin: "#c08a64", hair: "#ece8e0", hairStyle: "short", shirt: "#efe6d2", inner: "#c9a46a", pants: "#efe6d2", shoes: "#6a4a2a", face: true };
const OLD_W: Look = { skin: "#c99572", hair: "#e6e2da", hairStyle: "bun", shirt: "#8a2a3a", inner: "#d8a84a", pants: "#8a2a3a", shoes: "#6a4a2a", face: true };
const PHONERS: Look[] = [
  { skin: "#c48e6a", hair: "#1a1410", hairStyle: "short", shirt: "#3a5a7a", inner: "#ddd", pants: "#2a2a30", shoes: "#eee", face: true },
  { skin: "#d6a07e", hair: "#2a1a12", hairStyle: "long", shirt: "#8a5aa0", inner: "#eee", pants: "#3a3a48", shoes: "#ddd", face: true },
  { skin: "#b07850", hair: "#120e0c", hairStyle: "curly", shirt: "#4a7a4a", inner: "#ddd", pants: "#2a2a30", shoes: "#c33", face: true },
  { skin: "#cf9a76", hair: "#2a1c14", hairStyle: "ponytail", shirt: "#c06a3a", inner: "#eee", pants: "#2c3e5a", shoes: "#eee", face: true },
  { skin: "#be8660", hair: "#141010", hairStyle: "short", shirt: "#6a6a72", inner: "#ddd", pants: "#202028", shoes: "#eee", face: true },
];

// ------------------------------------------------------------------------------------ places
const TABLE = V(0, 0, 0);
const STAIR = { x: -1.0, zTop: -23.4, n: 6, rise: 0.18, run: 0.4 };   // descends toward +z
const stairY = (z: number) => {
  const i = Math.floor((z - STAIR.zTop) / STAIR.run);
  if (z < STAIR.zTop) return STAIR.n * STAIR.rise;
  if (i >= STAIR.n) return 0;
  return (STAIR.n - i) * STAIR.rise;
};
const BENCH = V(2.75, 0.16, -16);

// ------------------------------------------------------------------------------------ actors
type Actor = { key: string; look: Look; pose: Pose; pos: [number, number, number]; yaw: number; s: number; pitch?: number;
  handR?: React.ReactNode; handL?: React.ReactNode; fade?: number };

const Phone: React.FC<{ glow?: number }> = ({ glow = 1 }) => (
  <group rotation={[0.3, 0, 0]}>
    <mesh scale={[0.07, 0.13, 0.012]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshBasicMaterial color="#1a1a20" />
    </mesh>
    <mesh position={[0, 0, 0.007]} scale={[0.06, 0.115, 1]}>
      <planeGeometry args={[1, 1]} />
      <meshBasicMaterial color={new THREE.Color("#9fd0ff").multiplyScalar(0.7 + glow * 0.5)} />
    </mesh>
    <pointLight position={[0, 0.05, 0.25]} intensity={0.5 * glow} distance={0.9} color="#8fc4ff" />
  </group>
);
const Thread: React.FC = () => (
  <mesh position={[0, 0.06, 0]} rotation={[Math.PI / 2, 0, 0]}>
    <torusGeometry args={[0.045, 0.009, 6, 16]} />
    <meshBasicMaterial color="#d81e2e" />
  </mesh>
);

const holdPhone = (p: Pose) => { p.armR = [-0.7, -0.15]; p.elbowR = -1.25; p.headPitch = 0.45; p.lookY = -0.8; };
const point = (p: Pose) => { p.armR = [-1.35, -0.1]; p.elbowR = -0.1; };
const masked = (p: Pose, k: number) => { p.mask = k; if (k > 0.5) { p.armL = [-1.25, 0.25]; p.elbowL = -1.45; } };

function actorsAt(t: number): Actor[] {
  const out: Actor[] = [];
  // ---------------- 0 – 9.92: the street party
  if (t < 10.0) {
    const her = restPose();
    her.smile = 0.85; her.blush = 0.5;
    let herYaw = 0, herPos: [number, number, number] = [0, 0, -0.75];
    if (t >= 2.7 && t < 5.15) { herYaw = lerp(0, Math.PI, seg(t, 2.75, 3.1)); her.armR = [-0.5, -0.2]; her.elbowR = -1.2; }
    if (t >= 5.15 && t < 7.66) { herYaw = Math.PI; her.headPitch = 0.3; }
    if (t >= 7.66) {   // on the crate, crying; they laugh
      her.sit = 1; herPos = [0, 0, -1.0]; herYaw = 0;
      her.smile = -0.6; her.brow = 1; her.eyes = 0.35; her.headPitch = 0.25; her.lookY = 0.6;
      her.tear = clamp((t - 7.9) / 1.2); her.tearAlpha = 0.9;
      her.armL = [-0.9, 0.3]; her.elbowL = -1.6; her.armR = [-0.9, -0.3]; her.elbowR = -1.6;
    }
    out.push({ key: "her", look: HER, pose: her, pos: herPos, yaw: herYaw, s: 0.8, handR: <Thread /> });
    // friends round the table, masks up
    const fr = (look: Look, key: string, pos: [number, number, number], yaw: number, i: number) => {
      const p = restPose();
      p.smile = 0.2;
      let mk = 1;
      if (t >= 2.9 && key === "f2") mk = 1 - seg(t, 2.9, 3.2);
      if (t >= 5.15) mk = 1 - seg(t, 5.3 + i * 0.35, 5.7 + i * 0.35);
      masked(p, mk);
      if (mk < 0.5) { p.smirk = 1; p.smile = 0.55; p.brow = -0.6; p.eyes = 0.75; }
      let ps = pos, yw = yaw;
      if (key === "f2" && t >= 2.9 && t < 7.66) {   // slips off to shake hands with the enemy
        const k = seg(t, 3.05, 3.9);
        ps = [lerp(pos[0], 1.75, k), 0, lerp(pos[2], 1.85, k)];
        p.walk = k > 0 && k < 1 ? 1 : 0; p.phase = t * 8;
        yw = lerp(yaw, Math.PI / 2, k);
        if (k >= 1) { p.armR = [-1.0, -0.05]; p.elbowR = -0.3 + 0.12 * Math.sin(t * 18); p.smirk = 1; p.smile = 0.6; p.headYaw = 0.25; }
      }
      if (t >= 7.66) {   // laughing at her, pointing, filming
        p.mask = 0; p.happyEyes = true; p.eyes = Math.sin(t * 9 + i) > -0.3 ? 0 : 1; p.smile = 1; p.smirk = 0.5;
        p.headPitch = 0.25 + 0.08 * Math.sin(t * 14 + i);
        if (key === "f1") holdPhone(p); else point(p);
        if (key === "f1") { p.headPitch = 0.2; p.lookY = -0.2; }
      }
      out.push({ key, look, pose: p, pos: ps, yaw: yw, s: key === "f1" ? 0.8 : 0.85,
        handR: key === "f1" && t >= 7.66 ? <Phone /> : undefined });
    };
    fr(F1, "f1", [-0.85, 0, 0.55], Math.PI * 0.82, 0);
    fr(F2, "f2", [0.85, 0, 0.55], -Math.PI * 0.82, 1);
    fr(F3, "f3", [0.0, 0, 1.15], Math.PI, 2);
    if (t >= 2.7 && t < 7.66) {
      const e = restPose();
      e.armR = [-1.0, -0.05]; e.elbowR = -0.3 + 0.12 * Math.sin(t * 18 + 0.5);
      out.push({ key: "enemy", look: ENEMY, pose: e, pos: [2.4, 0, 2.0], yaw: -Math.PI / 2, s: 0.9 });
    }
    return out;
  }
  // ---------------- 10 – 12.4: alone down the lane
  if (t < 12.4) {
    const p = restPose();
    p.walk = 1; p.phase = t * 6.5; p.smile = -0.3; p.brow = 0.8; p.eyes = 0.6; p.headPitch = 0.3; p.armSwing = 0.4;
    out.push({ key: "her", look: HER, pose: p, pos: [0.3, 0, lerp(-2.0, -5.2, (t - 10) / 2.4)], yaw: Math.PI, s: 0.8, handR: <Thread /> });
    return out;
  }
  // ---------------- 12.4 – 15.1: everyone lost in their phones
  if (t < 15.1) {
    const p = restPose();
    p.walk = 1; p.phase = t * 6; p.smile = -0.2; p.brow = 0.7; p.armSwing = 0.4;
    const k = (t - 12.4) / 2.7;
    p.headYaw = 0.6 * Math.sin(k * Math.PI * 2);   // she looks from one to the next
    out.push({ key: "her", look: HER, pose: p, pos: [0.2, 0, lerp(-8.6, -11.2, k)], yaw: Math.PI, s: 0.8, handR: <Thread /> });
    const spots: [number, number, number][] = [[-1.3, -9.2, 0.6], [1.5, -9.8, -2.2], [-1.0, -11.0, 2.4], [1.2, -11.6, -0.9], [-1.6, -12.6, 1.4]];
    spots.forEach(([x, z, yaw], i) => {
      const q = restPose();
      holdPhone(q);
      q.smile = 0; q.eyes = 0.8;
      out.push({ key: "ph" + i, look: PHONERS[i], pose: q, pos: [x, 0, z], yaw, s: i % 2 ? 0.8 : 0.85, handR: <Phone /> });
    });
    return out;
  }
  // ---------------- 15.1 – 19.8: the old couple (sepia) who'd give their life for their own, fading away
  if (t < 19.8) {
    const fade = 1 - seg(t, 17.9, 19.2);
    const m = restPose(), w = restPose();
    m.sit = 1; w.sit = 1;
    m.smile = 0.7; w.smile = 0.8; w.blush = 0.5;
    m.headYaw = -0.5; m.headRoll = -0.15;
    w.headYaw = 0.35; w.eyes = 0; w.happyEyes = true;
    m.armL = [-0.6, 0.6]; m.elbowL = -1.2;   // his arm round her shoulders
    w.armR = [-0.5, -0.3]; w.elbowR = -0.8;
    if (fade > 0.01) {
      out.push({ key: "oldm", look: OLD_M, pose: m, pos: [BENCH.x - 0.28, BENCH.y, BENCH.z], yaw: -Math.PI / 2, s: 0.82 * (0.4 + 0.6 * fade), fade });
      out.push({ key: "oldw", look: OLD_W, pose: w, pos: [BENCH.x - 0.28, BENCH.y, BENCH.z - 0.55], yaw: -Math.PI / 2, s: 0.78 * (0.4 + 0.6 * fade), fade });
    }
    if (t > 17.55) {   // she arrives and finds the bench empty
      const p = restPose();
      const k = seg(t, 17.55, 18.6);
      p.walk = k < 1 ? 1 : 0; p.phase = t * 6.5; p.brow = 0.7; p.smile = -0.2; p.headYaw = 0.9;
      out.push({ key: "her", look: HER, pose: p, pos: [0.9, 0, lerp(-13.6, -15.6, k)], yaw: Math.PI, s: 0.8, handR: <Thread /> });
    }
    return out;
  }
  // ---------------- 19.8 – 29.1 and replay 29.1 – 33.9: the stairs
  if (t < 33.9) {
    const replay = t >= 29.1;
    const tt = replay ? lerp(20.6, 22.9, clamp((t - 29.4) / 3.6)) : t;   // slow-motion replay of the fall
    const her = restPose();
    let pos: [number, number, number];
    let pitch = 0;
    const fallK = clamp((tt - 21.25) / 0.85);
    if (tt < 21.25) {   // coming down the steps, smiling at her phone
      const z = lerp(STAIR.zTop - 0.6, STAIR.zTop + 0.55, clamp((tt - 19.8) / 1.45));
      pos = [STAIR.x, stairY(z), z];
      her.walk = 0.8; her.phase = tt * 6; holdPhone(her); her.smile = 0.6; her.headPitch = 0.35;
    } else if (tt < 22.1) {   // pushed: she pitches forward down the stairs
      const k = Easing.in(Easing.quad)(fallK);
      const z = lerp(STAIR.zTop + 0.55, STAIR.zTop + STAIR.n * STAIR.run + 0.6, k);
      pos = [STAIR.x, lerp(stairY(STAIR.zTop + 0.55), 0, k), z];
      pitch = 1.5 * smooth(fallK * 1.5);
      her.armL = [-2.4 * k, 0.5]; her.armR = [-2.2 * k, -0.5]; her.elbowL = -0.2; her.elbowR = -0.2;
      her.eyes = 1.3; her.mouthO = 1; her.brow = -0.5; her.smile = 0;
    } else {
      // on the ground, then sits up on the bottom step
      const up = seg(tt, 22.4, 23.3);
      const zb = STAIR.zTop + STAIR.n * STAIR.run;
      pos = [STAIR.x, lerp(0, -0.18, up), lerp(zb + 0.6, zb - 0.05, up)];
      pitch = lerp(1.5, 0, up);
      her.sit = up > 0.5 ? 1 : 0;
      her.armL = [-0.6, 0.4]; her.armR = [-0.6, -0.4];
      her.headYaw = 0; her.headPitch = lerp(0, -0.35, seg(tt, 22.3, 22.9));   // looks back up the stairs
      her.eyes = 1.15; her.brow = 0.9; her.smile = -0.5; her.mouthO = 0;
      if (t >= 23.85 && !replay) {   // she knows… and still takes the hand
        her.headPitch = lerp(-0.35, 0.05, seg(t, 23.9, 24.5));
        her.tear = clamp((t - 24.2) / 1.2); her.tearAlpha = 0.9;
        her.eyes = lerp(1, 0.55, seg(t, 24.2, 25.0));
        her.smile = lerp(-0.5, 0.35, seg(t, 24.8, 25.6));
        her.brow = 0.8;
        if (t > 25.8) { her.armR = [-1.25, -0.25]; her.elbowR = -0.2; }
        const rise = seg(t, 27.4, 28.4);
        if (rise > 0) { her.sit = rise > 0.5 ? 0 : 1; pos = [STAIR.x, lerp(-0.18, 0, rise), lerp(zb - 0.05, zb + 0.35, rise)]; }
      }
    }
    // she turns to face the stairs (and F1) once she is on the ground
    const yaw = tt >= 22.1 ? lerp(0, Math.PI, seg(tt, 22.2, 22.8)) : 0;
    out.push({ key: "her", look: HER, pose: her, pos, yaw, s: 0.8, pitch, handR: tt < 21.25 ? <Phone /> : <Thread /> });
    // F1: behind her on the stairs, mask up, the push, then the mask comes down
    const f = restPose();
    let fz = lerp(STAIR.zTop - 1.2, STAIR.zTop - 0.1, clamp((tt - 19.8) / 1.45));
    f.walk = tt < 21.1 ? 0.8 : 0; f.phase = tt * 6 + 1;
    masked(f, 1);
    if (tt >= 21.05 && tt < 21.5) { f.armR = [-1.5, -0.1]; f.elbowR = -0.1 * (1 - seg(tt, 21.05, 21.25)); }   // the push
    if (tt >= 22.3) {
      const k = seg(tt, 22.5, 23.1);
      masked(f, 1 - k);
      if (k > 0.5) { f.smirk = 1; f.smile = 0.55; f.brow = -0.6; f.eyes = 0.7; f.headPitch = 0.35; }
    }
    if (t >= 23.85 && !replay) {   // comes down and offers a hand, all concern
      const k = seg(t, 24.0, 25.4);
      fz = lerp(STAIR.zTop - 0.1, STAIR.zTop + STAIR.n * STAIR.run - 0.55, k);
      f.walk = k > 0 && k < 1 ? 0.8 : 0; f.mask = 0; f.smirk = 0; f.smile = -0.1; f.brow = 0.6; f.eyes = 1; f.headPitch = 0.4;
      if (t > 25.4) { f.armR = [-1.2, -0.1]; f.elbowR = -0.2; }
      if (t > 27.4) f.headPitch = lerp(0.4, 0.05, seg(t, 27.4, 28.4));
    }
    const fx = t >= 23.85 && !replay ? lerp(STAIR.x + 0.15, STAIR.x - 0.4, seg(t, 24.0, 25.4)) : STAIR.x + 0.15;
    out.push({ key: "f1", look: F1, pose: f, pos: [fx, stairY(fz), fz], yaw: 0, s: 0.8, handR: <Thread /> });
    return out;
  }
  // ---------------- 33.9 – end: hand in hand down the lane; the mask hangs behind F1's back
  const k = (t - 33.9) / 4.9;
  const her = restPose(), f = restPose();
  her.walk = 1; her.phase = t * 6.2; f.walk = 1; f.phase = t * 6.2 + 3.1;
  her.armR = [0.05, -0.25]; her.elbowR = -0.1; her.armSwing = 0.3; f.armSwing = 0.3;
  f.armL = [0.05, 0.25]; f.elbowL = -0.1;
  f.armR = [0.7, -0.15]; f.elbowR = -0.6;   // mask held behind her back
  f.smile = 0.5; her.smile = 0.25;
  her.headYaw = t > 36.2 ? lerp(0, 2.2, seg(t, 36.2, 36.9)) : 0;   // glances back at us
  her.brow = 0.6; her.eyes = t > 37.6 ? 0.1 : 0.75; her.happyEyes = t > 37.6;
  her.tear = t > 36.6 ? clamp((t - 36.6) / 1.4) : -1; her.tearAlpha = 0.85;
  const z = lerp(-26.5, -31.5, k);
  out.push({ key: "her", look: HER, pose: her, pos: [-0.3, 0, z], yaw: Math.PI, s: 0.8, handR: <Thread /> });
  out.push({ key: "f1", look: F1, pose: f, pos: [0.4, 0, z - 0.05], yaw: Math.PI, s: 0.8,
    handR: <group position={[0, 0.02, 0.05]} rotation={[2.4, 0, 0]}><MaskOnStick /></group>, handL: <Thread /> });
  return out;
}

let maskTex: THREE.Texture | null = null;
const MaskOnStick: React.FC = () => {
  if (!maskTex) {
    const c = document.createElement("canvas");
    c.width = c.height = 256;
    const x = c.getContext("2d")!;
    x.fillStyle = "#ffe9c8"; x.beginPath(); x.arc(128, 128, 124, 0, Math.PI * 2); x.fill();
    x.fillStyle = "#1a1010";
    x.beginPath(); x.ellipse(84, 104, 16, 24, 0, 0, Math.PI * 2); x.fill();
    x.beginPath(); x.ellipse(172, 104, 16, 24, 0, 0, Math.PI * 2); x.fill();
    x.strokeStyle = "#c2263a"; x.lineWidth = 14; x.lineCap = "round";
    x.beginPath(); x.arc(128, 140, 62, 0.15 * Math.PI, 0.85 * Math.PI); x.stroke();
    maskTex = new THREE.CanvasTexture(c);
    maskTex.colorSpace = THREE.SRGBColorSpace;
  }
  return (
    <group>
      <mesh position={[0, -0.3, 0]}>
        <circleGeometry args={[0.17, 28]} />
        <meshBasicMaterial map={maskTex} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, -0.1, -0.01]}>
        <cylinderGeometry args={[0.008, 0.008, 0.28, 6]} />
        <meshToonMaterial color="#8a6a3a" />
      </mesh>
    </group>
  );
};

// ------------------------------------------------------------------------------------ set pieces
const Party: React.FC<{ t: number }> = ({ t }) => {
  const bulbs = useMemo(() => Array.from({ length: 22 }, (_, i) => i / 21), []);
  return (
    <group>
      {/* table, cloth and cake */}
      <Toon geom={G.box} color="#f0e6dc" position={[TABLE.x, 0.72, TABLE.z]} scale={[1.1, 0.06, 0.6]} outline={0.004} />
      {[[-0.5, -0.25], [0.5, -0.25], [-0.5, 0.25], [0.5, 0.25]].map(([x, z], i) => (
        <mesh key={i} position={[TABLE.x + x, 0.36, TABLE.z + z]}>
          <cylinderGeometry args={[0.025, 0.025, 0.72, 8]} />
          <meshToonMaterial color="#5a4030" />
        </mesh>
      ))}
      <Toon geom={G.cyl} color="#f6c8d4" position={[TABLE.x, 0.84, TABLE.z]} scale={[0.17, 0.18, 0.17]} outline={0.01} />
      <Toon geom={G.cyl} color="#ffffff" position={[TABLE.x, 0.94, TABLE.z]} scale={[0.175, 0.02, 0.175]} outline={0} />
      {[-0.06, 0, 0.06].map((x, i) => (
        <group key={i} position={[TABLE.x + x, 0.98, TABLE.z + (i - 1) * 0.03]}>
          <mesh position={[0, 0.04, 0]}>
            <cylinderGeometry args={[0.006, 0.006, 0.08, 6]} />
            <meshBasicMaterial color="#6fb6ff" />
          </mesh>
          <mesh position={[0, 0.095, 0]} scale={[0.012, 0.022, 0.012]}>
            <sphereGeometry args={[1, 8, 6]} />
            <meshBasicMaterial color="#ffd27a" />
          </mesh>
        </group>
      ))}
      {/* the crate she ends up on */}
      <Toon geom={G.box} color="#8a6a44" position={[0, 0.2, -1.05]} scale={[0.5, 0.4, 0.4]} outline={0.005} />
      {/* fairy lights between two poles */}
      {[-2.0, 2.0].map((x) => (
        <mesh key={x} position={[x, 1.4, -0.2]}>
          <cylinderGeometry args={[0.03, 0.03, 2.8, 8]} />
          <meshToonMaterial color="#3a3a40" />
        </mesh>
      ))}
      {bulbs.map((u, i) => {
        const x = lerp(-2.0, 2.0, u), y = 2.75 - Math.sin(u * Math.PI) * 0.45;
        const on = 0.75 + 0.25 * Math.sin(t * 5 + i * 1.7);
        return (
          <mesh key={i} position={[x, y, -0.2]} scale={0.035}>
            <sphereGeometry args={[1, 8, 6]} />
            <meshBasicMaterial color={new THREE.Color(["#ffcf6a", "#ff7a8a", "#8ad0ff", "#a8ff9a"][i % 4]).multiplyScalar(on)} />
          </mesh>
        );
      })}
      <pointLight position={[0, 2.4, -0.2]} intensity={2.2} distance={6} color="#ffc890" />
      <pointLight position={[0, 1.2, 0.2]} intensity={0.7} distance={2.5} color="#ffb070" />
    </group>
  );
};

const Stairs: React.FC = () => (
  <group>
    {Array.from({ length: STAIR.n }).map((_, i) => {
      const h = (STAIR.n - i) * STAIR.rise;
      return (
        <Toon key={i} geom={G.box} color={i % 2 ? "#8c8478" : "#968e82"} position={[STAIR.x, h / 2, STAIR.zTop + (i + 0.5) * STAIR.run]}
          scale={[1.6, h, STAIR.run]} outline={0.002} />
      );
    })}
    <Toon geom={G.box} color="#8c8478" position={[STAIR.x, (STAIR.n * STAIR.rise) / 2, STAIR.zTop - 1.2]} scale={[1.6, STAIR.n * STAIR.rise, 2.4]} outline={0.002} />
    {[-1, 1].map((s) => (
      <group key={s}>
        <mesh position={[STAIR.x + s * 0.82, 1.0, STAIR.zTop + 1.2]} rotation={[-Math.atan2(STAIR.rise, STAIR.run), 0, 0]}>
          <boxGeometry args={[0.04, 0.04, 2.7]} />
          <meshToonMaterial color="#2a2a30" />
        </mesh>
        {[0, 1, 2, 3].map((j) => (
          <mesh key={j} position={[STAIR.x + s * 0.82, stairY(STAIR.zTop + j * 0.8 + 0.2) + 0.45, STAIR.zTop + j * 0.8 + 0.2]}>
            <cylinderGeometry args={[0.015, 0.015, 0.9, 6]} />
            <meshToonMaterial color="#2a2a30" />
          </mesh>
        ))}
      </group>
    ))}
  </group>
);

const Bench: React.FC = () => (
  <group position={[BENCH.x, BENCH.y, BENCH.z - 0.28]}>
    <Toon geom={G.box} color="#7a5634" position={[0, 0.42, 0]} scale={[0.5, 0.06, 1.5]} outline={0.004} />
    <Toon geom={G.box} color="#7a5634" position={[0.22, 0.75, 0]} scale={[0.06, 0.45, 1.5]} outline={0.004} />
    {[-0.6, 0.6].map((z) => (
      <mesh key={z} position={[0, 0.2, z]}>
        <boxGeometry args={[0.45, 0.4, 0.05]} />
        <meshToonMaterial color="#3a3a40" />
      </mesh>
    ))}
  </group>
);

const heartHalf = (side: 1 | -1) => {
  const s = new THREE.Shape();
  s.moveTo(0, -0.3);
  if (side < 0) { s.bezierCurveTo(-0.6, 0.1, -0.35, 0.55, 0, 0.25); s.lineTo(0.05, 0.1); s.lineTo(-0.03, -0.02); s.lineTo(0.03, -0.15); s.lineTo(0, -0.3); }
  else { s.bezierCurveTo(0.6, 0.1, 0.35, 0.55, 0, 0.25); s.lineTo(0.05, 0.1); s.lineTo(-0.03, -0.02); s.lineTo(0.03, -0.15); s.lineTo(0, -0.3); }
  return new THREE.ExtrudeGeometry(s, { depth: 0.08, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 });
};
const HL = heartHalf(-1), HR = heartHalf(1);

// "मुश्किल वफ़ा": a heart above her splits in two
const BrokenHeart: React.FC<{ t: number; at: THREE.Vector3 }> = ({ t, at }) => {
  if (t < 10.2 || t > 12.4) return null;
  const pop = smooth((t - 10.2) / 0.3);
  const k = seg(t, 11.0, 11.6);
  return (
    <group position={[at.x, at.y + 0.2 * k, at.z]} scale={0.5 * pop} rotation={[0, Math.PI, Math.PI]}>
      <mesh geometry={HL} position={[-0.12 * k, -0.2 * k, 0]} rotation={[0, 0, 0.35 * k]}>
        <meshBasicMaterial color="#e8304a" transparent opacity={1 - 0.4 * k} />
      </mesh>
      <mesh geometry={HR} position={[0.12 * k, -0.2 * k, 0]} rotation={[0, 0, -0.35 * k]}>
        <meshBasicMaterial color="#e8304a" transparent opacity={1 - 0.4 * k} />
      </mesh>
      <pointLight intensity={0.8} distance={2} color="#ff4a5a" />
    </group>
  );
};

// the old couple turning to dust
const Dust: React.FC<{ t: number }> = ({ t }) => {
  const motes = useMemo(() => {
    const r = rng(5);
    return Array.from({ length: 120 }, () => ({ x: (r() - 0.5) * 0.7, y: 0.3 + r() * 1.2, z: (r() - 0.5) * 1.0, d: r() * 0.8, sp: 0.4 + r() * 0.8 }));
  }, []);
  if (t < 17.8 || t > 19.8) return null;
  return (
    <group position={[BENCH.x - 0.28, BENCH.y, BENCH.z - 0.28]}>
      {motes.map((m, i) => {
        const k = clamp((t - 17.8 - m.d) / 1.1);
        if (k <= 0 || k >= 1) return null;
        return (
          <mesh key={i} position={[m.x - k * 0.6, m.y + k * m.sp, m.z + Math.sin(k * 6 + i) * 0.1]} scale={0.012 * (1 - k * 0.5)}>
            <sphereGeometry args={[1, 6, 4]} />
            <meshBasicMaterial color="#ffe0a8" transparent opacity={1 - k} />
          </mesh>
        );
      })}
    </group>
  );
};

// insert: two hands meeting, both wearing the same red thread
const HandsInsert: React.FC<{ t: number }> = ({ t }) => {
  if (t < 25.8 || t >= 27.3) return null;
  const k = Easing.out(Easing.cubic)(clamp((t - 25.9) / 0.8));
  const arm = (side: 1 | -1, col: string, skin: string) => {
    const x = side * lerp(0.42, 0.075, k);
    return (
      <group position={[x, 0, 0]} rotation={[0, 0, side * Math.PI / 2]}>
        <Toon geom={G.capsule} color={col} position={[0, side * 0.35, 0]} scale={[0.055, 0.17, 0.055]} />
        <Toon geom={G.sphere} color={skin} position={[0, side * -0.02, 0]} scale={[0.06, 0.07, 0.05]} outline={0.01} />
        <mesh position={[0, side * 0.1, 0]}>
          <torusGeometry args={[0.052, 0.01, 8, 20]} />
          <meshBasicMaterial color="#d81e2e" />
        </mesh>
      </group>
    );
  };
  return (
    <group position={[0, 40, 40]}>
      {arm(-1, F1.shirt, F1.skin)}
      {arm(1, HER.shirt, HER.skin)}
      <pointLight position={[0, 0.4, 0.6]} intensity={2} distance={3} color="#ffd8b0" />
      <mesh position={[0, 0, -1.2]}>
        <planeGeometry args={[6, 6]} />
        <meshBasicMaterial color="#1a1424" />
      </mesh>
      {Array.from({ length: 14 }).map((_, i) => (
        <mesh key={i} position={[Math.sin(i * 2.3) * 1.2, Math.cos(i * 1.7) * 0.9, -1.1]} scale={0.06 + (i % 3) * 0.03}>
          <circleGeometry args={[1, 16]} />
          <meshBasicMaterial color={["#ffb860", "#ff7080", "#80b0ff"][i % 3]} transparent opacity={0.35} />
        </mesh>
      ))}
    </group>
  );
};

// ------------------------------------------------------------------------------------ camera
type Cam = { pos: [number, number, number]; target: [number, number, number]; fov: number; roll?: number };
function camAt(t: number): Cam {
  if (t < 2.7) {   // crane down behind her: three smiling masks look back at her
    const k = Easing.inOut(Easing.cubic)(t / 2.7);
    return { pos: lerp3([0.9, 3.0, -3.6], [0.35, 1.5, -2.1], k), target: lerp3([0, 1.0, 0.6], [0, 1.35, 0.7], k), fov: lerp(46, 40, k) };
  }
  if (t < 5.15) {  // her back is turned; one of them shakes hands with the enemy
    const k = (t - 2.7) / 2.45;
    return { pos: lerp3([3.3, 1.45, 4.4], [3.1, 1.4, 4.0], k), target: lerp3([1.2, 1.2, 0.8], [1.4, 1.25, 1.1], k), fov: 40 };
  }
  if (t < 7.66) {  // masks come down: dutch close-up pan across the smirks
    const k = Easing.inOut(Easing.quad)((t - 5.15) / 2.51);
    return { pos: lerp3([-0.5, 1.5, -0.35], [0.5, 1.5, -0.35], k), target: lerp3([-0.85, 1.42, 0.55], [0.85, 1.45, 0.55], k), fov: 34, roll: lerp(0.16, -0.16, k) };
  }
  if (t < 10.0) {  // low, behind her on the crate: they tower over her, laughing
    const k = (t - 7.66) / 2.34;
    return { pos: [lerp(0.25, 0.15, k), 0.72, lerp(-1.75, -1.65, k)], target: [0, 1.55, 0.6], fov: lerp(44, 40, k) };
  }
  if (t < 12.4) {  // high wide: alone down the lane, a heart breaks above her
    const k = (t - 10.0) / 2.4;
    return { pos: lerp3([3.0, 7.0, 0.5], [2.4, 6.0, -1.2], k), target: lerp3([0.3, 0.5, -3.0], [0.3, 0.6, -4.8], k), fov: 40 };
  }
  if (t < 15.1) {  // orbit round her among the phone faces
    const k = (t - 12.4) / 2.7;
    const her = V(0.2, 1.3, lerp(-8.6, -11.2, k));
    const a = lerp(-0.9, 0.9, k);
    return { pos: [her.x + 2.6 * Math.sin(a), 1.55, her.z - 2.6 * Math.cos(a)], target: [her.x, 1.25, her.z], fov: 46 };
  }
  if (t < 19.8) {  // the bench: an old couple (sepia), then nothing
    const k = (t - 15.1) / 4.7;
    return { pos: lerp3([1.0, 1.2, -14.6], [0.2, 1.7, -13.4], k), target: lerp3([2.75, 0.95, -16.3], [2.4, 0.9, -16.0], k), fov: lerp(34, 42, k) };
  }
  if (t < 21.25) { // low at the foot of the stairs: she comes down, someone behind her
    const k = (t - 19.8) / 1.45;
    return { pos: [lerp(0.4, 0.3, k), 0.55, -19.0], target: [STAIR.x, 1.5, STAIR.zTop - 0.2], fov: 42 };
  }
  if (t < 22.1) {  // the fall: dutch, from the side
    return { pos: [0.5, 0.55, -18.9], target: [STAIR.x, 0.75, -21.4], fov: 50, roll: 0.2 };
  }
  if (t < 23.85) { // her point of view: up the stairs at the one who pushed
    const k = (t - 22.1) / 1.75;
    return { pos: [STAIR.x, 0.75, lerp(-20.0, -20.3, k)], target: [STAIR.x + 0.15, 1.95, STAIR.zTop - 0.1], fov: lerp(40, 32, k) };
  }
  if (t < 25.8) {  // close on her face: she knows
    return { pos: [STAIR.x + 1.5, 1.05, -22.5], target: [STAIR.x, 0.9, -21.05], fov: 30 };
  }
  if (t < 27.3) {  // insert: the hands
    return { pos: [0, 40.15, 41.2], target: [0, 40, 40], fov: 34 };
  }
  if (t < 29.1) {  // two-shot: she rises with her
    return { pos: [1.9, 1.2, -19.4], target: [STAIR.x, 1.0, -20.9], fov: 40 };
  }
  if (t < 33.9) {  // the replay, straight down from above
    const k = (t - 29.1) / 4.8;
    return { pos: [STAIR.x + 0.3, lerp(6.5, 5.5, k), -21.6], target: [STAIR.x, 0.4, -21.8], fov: 44, roll: lerp(0, 0.2, k) };
  }
  // follow them from behind, then crane up as she looks back
  const k = Easing.inOut(Easing.cubic)(clamp((t - 33.9) / 4.9));
  const z = lerp(-26.5, -31.5, (t - 33.9) / 4.9);
  return { pos: lerp3([0.05, 1.3, z + 2.6], [0.6, 3.6, z + 4.2], k), target: [0.05, 1.1, z - 0.4], fov: lerp(38, 44, k) };
}

const CameraRig: React.FC<{ t: number }> = ({ t }) => {
  const { camera } = useThree();
  const c = camAt(t);
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(...c.pos);
  cam.up.set(Math.sin(c.roll ?? 0), Math.cos(c.roll ?? 0), 0);
  cam.fov = c.fov;
  cam.near = 0.03;
  cam.far = 200;
  cam.lookAt(V(...c.target));
  cam.updateProjectionMatrix();
  return null;
};

// ------------------------------------------------------------------------------------ scene
const Scene: React.FC<{ t: number }> = ({ t }) => {
  const day = t >= 15.1 && t < 19.8 ? 1 - seg(t, 18.6, 19.6) : 0;
  const skyN = useMemo(() => skyMat(), []);
  const skyD = useMemo(() => skyMat("#6aa0e0", "#fff0d0", 0), []);
  const actors = actorsAt(t);
  const herA = actors.find((a) => a.key === "her");
  const red = (t >= 5.15 && t < 7.66) || (t >= 22.1 && t < 23.85);
  return (
    <>
      <CameraRig t={t} />
      <mesh material={day > 0.5 ? skyD : skyN} scale={90}>
        <sphereGeometry args={[1, 32, 16]} />
      </mesh>
      <fog attach="fog" args={[day > 0.5 ? "#e8dcc0" : "#2a2e52", 12, 48]} />
      <ambientLight intensity={lerp(0.6, 1.4, day)} />
      <hemisphereLight args={["#6a78b8", "#2a2228", 0.55]} />
      <directionalLight position={day > 0.5 ? [6, 10, 4] : [-6, 9, -10]} intensity={lerp(0.5, 2.2, day)} color={day > 0.5 ? "#fff0d0" : "#9fb4ff"} castShadow
        shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-10} shadow-camera-right={10}
        shadow-camera-top={10} shadow-camera-bottom={-10} shadow-bias={-0.0008} shadow-normalBias={0.03} />
      {red ? <pointLight position={t < 10 ? [0, 1.6, -0.2] : [STAIR.x, 2.6, STAIR.zTop - 1.0]} intensity={2.6} distance={4} color="#ff2a3a" /> : null}
      <Street />
      <Buildings />
      <Lamp base={[2.5, 0.16, 2.2]} dir={-1} target={[1.4, 0, 1.6]} intensity={10} />
      <Lamp base={[-2.5, 0.16, -10]} dir={1} target={[-0.5, 0, -10]} intensity={14} />
      <Lamp base={[2.5, 0.16, -17.5]} dir={-1} target={[2.2, 0, -16]} intensity={14} />
      <Lamp base={[-2.4, 0.16, -20.6]} dir={1} target={[STAIR.x, 0.5, -21.6]} intensity={18} shadow />
      <Lamp base={[2.5, 0.16, -29]} dir={-1} target={[0.6, 0, -29]} intensity={14} />
      {[[-3.4, 0.16, -5], [3.4, 0.16, -3], [3.4, 0.16, -13.5], [-3.4, 0.16, -15], [3.4, 0.16, -24], [-3.4, 0.16, -27]].map((p, i) => (
        <Tree key={i} pos={p as [number, number, number]} s={0.9 + (i % 2) * 0.15} />
      ))}
      <Party t={t} />
      <Stairs />
      <Bench />
      {actors.map((a) => (
        <group key={a.key} position={a.pos} rotation={[0, a.yaw, 0]}>
          <group rotation={[a.pitch ?? 0, 0, 0]} scale={a.s}>
            <Person look={a.look} pose={a.pose} handR={a.handR} handL={a.handL} />
          </group>
        </group>
      ))}
      {herA ? <BrokenHeart t={t} at={V(herA.pos[0], 1.95, herA.pos[2])} /> : null}
      <Dust t={t} />
      <HandsInsert t={t} />
    </>
  );
};

export const Chehre3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const line = LINES.find(([a, b]) => t >= a && t < b);
  let dip = 0;
  for (const c of CUTS) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.1);
  const flash = Math.max(Math.max(0, 1 - Math.abs(t - 21.25) / 0.1), Math.max(0, 1 - Math.abs(t - 29.1) / 0.12));
  const fade = Math.min(clamp(t / 0.35), clamp((END - t) / 0.85));
  const sepia = t >= 15.1 && t < 19.8 ? 1 - seg(t, 18.6, 19.6) : 0;
  const replay = t >= 29.1 && t < 33.9 ? 1 : 0;
  const filter = replay ? "sepia(0.9) hue-rotate(-38deg) saturate(2.6) contrast(1.1)" : sepia > 0 ? `sepia(${0.85 * sepia}) contrast(1.05)` : "none";
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter }}>
        <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
          <Scene t={t} />
        </ThreeCanvas>
      </AbsoluteFill>
      {replay ? (
        <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, rgba(0,0,0,0.12) 0px, rgba(0,0,0,0.12) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 6px)" }} />
      ) : null}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 52%, rgba(0,0,0,${sepia > 0 ? 0.65 : 0.5}) 100%)` }} />
      {line ? (
        <div style={{ position: "absolute", top: 1290, left: 50, right: 50, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 62, lineHeight: 1.35, color: "#faf8f4", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill",
          textShadow: "0 4px 14px rgba(0,0,0,0.7)" }}>
          {line[2]}
        </div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash * 0.65 }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.45) }} />
    </AbsoluteFill>
  );
};
