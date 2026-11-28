import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { G, Look, Person, Pose, Toon, restPose } from "./Character";
import { rng, skyMat } from "./World";

// "सबको लगता है कि कौआ ने…" (ReelAudio-2110): the thirsty crow, the true version. He clears the path for others.
export const DURATION = 1231; // 41.0 s
const FPS = 30;
const END = DURATION / FPS;
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (x: number) => { const t = clamp(x); return t * t * (3 - 2 * t); };
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: number[], b: number[], t: number) => a.map((v, i) => lerp(v, b[i], t)) as [number, number, number];
const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

const SUBS: [number, number, string][] = [
  [0.0, 5.4, "सबको लगता है कि कौआ ने उस दिन अपनी प्यास बुझाने के लिए मटके में कंकड़ डाले थे।"],
  [5.86, 8.4, "कौआ प्यासा दर-दर भटक रहा था।"],
  [8.58, 12.08, "तो उसने देखा कि एक मटके के अंदर थोड़ा सा पानी भरा है।"],
  [12.08, 15.7, "उसने दिमाग लगाया और बाहर पड़े कंकड़ उठाने गया,"],
  [15.9, 18.7, "तो देखा उधर एक पानी का तालाब भरा है।"],
  [18.88, 21.1, "कौआ तालाब के पास जा ही रहा था,"],
  [21.28, 24.3, "लेकिन कौआ ने देखा कि कंकड़ रास्ते में पड़े थे।"],
  [24.56, 27.4, "बाहर से निकलने वाले लोगों को वो कंकड़ चुभ रहे थे।"],
  [27.4, 31.4, "तो कौआ कंकड़ को बारी-बारी उठाके मटके में डालने लगा,"],
  [31.5, 34.7, "और रास्ते के सारे कंकड़ उठाके मटके में डाल दिए,"],
  [34.7, 36.5, "और अपनी प्यास बुझा ली।"],
  [36.88, 41.0, "कभी-कभी अपना ना सोचके दूसरों की भी मदद करके अच्छा लगता है।"],
];
const S = { heat: 5.86, pot: 8.58, idea: 12.08, pond: 15.9, go: 18.88, stones: 21.28, hurt: 24.56, pick: 27.4, clear: 31.5, drink: 34.7, end: 36.88 };

// ------------------------------------------------------------------ places
const POT = V(0, 0, -1.4);                // the matka under the tree
const POT_MOUTH = 0.5;                    // mouth height
const POND = V(4.6, 0, -2.6);
const TREE = V(-1.0, 0, -2.4);
const STONES = (() => { const r = rng(17); return Array.from({ length: 10 }, (_, i) => ({ x: -1.4 + i * 0.5 + (r() - 0.5) * 0.3, z: (r() - 0.5) * 0.7, s: 0.045 + r() * 0.03, rot: r() * 6 })); })();
const PICK_T = (i: number) => S.pick + 0.2 + i * 0.7;    // when each stone is picked up

// ------------------------------------------------------------------ the crow
type CrowPose = { flap: number; peck: number; beak: number; eyes: number; tilt: number; pant: number; happy: boolean };
const Crow: React.FC<{ p: CrowPose; t: number; stone?: boolean }> = ({ p, t, stone }) => {
  const wing = p.flap > 0 ? Math.sin(t * 22) * 0.95 * p.flap : 0.12;
  const pant = p.pant > 0 ? 0.25 * p.pant * Math.abs(Math.sin(t * 9)) : 0;
  return (
    <group>
      <Toon geom={G.sphere} color="#1c1e26" position={[0, 0.16, 0]} scale={[0.1, 0.1, 0.16]} outline={0.008} />
      <mesh position={[0, 0.2, 0.02]} scale={[0.095, 0.08, 0.13]}><sphereGeometry args={[1, 12, 10]} /><meshStandardMaterial color="#2a3448" metalness={0.5} roughness={0.35} transparent opacity={0.4} /></mesh>
      {/* tail */}
      <mesh position={[0, 0.17, -0.2]} rotation={[-0.4, 0, 0]} scale={[0.07, 0.012, 0.11]}><sphereGeometry args={[1, 10, 6]} /><meshToonMaterial color="#16181e" /></mesh>
      {/* grey nape (house crow) */}
      <Toon geom={G.sphere} color="#666a74" position={[0, 0.245, 0.075]} scale={[0.082, 0.078, 0.085]} outline={0.006} />
      {/* head */}
      <group position={[0, 0.27, 0.12]} rotation={[p.peck * 1.1, 0, p.tilt]}>
        <Toon geom={G.sphere} color="#1c1e26" scale={[0.075, 0.075, 0.075]} outline={0.008} />
        {/* beak: upper and lower */}
        <mesh position={[0, 0.0, 0.1]} rotation={[Math.PI / 2 - 0.1 - p.beak * 0.25 - pant, 0, 0]} scale={[0.026, 0.07, 0.022]}><coneGeometry args={[1, 1, 8]} /><meshToonMaterial color="#3a3a42" /></mesh>
        <mesh position={[0, -0.015, 0.09]} rotation={[Math.PI / 2 + 0.1 + p.beak * 0.35 + pant, 0, 0]} scale={[0.022, 0.06, 0.018]}><coneGeometry args={[1, 1, 8]} /><meshToonMaterial color="#2a2a32" /></mesh>
        {stone ? <mesh position={[0, -0.02, 0.15]} scale={0.03}><dodecahedronGeometry args={[1, 0]} /><meshToonMaterial color="#8a8680" /></mesh> : null}
        {/* big expressive eyes */}
        {[-1, 1].map((s) => (
          <group key={s} position={[s * 0.045, 0.02, 0.055]}>
            <mesh scale={[0.026, 0.028 * Math.max(0.1, p.eyes), 0.015]}><sphereGeometry args={[1, 12, 10]} /><meshBasicMaterial color="#ffffff" /></mesh>
            {p.eyes > 0.15 ? <mesh position={[0, 0, 0.012]} scale={[0.013, 0.016 * Math.min(1, p.eyes), 0.008]}><sphereGeometry args={[1, 10, 8]} /><meshBasicMaterial color="#0a0a0a" /></mesh>
              : <mesh position={[0, 0, 0.012]} rotation={[0, 0, p.happy ? 0 : Math.PI]} scale={[0.02, 0.013, 0.01]}><torusGeometry args={[1, 0.25, 6, 12, Math.PI]} /><meshBasicMaterial color="#0a0a0a" /></mesh>}
            {p.eyes > 0.15 ? <mesh position={[-0.005, 0.008, 0.02]} scale={0.005}><sphereGeometry args={[1, 6, 6]} /><meshBasicMaterial color="#ffffff" /></mesh> : null}
          </group>
        ))}
      </group>
      {/* wings */}
      {p.flap > 0 ? [-1, 1].map((s) => (
        <group key={s} position={[s * 0.08, 0.2, 0.0]} rotation={[0, 0, s * (0.15 + wing)]}>
          <mesh position={[s * 0.13, 0, -0.03]} scale={[0.15, 0.015, 0.1]}><sphereGeometry args={[1, 12, 6]} /><meshToonMaterial color="#20222a" /></mesh>
        </group>
      )) : [-1, 1].map((s) => (
        <mesh key={s} position={[s * 0.088, 0.19, -0.05]} rotation={[0.25, 0, 0]} scale={[0.028, 0.07, 0.17]}><sphereGeometry args={[1, 12, 8]} /><meshToonMaterial color="#20222a" /></mesh>
      ))}
      {/* legs */}
      {[-1, 1].map((s) => <mesh key={s} position={[s * 0.035, 0.03, 0.02]} scale={[0.008, 0.06, 0.008]}><cylinderGeometry args={[1, 1, 1, 4]} /><meshToonMaterial color="#2a2a2a" /></mesh>)}
    </group>
  );
};
const crowRest = (): CrowPose => ({ flap: 0, peck: 0, beak: 0, eyes: 1, tilt: 0, pant: 0, happy: false });

// where the crow is, and how
function crowAt(t: number): { pos: [number, number, number]; yaw: number; p: CrowPose; stone: boolean; s: number } {
  const p = crowRest();
  const rim: [number, number, number] = [POT.x + 0.12, POT_MOUTH + 0.02, POT.z + 0.05];
  if (t < S.heat) {   // storybook: the familiar crow dropping a stone into the pot
    const k = (t % 1.6) / 1.6;
    p.peck = k < 0.4 ? 0.9 : 0; p.beak = k < 0.35 ? 0 : 0.2;
    return { pos: rim, yaw: -Math.PI / 2 - 0.3, p, stone: k < 0.35, s: 1.0 };
  }
  if (t < S.pot) {    // flying, exhausted, through the heat, then lands by the pot
    const k = seg(t, S.heat, S.pot - 0.3);
    p.flap = k < 1 ? 1 : 0; p.pant = 1; p.eyes = 0.6;
    return { pos: [lerp(-5, POT.x + 0.5, k), lerp(2.6, 0.02, k) + 0.15 * Math.sin(t * 3) * (1 - k), lerp(1.2, POT.z + 0.35, k)], yaw: lerp(1.96, -2.18, seg(k, 0.85, 1)), p, stone: false, s: 1.0 };
  }
  if (t < S.idea) {   // up on the rim, peering in: a little water at the bottom
    p.peck = seg(t, S.pot + 0.4, S.pot + 1.0) * 0.9; p.pant = 0.6; p.eyes = 1.1;
    if (t > 10.6) { p.peck = 0.2; p.tilt = 0.25; p.eyes = 0.8; }
    return { pos: rim, yaw: -Math.PI / 2 - 0.3, p, stone: false, s: 1.0 };
  }
  if (t < S.pond) {   // the idea (a bulb), hops down toward the stones
    const k = seg(t, S.idea + 1.4, S.pond - 0.3);
    p.eyes = 1.2; p.beak = 0.4; p.tilt = -0.2;
    return { pos: [lerp(rim[0], 1.2, k), lerp(rim[1], 0.0, k) + Math.abs(Math.sin(k * Math.PI * 3)) * 0.18, lerp(rim[2], 0.6, k)], yaw: lerp(-1.87, 0.5, seg(t, S.idea, S.idea + 0.4)), p, stone: false, s: 1.0 };
  }
  if (t < S.stones) { // sees the pond! hops/flies toward it
    p.eyes = 1.25; p.beak = 0.5; p.happy = false;
    const k = seg(t, S.go, S.stones);
    p.flap = t > S.go ? 0.6 : 0;
    return { pos: [lerp(1.2, 2.4, k), Math.abs(Math.sin(t * 7)) * 0.12 * (t > S.go ? 1 : 0), lerp(0.6, 0.5, k)], yaw: t < S.go ? 2.33 : 1.7, p, stone: false, s: 1.0 };
  }
  if (t < S.pick) {   // stops: stones on the path, people hurting
    p.eyes = 1.05; p.tilt = 0.3 * Math.sin(t * 2); p.peck = t < S.hurt ? 0.5 : 0;
    const look = t < S.hurt ? -1.4 : t < S.pick - 0.9 ? 1.3 : t < S.pick - 0.45 ? 2.33 : -1.6;   // the stones; the people; the pond… then back to work
    return { pos: [2.4, 0, 0.5], yaw: look, p, stone: false, s: 1.0 };
  }
  if (t < S.drink) {  // picks them up one by one and drops them in the pot
    const i = clamp(Math.floor((t - S.pick - 0.2) / 0.7), 0, STONES.length - 1);
    const u = clamp((t - PICK_T(i)) / 0.7);
    const st = STONES[i];
    const ground: [number, number, number] = [st.x, 0, st.z];
    if (u < 0.3) { p.peck = 0.9; return { pos: ground, yaw: Math.atan2(POT.x - st.x, POT.z - st.z), p, stone: u > 0.18, s: 1.0 }; }
    const k = Easing.inOut(Easing.quad)((u - 0.3) / 0.7);
    p.flap = 1;
    const pos = lerp3(ground, rim, k); pos[1] += Math.sin(Math.PI * k) * 0.5;
    return { pos, yaw: Math.atan2(POT.x - st.x, POT.z - st.z), p, stone: k < 0.8, s: 1.0 };
  }
  if (t < S.end) {    // drinks from the full pot
    p.peck = 0.7 + 0.25 * Math.sin(t * 6); p.eyes = 0; p.happy = true;
    if (t > 35.9) { p.peck = 0; p.eyes = 0; p.happy = true; p.tilt = 0.2; }
    return { pos: rim, yaw: -Math.PI / 2 - 0.3, p, stone: false, s: 1.0 };
  }
  // the girl leaves him a piece of roti; he hops to it, then sits on the pot at sunset
  p.eyes = t > 38.5 ? 0 : 1; p.happy = true; p.tilt = 0.15 * Math.sin(t * 2);
  return { pos: rim, yaw: -0.4, p, stone: false, s: 1.0 };
}

// ------------------------------------------------------------------ people
const GIRL: Look = { skin: "#b07854", hair: "#140e0c", hairStyle: "ponytail", shirt: "#f0a030", inner: "#ffe0a0", pants: "#c83a4a", shoes: "#b07854", face: true };
const BABA: Look = { skin: "#9a6a48", hair: "#ece8e0", hairStyle: "receding", shirt: "#e8e0cc", inner: "#c9bea4", pants: "#e0d8c4", shoes: "#9a6a48", face: true, beard: "#e0dcd2" };
type Actor = { look: Look; pose: Pose; pos: [number, number, number]; yaw: number; s: number; handR?: React.ReactNode; handL?: React.ReactNode };

const Lota: React.FC = () => <Toon geom={G.sphere} color="#c8a040" position={[0, -0.02, 0.04]} scale={[0.08, 0.07, 0.08]} outline={0.006} />;
const Stick: React.FC = () => <mesh position={[0, -0.4, 0.05]} scale={[0.012, 0.85, 0.012]}><cylinderGeometry args={[1, 1, 1, 6]} /><meshToonMaterial color="#7a5a34" /></mesh>;

function peopleAt(t: number): Actor[] {
  const out: Actor[] = [];
  if (t >= S.hurt && t < S.pick) {   // they walk the stony path: she steps on one and hops, he limps
    const k = (t - S.hurt) / (S.pick - S.hurt);
    const g = restPose(); g.walk = 1; g.phase = t * 7; g.smile = 0.2;
    const ouch = t > S.hurt + 0.9 && t < S.hurt + 2.4;
    if (ouch) { g.walk = 0; g.smile = -0.7; g.brow = 1; g.eyes = 0.2; g.mouthO = 0.9; g.tear = clamp((t - S.hurt - 1.1) / 1); g.tearAlpha = 0.9; g.armL = [-0.6, 0.6]; g.headPitch = 0.3; }
    const walked = t - S.hurt - clamp(t - (S.hurt + 0.9), 0, 1.5);
    out.push({ look: GIRL, pose: g, pos: [3.6 - 0.7 * walked, ouch ? 0.04 * Math.abs(Math.sin(t * 14)) : 0, 0.15], yaw: -Math.PI / 2, s: 0.55, handR: <Lota /> });
    const b = restPose(); b.walk = 0.6; b.phase = t * 4.5; b.headPitch = 0.3; b.brow = 0.9; b.smile = -0.4; b.armR = [-0.5, -0.1]; b.elbowR = -0.3;
    out.push({ look: BABA, pose: b, pos: [lerp(4.3, 3.3, k), -0.02 * Math.abs(Math.sin(t * 4.5)), -0.25], yaw: -Math.PI / 2, s: 0.82, handR: <Stick /> });
  }
  if (t >= S.clear && t < S.drink) {  // the path is clear: they walk easily now
    const k = (t - S.clear) / (S.drink - S.clear);
    const g = restPose(); g.walk = 1; g.phase = t * 8; g.smile = 1; g.happyEyes = true; g.eyes = 0;
    out.push({ look: GIRL, pose: g, pos: [lerp(0.9, -2.0, k), 0.03 * Math.abs(Math.sin(t * 8)), 0.15], yaw: -Math.PI / 2, s: 0.55, handR: <Lota /> });
    const b = restPose(); b.walk = 1; b.phase = t * 6; b.smile = 0.7; b.armR = [-0.5, -0.1]; b.elbowR = -0.3;
    out.push({ look: BABA, pose: b, pos: [lerp(1.4, -0.4, k), 0, -0.25], yaw: -Math.PI / 2, s: 0.82, handR: <Stick /> });
  }
  if (t >= S.end) {   // she kneels by the pot and leaves him a piece of roti, smiling
    const g = restPose(); g.sit = 1; g.armR = [-1.3, -0.2]; g.elbowR = -0.3; g.smile = 1; g.blush = 0.6; g.headPitch = 0.2;
    if (t > 38.6) { g.sit = 0; g.armR = [0, -0.1]; g.elbowR = 0.15; g.headYaw = 0.6; }
    out.push({ look: GIRL, pose: g, pos: [POT.x + 0.7, t > 38.6 ? 0 : -0.1, POT.z + 0.45], yaw: -2.0, s: 0.55 });
  }
  return out;
}

// ------------------------------------------------------------------ set pieces
const Matka: React.FC<{ level: number }> = ({ level }) => {
  const geo = useMemo(() => {
    const pts = [[0.0, 0], [0.16, 0.0], [0.24, 0.1], [0.27, 0.25], [0.24, 0.38], [0.15, 0.46], [0.11, 0.5], [0.13, 0.52], [0.12, 0.54]].map(([x, y]) => new THREE.Vector2(x, y));
    return new THREE.LatheGeometry(pts, 28);
  }, []);
  const r = 0.24 - Math.abs(level - 0.25) * 0.5;
  return (
    <group position={POT}>
      <mesh geometry={geo} castShadow><meshToonMaterial color="#b55a32" side={THREE.FrontSide} /></mesh>
      <mesh geometry={geo}><meshToonMaterial color="#4a2010" side={THREE.BackSide} /></mesh>
      <mesh position={[0, 0.3, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[0.272, 0.272, 0.04]}><torusGeometry args={[1, 0.1, 6, 28]} /><meshToonMaterial color="#8a3e20" /></mesh>
      <mesh position={[0, 0.05 + level * 0.44, 0]} rotation={[-Math.PI / 2, 0, 0]} scale={Math.max(0.08, r)}><circleGeometry args={[1, 24]} /><meshStandardMaterial color={level < 0.1 ? "#2c5f86" : "#5aa0d0"} roughness={0.15} metalness={0.3} /></mesh>
    </group>
  );
};

const Stones: React.FC<{ t: number; storybook: boolean }> = ({ t, storybook }) => (
  <group>
    {STONES.map((st, i) => {
      if (storybook) return null;
      if (t >= PICK_T(i) + 0.18) return null;   // picked up
      return <mesh key={i} position={[st.x, st.s * 0.6, st.z]} rotation={[st.rot, st.rot * 2, 0]} scale={st.s}><dodecahedronGeometry args={[1, 0]} /><meshToonMaterial color="#8a8680" /></mesh>;
    })}
  </group>
);

const World: React.FC<{ t: number }> = ({ t }) => {
  const grass = useMemo(() => { const r = rng(4); return Array.from({ length: 120 }, () => ({ x: -8 + r() * 16, z: -7 + r() * 10, h: 0.1 + r() * 0.15 })); }, []);
  const dry = t >= S.heat && t < S.pick;
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[60, 60]} /><meshToonMaterial color={dry ? "#c8a46a" : "#a8b860"} /></mesh>
      {/* the dirt path */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.004, 0]} receiveShadow><planeGeometry args={[30, 1.4]} /><meshToonMaterial color="#b8905a" /></mesh>
      {grass.map((g, k) => Math.abs(g.z) < 0.8 ? null : <mesh key={k} position={[g.x, g.h / 2, g.z]}><coneGeometry args={[0.03, g.h, 4]} /><meshToonMaterial color={dry ? "#9a8a4a" : "#5a8a3a"} /></mesh>)}
      {/* tree over the pot */}
      <group position={TREE}>
        <mesh position={[0, 1.2, 0]} castShadow><cylinderGeometry args={[0.14, 0.22, 2.4, 10]} /><meshToonMaterial color="#5a3a24" /></mesh>
        {[[0, 2.7, 0, 1.2], [0.7, 2.4, 0.3, 0.85], [-0.6, 2.5, 0.2, 0.9], [0.2, 3.2, -0.2, 0.8]].map(([x, y, z, r], k) => <Toon key={k} geom={G.sphere} color={dry ? "#6a7a3a" : "#3a6a30"} position={[x, y, z]} scale={r} outline={0.005} />)}
      </group>
      {/* the pond with lotuses */}
      <group position={POND}>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]} scale={[1.8, 1.2, 1]}><circleGeometry args={[1, 32]} /><meshStandardMaterial color="#3a8ab0" roughness={0.1} metalness={0.35} /></mesh>
        {Array.from({ length: 5 }).map((_, k) => (
          <group key={k} position={[Math.cos(k * 1.3) * 0.9, 0.03, Math.sin(k * 1.3) * 0.6]}>
            <mesh rotation={[-Math.PI / 2, 0, 0]} scale={0.14}><circleGeometry args={[1, 12]} /><meshToonMaterial color="#3a8a3a" /></mesh>
            <mesh position={[0, 0.05, 0]} scale={[0.05, 0.06, 0.05]}><sphereGeometry args={[1, 8, 6]} /><meshToonMaterial color="#ff8ab0" /></mesh>
          </group>
        ))}
        {Array.from({ length: 12 }).map((_, k) => { const a = (t * 0.6 + k) % 1; return <mesh key={"g" + k} rotation={[-Math.PI / 2, 0, 0]} position={[Math.cos(k * 2.1) * 1.2, 0.02, Math.sin(k * 2.1) * 0.8]} scale={[0.2 * a, 0.03, 1]}><planeGeometry /><meshBasicMaterial color="#e8f8ff" transparent opacity={0.6 * (1 - a)} /></mesh>; })}
      </group>
      {/* village huts in the back */}
      {[[-5, -6, "#c8a070"], [-2.4, -7, "#b89060"], [6.5, -7.5, "#c89a68"]].map(([x, z, c], k) => (
        <group key={k} position={[x as number, 0, z as number]}>
          <Toon geom={G.box} color={c as string} position={[0, 0.7, 0]} scale={[1.8, 1.4, 1.5]} outline={0.004} />
          <mesh position={[0, 1.7, 0]} rotation={[0, Math.PI / 4, 0]}><coneGeometry args={[1.5, 0.9, 4]} /><meshToonMaterial color="#c8a040" /></mesh>
        </group>
      ))}
    </group>
  );
};

// ------------------------------------------------------------------ camera
type Cam = { pos: [number, number, number]; target: [number, number, number]; fov: number; roll?: number };
// the crow's position averaged over ~0.8 s, so tracking shots glide instead of jerking with every hop
function crowSmooth(t: number): [number, number, number] {
  const acc = [0, 0, 0]; let n = 0;
  for (let d = -0.4; d <= 0.401; d += 0.1) { const q = crowAt(t + d).pos; acc[0] += q[0]; acc[1] += q[1]; acc[2] += q[2]; n++; }
  return [acc[0] / n, acc[1] / n, acc[2] / n];
}
const add = (a: number[], b: number[]) => a.map((v, i) => v + b[i]) as [number, number, number];
const GIRL_OUCH_X = 3.6 - 0.7 * 0.9;
function camAt(t: number): Cam {
  const P = [POT.x, 0, POT.z];
  if (t < S.heat) { const k = t / S.heat; return { pos: lerp3([0.05, 0.95, 1.25], [0.05, 0.85, 0.75], k), target: [0.05, 0.5, POT.z], fov: 38 }; }   // storybook: side profile
  if (t < S.pot) { const c = crowSmooth(t); return { pos: add(c, [-0.35, 0.25, 2.0]), target: add(c, [0, 0.15, 0]), fov: 44 }; }                       // tracking the tired crow
  if (t < S.idea) { if (t < 10.4) return { pos: lerp3([-0.9, 0.42, 0.25], [-0.75, 0.45, 0.0], seg(t, S.pot, 10.4)), target: [0.05, 0.62, POT.z], fov: 40 };   // low 3/4 front: peering in
    return { pos: [POT.x + 0.02, lerp(1.15, 0.95, seg(t, 10.4, S.idea)), POT.z + 0.03], target: [POT.x, 0.0, POT.z], fov: 40 }; }                // POV: down into the pot
  if (t < S.pond) { const c = crowSmooth(t); return { pos: add(c, [0.75, 0.32, 1.75]), target: add(c, [0, 0.32, 0]), fov: 38 }; }                     // the idea, then the hop down
  if (t < S.go) { const c = crowAt(t).pos;
    if (t < S.pond + 1.1) return { pos: add(c, [0.78, 0.3, -0.42]), target: add(c, [0, 0.26, 0]), fov: 34 };                                            // his eyes widen
    return { pos: add(c, [-1.1, 0.7, 1.25]), target: [POND.x, 0.1, POND.z], fov: 40 }; }                                                              // over his shoulder: the pond
  if (t < S.stones) { const c = crowSmooth(t); return { pos: add(c, [-0.3, 0.45, 1.9]), target: add(c, [0.12, 0.2, 0]), fov: 42 }; }                 // he hops toward it
  if (t < S.hurt) { const k = seg(t, S.stones, S.hurt); return { pos: [lerp(0.9, 1.35, k), 0.13, 0.42], target: [2.4, 0.16, 0.45], fov: 44 }; }     // ground level: stones in front, crow behind
  if (t < S.pick) {
    if (t < S.hurt + 1.2) return { pos: [1.6, 0.85, 3.2], target: [3.2, 0.5, 0.0], fov: 46 };                                                         // the girl steps on one
    if (t < S.hurt + 2.4) return { pos: [GIRL_OUCH_X - 1.0, 1.08, 0.18], target: [GIRL_OUCH_X, 1.0, 0.15], fov: 36 };                              // close: she cries
    return { pos: [1.75, 0.4, 1.95], target: [3.3, 0.78, -0.2], fov: 42 };                                                                          // over the crow: the old man limps
  }
  if (t < S.clear) {                                                                                                                                  // stone by stone
    if (t < 29.9) return { pos: [-3.0, 1.1, 1.6], target: [lerp(-0.4, 0.1, seg(t, S.pick, 29.9)), 0.3, -0.7], fov: 44 };
    if (t < 30.7) return { pos: [POT.x + 0.02, lerp(1.05, 0.9, seg(t, 29.9, 30.7)), POT.z + 0.03], target: [POT.x, 0.0, POT.z], fov: 40 };   // POV: plink, the water rises
    return { pos: [2.2, 0.45, 1.7], target: [0.55, 0.25, -0.35], fov: 44 };
  }
  if (t < S.drink) { const k = seg(t, S.clear, S.drink); return { pos: [lerp(-3.0, -3.7, k), 0.85, 2.1], target: [lerp(0.4, -1.4, k), 0.45, -0.2], fov: 44 }; }   // the path clears: they walk to us
  if (t < S.end) return { pos: [POT.x + 0.2, 0.78, POT.z + 1.85], target: [POT.x + 0.05, 0.58, POT.z], fov: 38 };                                     // he drinks
  const k = Easing.inOut(Easing.cubic)(clamp((t - S.end) / (END - S.end)));
  return { pos: lerp3(add(P, [1.6, 0.8, 1.7]), [3.2, 3.4, 4.6], k), target: lerp3(add(P, [0.3, 0.5, 0]), [0.6, 0.4, -1.0], k), fov: 44 };
}
const CameraRig: React.FC<{ t: number }> = ({ t }) => {
  const { camera } = useThree();
  const k = camAt(t);
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(...k.pos); cam.up.set(Math.sin(k.roll ?? 0), Math.cos(k.roll ?? 0), 0);
  cam.fov = k.fov; cam.near = 0.02; cam.far = 120; cam.lookAt(V(...k.target)); cam.updateProjectionMatrix();
  return null;
};

const Scene: React.FC<{ t: number }> = ({ t }) => {
  const crow = crowAt(t);
  const storybook = t < S.heat;
  const picked = STONES.filter((_, i) => t >= PICK_T(i) + 0.65).length;
  const level = storybook ? 0.3 + 0.5 * clamp(t / S.heat) : t < S.pick ? 0.06 : t < S.drink ? 0.06 + 0.86 * (picked / STONES.length) : 0.95;
  const sunset = t >= S.end ? seg(t, S.end, END) : 0;
  const hot = t >= S.heat && t < S.pick;
  const skyD = useMemo(() => skyMat("#5aa8f0", "#fff0c8", 0), []);
  const skyHot = useMemo(() => skyMat("#e8a050", "#fff4d0", 0), []);
  const skySet = useMemo(() => skyMat("#4a3a7a", "#ff9a50", 0.1), []);
  return (
    <>
      <CameraRig t={t} />
      <mesh material={sunset > 0.4 ? skySet : hot ? skyHot : skyD} scale={100}><sphereGeometry args={[1, 32, 16]} /></mesh>
      <mesh position={[12, 18, -40]}><sphereGeometry args={[hot ? 3.4 : 2.4, 24, 16]} /><meshBasicMaterial color={hot ? "#fff6c0" : sunset > 0.4 ? "#ffb070" : "#fffbe0"} /></mesh>
      <fog attach="fog" args={[sunset > 0.4 ? "#e8a070" : hot ? "#f0dcb0" : "#e8eef0", 14, 50]} />
      <ambientLight intensity={hot ? 1.2 : 0.95} color={sunset > 0.4 ? "#ffd0a0" : "#ffffff"} />
      <hemisphereLight args={["#9ad0ff", "#6a5a3a", 0.5]} />
      <directionalLight position={sunset > 0.4 ? [-10, 5, -2] : [6, 12, 4]} intensity={hot ? 2.6 : 2.0} color={sunset > 0.4 ? "#ff9a50" : hot ? "#fff0c0" : "#fff4e0"} castShadow
        shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-6} shadow-camera-right={6} shadow-camera-top={6} shadow-camera-bottom={-6} shadow-bias={-0.001} />
      <directionalLight position={[-4, 3, -6]} intensity={0.9} color="#ffe8c0" />
      <World t={t} />
      <Matka level={level} />
      <Stones t={t} storybook={storybook} />
      {(t >= 10.4 && t < S.idea) || (t >= 29.9 && t < 30.7) ? null : <group position={crow.pos} rotation={[0, crow.yaw, 0]} scale={crow.s}><Crow p={crow.p} t={t} stone={crow.stone} /></group>}
      {peopleAt(t).map((a, k) => (
        <group key={k} position={a.pos} rotation={[0, a.yaw, 0]} scale={a.s}><Person look={a.look} pose={a.pose} handR={a.handR} handL={a.handL} /></group>
      ))}
      {/* the idea bulb over his head */}
      {t >= S.idea + 0.3 && t < S.idea + 1.8 ? (
        <group position={[crow.pos[0], crow.pos[1] + 0.55, crow.pos[2]]} scale={0.6 * seg(t, S.idea + 0.3, S.idea + 0.6)}>
          <mesh scale={0.12}><sphereGeometry args={[1, 16, 12]} /><meshBasicMaterial color="#fff2a0" /></mesh>
          <mesh position={[0, -0.13, 0]} scale={[0.05, 0.05, 0.05]}><cylinderGeometry args={[1, 1, 1, 10]} /><meshToonMaterial color="#8a8a90" /></mesh>
          <pointLight color="#fff2a0" intensity={2.5} distance={1.5} />
        </group>
      ) : null}
      {/* plink: a splash ring each time a stone drops in */}
      {t >= S.pick && t < S.drink ? STONES.map((_, i) => { const u = (t - (PICK_T(i) + 0.65)) / 0.5; if (u < 0 || u > 1) return null;
        return <mesh key={i} position={[POT.x, 0.06 + level * 0.44 + 0.01, POT.z]} rotation={[-Math.PI / 2, 0, 0]} scale={0.04 + u * 0.18}><ringGeometry args={[0.85, 1, 24]} /><meshBasicMaterial color="#e8f8ff" transparent opacity={1 - u} /></mesh>; }) : null}
      {t >= S.pick && t < S.drink ? STONES.map((st, i) => { const u = (t - (PICK_T(i) + 0.55)) / 0.1; if (u < 0 || u > 1) return null;
        return <mesh key={"fall" + i} position={[POT.x + 0.05, lerp(POT_MOUTH + 0.3, 0.06 + level * 0.44, u * u), POT.z]} scale={st.s * 0.8}><dodecahedronGeometry args={[1, 0]} /><meshToonMaterial color="#8a8680" /></mesh>; }) : null}
      {/* the roti she leaves for him */}
      {t >= S.end + 0.6 ? <mesh position={[POT.x + 0.35, 0.02, POT.z + 0.3]} rotation={[-Math.PI / 2, 0, 0]} scale={0.09}><circleGeometry args={[1, 20]} /><meshToonMaterial color="#d8a860" /></mesh> : null}
    </>
  );
};

export const Kauwa3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const sub = SUBS.find(([a, b]) => t >= a && t < b);
  const storybook = t < S.heat;
  const cuts = (Object.keys(S) as (keyof typeof S)[]).map((k) => S[k]);
  let dip = 0; for (const c of cuts) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.1);
  const fade = Math.min(clamp(t / 0.4), clamp((END - t) / 1.0));
  const hot = t >= S.heat && t < S.pick;
  const filter = storybook ? "sepia(0.75) saturate(0.9) contrast(1.05)" : hot ? "saturate(1.15) contrast(1.05)" : "none";
  // the storybook page tears away at the cut to the real heat
  const tear = seg(t, S.heat - 0.45, S.heat + 0.05);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter, transform: hot ? `translateX(${2 * Math.sin(t * 40)}px)` : "none" }}>
        <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
          <Scene t={t} />
        </ThreeCanvas>
      </AbsoluteFill>
      {storybook || tear < 1 ? (
        <AbsoluteFill style={{ pointerEvents: "none", transform: `translateX(${-1200 * tear}px) rotate(${-8 * tear}deg)`, opacity: storybook ? 1 : 1 - tear }}>
          <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(255,240,210,0) 45%, rgba(120,80,40,0.55) 100%)", border: "28px solid #e8d8b0", boxShadow: "inset 0 0 60px rgba(90,60,30,0.6)" }} />
          <div style={{ position: "absolute", top: 120, left: 0, right: 0, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif", fontSize: 54, fontWeight: 700, color: "#5a3a1e" }}>प्यासा कौआ</div>
        </AbsoluteFill>
      ) : null}
      {hot ? <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(255,180,80,0.18), rgba(255,220,150,0))", pointerEvents: "none" }} /> : null}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)" }} />
      {sub ? (
        <div style={{ position: "absolute", top: 1300, left: 60, right: 60, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 54, lineHeight: 1.4, color: "#faf6ee", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill",
          textShadow: "0 4px 14px rgba(0,0,0,0.75)" }}>{sub[2]}</div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.3) }} />
    </AbsoluteFill>
  );
};
