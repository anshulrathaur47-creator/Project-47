import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { G, Look, Person, Pose, Toon, restPose } from "./Character";
import { rng } from "./World";

// "रात आया मेरे घर एक चोर…" (ReelAudio-33727), 3D. A tired man gives a thief everything, even his grief.
export const DURATION = 1443; // 48.1 s
const FPS = 30;
const END = DURATION / FPS;
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (x: number) => { const t = clamp(x); return t * t * (3 - 2 * t); };
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: number[], b: number[], t: number) => a.map((v, i) => lerp(v, b[i], t)) as [number, number, number];
const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

// Whisper (chunked) timings
const ITEMS = [21.85, 23.88, 25.9, 27.88, 29.9, 31.9, 33.9, 35.85, 37.88, 39.95, 41.95, 43.93];
const ITEM_TEXT = ["मेरी जीत भी ले जा", "मेरी हार भी ले जा", "मेरा डर भी ले जा", "मेरा घर भी ले जा", "मेरे ख़्वाब भी ले जा", "मेरे राज़ भी ले जा",
  "मेरा ग़म भी ले जा", "हर ज़ख़्म भी ले जा", "मेरी जात भी ले जा", "औक़ात भी ले जा", "मेरी बात भी ले जा", "हालात भी ले जा"];
const LINES: [number, number, string][] = [
  [0.0, 3.6, "रात आया"], [3.75, 7.9, "मेरे घर एक चोर"], [8.35, 11.5, "आके बोला"], [11.95, 15.5, "दे दे मुझे जो भी तेरा है"], [15.85, 19.6, "मैंने बोला"],
  ...ITEMS.map((s, i) => [s, i + 1 < ITEMS.length ? ITEMS[i + 1] - 0.03 : 46.3, ITEM_TEXT[i]] as [number, number, string]),
];
const CUTS = [3.75, 8.35, 11.95, 15.85, 19.0, ...ITEMS, 46.3];

// ------------------------------------------------------------------ people
const lungiTex = (() => {
  if (typeof document === "undefined") return undefined;
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const x = c.getContext("2d")!;
  x.fillStyle = "#3d5a8a"; x.fillRect(0, 0, 64, 64);
  x.fillStyle = "rgba(240,240,250,0.55)"; for (let i = 0; i < 64; i += 16) { x.fillRect(i, 0, 4, 64); x.fillRect(0, i, 64, 4); }
  x.fillStyle = "rgba(20,30,60,0.5)"; for (let i = 8; i < 64; i += 16) { x.fillRect(i, 0, 2, 64); x.fillRect(0, i, 64, 2); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(2, 3); return t;
})();
const MAN: Look = { skin: "#b27a55", hair: "#d8d4cc", hairStyle: "receding", shirt: "#e8e0cc", inner: "#c9bea4", pants: "#3d5a8a", pantsMap: lungiTex,
  shoes: "#5a3a22", face: true, beard: "#cfcac0" };
const THIEF: Look = { skin: "#8a6448", hair: "#2a3042", hairStyle: "hood", shirt: "#2e3850", inner: "#3a4560", pants: "#252c3e", shoes: "#14161c", face: true, eyeMask: true };

const MAN_SEAT = V(-0.8, 0, 0.45);
const MAN_STAND = V(-0.4, 0, 0.45);
const THIEF_AT = V(0.85, 0, 0.45);
const SACK = V(0.38, 0.9, 0.45);
const HAND = V(0.02, 1.08, 0.45);

type Actor = { look: Look; pose: Pose; pos: THREE.Vector3; yaw: number; s: number; handR?: React.ReactNode; handL?: React.ReactNode };

const itemIdx = (t: number) => ITEMS.filter((s) => t >= s).length - 1;

function man(t: number): Actor {
  const p = restPose();
  p.smile = -0.2; p.brow = 0.75; p.eyes = 0.7;
  let pos = MAN_SEAT.clone();
  if (t < 17.4) {   // awake on the cot, elbows on knees
    p.sit = 1; p.armL = [-0.9, 0.3]; p.armR = [-0.9, -0.3]; p.elbowL = -1.3; p.elbowR = -1.3; p.headPitch = 0.35; p.lookY = -0.5;
    if (t > 8.6) { p.headPitch = lerp(0.35, -0.2, seg(t, 8.6, 9.4)); p.lookY = 0.4; p.eyes = 0.85; }
    if (t > 15.9) { p.tear = clamp((t - 16.2) / 1.2); p.tearAlpha = 0.9; p.smile = lerp(-0.2, 0.35, seg(t, 16.4, 17.2)); p.eyes = lerp(0.85, 0.5, seg(t, 16.0, 16.8)); }
  } else {          // stands, and gives everything away
    const k = seg(t, 17.4, 18.6);
    p.sit = k < 0.5 ? 1 : 0;
    pos = MAN_SEAT.clone().lerp(MAN_STAND, k);
    p.headPitch = 0.05; p.smile = 0.3; p.brow = 0.8; p.eyes = 0.6; p.tear = 1; p.tearAlpha = 0.85;
    if (t > 19.0 && t < 21.8) { p.headYaw = 0.9 * Math.sin(((t - 19.0) / 2.8) * Math.PI); }   // looks round his room
    const i = itemIdx(t);
    if (i >= 0) {
      const u = t - ITEMS[i];
      const give = u < 1.3 ? Math.sin(Math.PI * clamp(u / 1.3)) : 0;
      p.armR = [lerp(0, -1.2, give), -0.1]; p.armL = [lerp(0, -1.2, give), 0.1]; p.elbowR = -0.4; p.elbowL = -0.4;
      p.headPitch = 0.25 * give;
      if (i === 6) {   // ग़म: he hugs the photo first, then lets it go
        const hug = u < 1.0 ? seg(u, 0, 0.3) : 1 - seg(u, 1.0, 1.3);
        p.armR = [-0.9 * hug - 1.2 * seg(u, 1.0, 1.4) * (1 - seg(u, 1.6, 1.9)), -0.35 * hug]; p.armL = [p.armR[0], 0.35 * hug];
        p.elbowR = -1.6 * hug - 0.3; p.elbowL = p.elbowR;
        p.eyes = 0.1 + 0.5 * (1 - hug); p.headPitch = 0.3 * hug; p.tear = 1;
      }
      if (i === 11) { p.armR = [-0.3, -1.3 * smooth(u / 0.8)]; p.armL = [-0.3, 1.3 * smooth(u / 0.8)]; p.elbowR = -0.1; p.elbowL = -0.1; p.headPitch = -0.2; p.smile = 0.45; }
    }
    if (t > 46.0) {   // sits back down; the thief sits beside him
      const k2 = seg(t, 46.0, 46.9);
      pos = MAN_STAND.clone().lerp(MAN_SEAT, k2); p.sit = k2 > 0.5 ? 1 : 0;
      p.armL = [-0.9, 0.3]; p.armR = [-0.9, -0.3]; p.elbowL = -1.3; p.elbowR = -1.3; p.headPitch = 0.2; p.eyes = 0.1; p.happyEyes = false; p.smile = 0.45;
    }
  }
  const hold = heldItem(t);
  return { look: MAN, pose: p, pos, yaw: Math.PI / 2, s: 0.85, handR: hold };
}

function thief(t: number): Actor {
  const p = restPose();
  p.smile = 0; p.brow = -0.5; p.eyes = 0.8;
  let pos = THIEF_AT.clone(), yaw = -Math.PI / 2;
  if (t < 8.4) {   // climbs in through the window, crosses the room
    if (t < 6.4) {
      const k = seg(t, 4.0, 6.2);
      pos = V(lerp(1.5, 1.4, k), lerp(0.75, 0, seg(t, 5.2, 6.2)), lerp(-3.6, -2.4, k));
      yaw = 0; p.armL = [-2.6, 0.3]; p.armR = [-2.6, -0.3]; p.headPitch = 0.3;
    } else {
      const k = seg(t, 6.4, 8.2);
      pos = V(lerp(1.4, THIEF_AT.x, k), 0, lerp(-2.4, THIEF_AT.z, k)); yaw = lerp(0, -Math.PI / 2, seg(t, 6.4, 7.2));
      p.walk = k > 0 && k < 1 ? 1 : 0; p.phase = t * 7;
    }
  } else {
    // holds the sack out in front
    p.armL = [-0.9, 0.25]; p.armR = [-0.9, -0.25]; p.elbowL = -0.8; p.elbowR = -0.8;
    if (t > 11.95 && t < 15.6) { p.armR = [-1.4, -0.1]; p.elbowR = -0.1; p.headPitch = -0.1; p.brow = -0.7; }   // "de de"
    // his eyes soften as the things pile up; after the photo he is moved
    const i = itemIdx(t);
    if (i >= 3) { p.brow = lerp(-0.5, 0.3, (i - 3) / 3); }
    if (i >= 6) { p.brow = 0.85; p.eyes = 0.7; p.headPitch = 0.15; }
    if (t > 42) { p.tear = clamp((t - 42.3) / 1.5); p.tearAlpha = 0.9; }
    if (t > 46.0) {   // puts the sack down and sits beside him, hand on his shoulder
      const k = seg(t, 46.0, 47.0);
      pos = THIEF_AT.clone().lerp(V(-0.15, 0, 0.6), k); yaw = lerp(-Math.PI / 2, Math.PI / 2 + 0.6, k);
      p.sit = k > 0.6 ? 1 : 0; p.armR = [-1.0, 0.0]; p.armL = [0, 0.1]; p.elbowR = -0.4;
      if (k > 0.6) { yaw = Math.PI / 2 - 0.3; p.armL = [-1.2, 0.6]; p.elbowL = -0.3; p.armR = [-0.8, -0.3]; p.elbowR = -1.2; }
    }
  }
  return { look: THIEF, pose: p, pos, yaw, s: 0.88 };
}

// ------------------------------------------------------------------ the 12 things (visual signs)
const portraitTex = (() => {
  if (typeof document === "undefined") return undefined;
  const c = document.createElement("canvas"); c.width = 128; c.height = 160;
  const x = c.getContext("2d")!;
  const g = x.createLinearGradient(0, 0, 0, 160); g.addColorStop(0, "#c9b48a"); g.addColorStop(1, "#8a7350"); x.fillStyle = g; x.fillRect(0, 0, 128, 160);
  x.fillStyle = "#2a1a12"; x.beginPath(); x.ellipse(64, 66, 34, 40, 0, 0, Math.PI * 2); x.fill();               // hair
  x.fillStyle = "#c08a64"; x.beginPath(); x.ellipse(64, 72, 26, 30, 0, 0, Math.PI * 2); x.fill();                // face
  x.fillStyle = "#b02030"; x.beginPath(); x.arc(64, 54, 3, 0, Math.PI * 2); x.fill();                             // bindi
  x.strokeStyle = "#5a2a1a"; x.lineWidth = 3; x.beginPath(); x.arc(64, 80, 10, 0.15 * Math.PI, 0.85 * Math.PI); x.stroke();
  x.fillStyle = "#1a1010"; x.beginPath(); x.arc(54, 68, 3, 0, 7); x.arc(74, 68, 3, 0, 7); x.fill();
  x.fillStyle = "#9a2a4a"; x.fillRect(24, 110, 80, 50);                                                             // saree
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
})();
const textTex = (lines: string[], bg: string, fg: string, w = 256, h = 160) => {
  if (typeof document === "undefined") return undefined;
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  const x = c.getContext("2d")!; x.fillStyle = bg; x.fillRect(0, 0, w, h); x.fillStyle = fg;
  lines.forEach((l, i) => { x.font = `${i === 0 ? 700 : 400} ${i === 0 ? 30 : 22}px 'Noto Sans Devanagari'`; x.fillText(l, 14, 40 + i * 34); });
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
};
const ID_TEX = textTex(["पहचान पत्र", "नाम: रमेश", "उम्र: 52", "पता: झोपड़ी नं. 7"], "#e8e2cc", "#2a2a40");
const LETTER_TEX = textTex(["प्रिय बेटा,", "बहुत दिन हुए", "तुम्हारी आवाज़", "नहीं सुनी..."], "#f4ecd8", "#3a2a20");
const FAIL_TEX = textTex(["परिणाम", "अनुत्तीर्ण ✕"], "#efe8d6", "#a01a1a");

const heartShape = (() => {
  const s = new THREE.Shape();
  s.moveTo(0, -0.3); s.bezierCurveTo(-0.6, 0.1, -0.35, 0.55, 0, 0.25); s.bezierCurveTo(0.35, 0.55, 0.6, 0.1, 0, -0.3);
  return new THREE.ExtrudeGeometry(s, { depth: 0.08, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 });
})();

const ItemMesh: React.FC<{ i: number; t: number }> = ({ i, t }) => {
  switch (i) {
    case 0: return (   // जीत: a small brass trophy
      <group scale={0.9}>
        <Toon geom={G.cyl} color="#d9a63a" position={[0, 0.09, 0]} scale={[0.06, 0.08, 0.06]} outline={0.01} emissive="#5a3a00" emissiveIntensity={0.5} />
        <Toon geom={G.cyl} color="#c8962e" position={[0, 0.03, 0]} scale={[0.015, 0.05, 0.015]} outline={0} />
        <Toon geom={G.box} color="#5a3a22" position={[0, -0.01, 0]} scale={[0.07, 0.03, 0.07]} outline={0.01} />
      </group>
    );
    case 1: return (   // हार: a crumpled result paper
      <mesh rotation={[0.2, 0.3, 0.15]}><planeGeometry args={[0.18, 0.12]} /><meshBasicMaterial map={FAIL_TEX} side={THREE.DoubleSide} /></mesh>
    );
    case 2: return (   // डर: a dark, shivering smoke ball
      <group>{[0, 1, 2, 3, 4].map((k) => (
        <mesh key={k} position={[Math.sin(t * 9 + k) * 0.02, k * 0.02, Math.cos(t * 7 + k) * 0.02]} scale={0.05 + 0.01 * k}>
          <sphereGeometry args={[1, 12, 8]} /><meshBasicMaterial color="#2a1a3a" transparent opacity={0.65} />
        </mesh>))}
        <pointLight color="#7a3aff" intensity={0.6} distance={0.8} />
      </group>
    );
    case 3: return (   // घर: house keys on a ring
      <group>
        <mesh rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.03, 0.006, 6, 16]} /><meshStandardMaterial color="#c9b06a" metalness={0.8} roughness={0.3} /></mesh>
        {[-1, 1].map((s) => (
          <group key={s} position={[s * 0.02, -0.06, 0]} rotation={[0, 0, s * 0.3]}>
            <Toon geom={G.box} color="#d8c070" scale={[0.012, 0.08, 0.004]} outline={0} />
            <Toon geom={G.cyl} color="#d8c070" position={[0, 0.045, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[0.02, 0.005, 0.02]} outline={0} />
          </group>))}
      </group>
    );
    case 4: return (   // ख़्वाब: a dream bubble with a tiny heart
      <group>
        {[[0, 0, 0.09], [-0.07, -0.03, 0.06], [0.07, -0.02, 0.065], [0, 0.05, 0.07]].map(([x, y, r], k) => (
          <mesh key={k} position={[x, y, 0]} scale={r}><sphereGeometry args={[1, 16, 12]} /><meshBasicMaterial color="#e8f0ff" transparent opacity={0.85} /></mesh>))}
        <mesh geometry={heartShape} position={[0, 0.005, 0.07]} rotation={[0, 0, Math.PI]} scale={0.1}><meshBasicMaterial color="#ff5a7a" /></mesh>
        <pointLight color="#bcd4ff" intensity={0.8} distance={1} />
      </group>
    );
    case 5: return (   // राज़: a diary with a lock
      <group rotation={[0.3, 0.4, 0]}>
        <Toon geom={G.box} color="#6a2a2a" scale={[0.12, 0.16, 0.03]} outline={0.01} />
        <Toon geom={G.box} color="#d9b04a" position={[0.06, 0, 0.012]} scale={[0.02, 0.03, 0.012]} outline={0} />
      </group>
    );
    case 6: return (   // ग़म: his late wife's photo with a marigold garland
      <group>
        <Toon geom={G.box} color="#4a2e1a" scale={[0.2, 0.25, 0.02]} outline={0.006} />
        <mesh position={[0, 0, 0.011]}><planeGeometry args={[0.16, 0.2]} /><meshBasicMaterial map={portraitTex} /></mesh>
        {Array.from({ length: 14 }).map((_, k) => {
          const a = Math.PI * (0.05 + 0.9 * (k / 13));
          return <mesh key={k} position={[Math.cos(a) * 0.1, 0.06 - Math.sin(a) * 0.15, 0.02]} scale={0.014}><sphereGeometry args={[1, 6, 5]} /><meshToonMaterial color="#f08a1a" /></mesh>;
        })}
      </group>
    );
    case 7: return (   // ज़ख़्म: a cracked, glowing heart
      <group rotation={[0, 0, Math.PI]} scale={0.22}>
        <mesh geometry={heartShape}><meshBasicMaterial color="#c81a2a" /></mesh>
        <mesh position={[0, -0.02, 0.12]} rotation={[0, 0, 0.3]} scale={[0.02, 0.5, 0.02]}><boxGeometry /><meshBasicMaterial color="#1a0505" /></mesh>
        <pointLight color="#ff2a3a" intensity={0.9} distance={1} />
      </group>
    );
    case 8: return (   // जात: a worn identity card
      <mesh rotation={[0, 0.3, 0.1]}><planeGeometry args={[0.18, 0.115]} /><meshBasicMaterial map={ID_TEX} side={THREE.DoubleSide} /></mesh>
    );
    case 9: return (   // औक़ात: an empty wallet, two coins
      <group>
        <Toon geom={G.box} color="#4a2a1a" scale={[0.11, 0.075, 0.02]} outline={0.01} />
        {[0, 1].map((k) => <mesh key={k} position={[0.03 * k - 0.015, -0.06 - 0.03 * k, 0.01]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.015, 0.015, 0.004, 16]} /><meshStandardMaterial color="#c9a24a" metalness={0.9} roughness={0.3} /></mesh>)}
      </group>
    );
    case 10: return (  // बात: an unsent letter
      <mesh rotation={[0.1, 0.4, -0.1]}><planeGeometry args={[0.16, 0.11]} /><meshBasicMaterial map={LETTER_TEX} side={THREE.DoubleSide} /></mesh>
    );
    default: return (  // हालात: a swirl of everything that is left
      <group>{Array.from({ length: 10 }).map((_, k) => (
        <mesh key={k} position={[Math.cos(t * 4 + k) * 0.08, (k - 5) * 0.012, Math.sin(t * 4 + k) * 0.08]} scale={0.012}>
          <sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color="#ffd27a" />
        </mesh>))}
        <pointLight color="#ffc070" intensity={0.8} distance={1} />
      </group>
    );
  }
};

// where the current item is: in his hands, flying in an arc, sinking into the sack
function itemState(t: number): { i: number; pos: THREE.Vector3; scale: number; inHand: boolean } | null {
  const i = itemIdx(t);
  if (i < 0 || t > 46.0) return null;
  let u = t - ITEMS[i];
  if (i === 6) u = Math.max(0, u - 1.0);   // the hug delays the photo
  if (u > 1.5) return null;
  if (u < 0.35) return { i, pos: HAND.clone(), scale: smooth(u / 0.25), inHand: true };
  const k = Easing.inOut(Easing.quad)(clamp((u - 0.35) / 0.75));
  const p = HAND.clone().lerp(SACK, k); p.y += Math.sin(Math.PI * k) * 0.35;
  return { i, pos: p, scale: u > 1.1 ? 1 - smooth((u - 1.1) / 0.35) : 1, inHand: false };
}
function heldItem(t: number) { void t; return null; }

const Sack: React.FC<{ t: number }> = ({ t }) => {
  if (t < 8.0) return null;
  const n = ITEMS.filter((s) => t > s + 1.4).length;
  const r = 0.16 + 0.012 * n;
  const flash = Math.max(0, ...ITEMS.map((s) => 1 - Math.abs(t - (s + 1.35)) / 0.2));
  const dropped = t > 46.0;
  const pos = dropped ? lerp3([SACK.x, SACK.y - r * 0.4, SACK.z], [0.6, r * 0.8, 0.8], seg(t, 46.0, 46.6)) : [SACK.x, SACK.y - r * 0.4, SACK.z];
  return (
    <group position={pos as [number, number, number]}>
      {/* a jute sack: soft body, cinched neck, rope */}
      <Toon geom={G.sphere} color="#b8925e" scale={[r * 0.85, r * 1.25, r * 0.7]} outline={0.008} />
      <Toon geom={G.cyl} color="#a8824e" position={[0, r * 1.25, 0]} scale={[r * 0.28, r * 0.35, r * 0.28]} outline={0.006} />
      <mesh position={[0, r * 1.22, 0]} rotation={[Math.PI / 2, 0, 0]} scale={r * 0.3}><torusGeometry args={[1, 0.12, 6, 16]} /><meshToonMaterial color="#5a3e1e" /></mesh>
      {[-0.3, 0, 0.3].map((y) => <mesh key={y} position={[0, y * r, r * 0.69]}><planeGeometry args={[r * 1.4, 0.006]} /><meshBasicMaterial color="#8a6a3e" /></mesh>)}
      <pointLight position={[0, r, 0]} color="#ffc070" intensity={flash * 2 + n * 0.06} distance={1.6} />
      {dropped ? Array.from({ length: 12 }).map((_, k) => {   // the things spill out, glowing
        const kk = seg(t, 46.3 + k * 0.05, 47.2 + k * 0.05);
        return <mesh key={k} position={[Math.cos(k * 0.6) * 0.5 * kk, 0.05 - r * 0.8 + 0.02, Math.sin(k * 0.6) * 0.4 * kk]} scale={0.025}>
          <sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color={["#ffd27a", "#ff7a8a", "#bcd4ff"][k % 3]} /></mesh>;
      }) : null}
    </group>
  );
};

// ------------------------------------------------------------------ the room
const Room: React.FC<{ t: number }> = ({ t }) => {
  const mud = "#8a6a4e", mud2 = "#7a5c42";
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[6, 6]} /><meshToonMaterial color="#5a4632" /></mesh>
      {/* back wall with a window hole (x 1..2, y 1..2) */}
      <mesh position={[-1, 1.5, -3]} receiveShadow><boxGeometry args={[4, 3, 0.15]} /><meshToonMaterial color={mud} /></mesh>
      <mesh position={[2.5, 1.5, -3]}><boxGeometry args={[1, 3, 0.15]} /><meshToonMaterial color={mud} /></mesh>
      <mesh position={[1.5, 0.5, -3]}><boxGeometry args={[1, 1, 0.15]} /><meshToonMaterial color={mud} /></mesh>
      <mesh position={[1.5, 2.5, -3]}><boxGeometry args={[1, 1, 0.15]} /><meshToonMaterial color={mud} /></mesh>
      {[[1.0, 1.5], [2.0, 1.5]].map(([x, y]) => <mesh key={x} position={[x, y, -3]}><boxGeometry args={[0.06, 1.0, 0.2]} /><meshToonMaterial color="#3a2a1a" /></mesh>)}
      {[1.33, 1.66].map((x) => <mesh key={x} position={[x, 1.5, -3]}><boxGeometry args={[0.025, 1.0, 0.03]} /><meshToonMaterial color="#2a2a2a" /></mesh>)}
      <mesh position={[-3, 1.5, 0]} rotation={[0, Math.PI / 2, 0]} receiveShadow><boxGeometry args={[6, 3, 0.15]} /><meshToonMaterial color={mud2} /></mesh>
      <mesh position={[3, 1.5, 0]} rotation={[0, Math.PI / 2, 0]}><boxGeometry args={[6, 3, 0.15]} /><meshToonMaterial color={mud2} /></mesh>
      <mesh position={[0, 3.02, 0]} rotation={[Math.PI / 2, 0, 0]}><planeGeometry args={[6, 6]} /><meshToonMaterial color="#5a5a62" side={THREE.DoubleSide} /></mesh>
      {/* cracks */}
      {[[-1.5, 2.2, 0.3], [-0.2, 1.0, -0.5], [2.6, 2.0, 0.8]].map(([x, y, r], k) => (
        <mesh key={k} position={[x, y, -2.92]} rotation={[0, 0, r]}><planeGeometry args={[0.02, 0.7]} /><meshBasicMaterial color="#3a2818" /></mesh>))}
      {/* cot */}
      <group position={[-1.4, 0, 0.45]}>
        <Toon geom={G.box} color="#c9a46a" position={[0, 0.42, 0]} scale={[1.8, 0.03, 0.9]} outline={0.003} />
        {[[-0.85, -0.4], [0.85, -0.4], [-0.85, 0.4], [0.85, 0.4]].map(([x, z], k) => <Toon key={k} geom={G.cyl} color="#5a3a1e" position={[x, 0.2, z]} scale={[0.04, 0.42, 0.04]} outline={0.004} />)}
        {[-0.45, 0.45].map((z) => <Toon key={z} geom={G.box} color="#6a4424" position={[0, 0.42, z]} scale={[1.8, 0.05, 0.05]} outline={0.003} />)}
      </group>
      {/* trunk + lantern */}
      <Toon geom={G.box} color="#4a5a6a" position={[-2.3, 0.25, -2.2]} scale={[0.9, 0.5, 0.5]} outline={0.004} />
      <group position={[-2.3, 0.5, -2.2]}>
        <Toon geom={G.cyl} color="#2a2a2a" position={[0, 0.03, 0]} scale={[0.07, 0.06, 0.07]} outline={0.004} />
        <mesh position={[0, 0.14, 0]}><cylinderGeometry args={[0.055, 0.055, 0.14, 12]} /><meshBasicMaterial color="#ffd890" transparent opacity={0.85} /></mesh>
        <pointLight position={[0, 0.16, 0]} color="#ffb060" intensity={4.5 + 0.6 * Math.sin(t * 13) + 0.3 * Math.sin(t * 29)} distance={7} decay={1.3} castShadow
          shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-bias={-0.002} />
      </group>
      {/* shelf with the trophy; the photo on the left wall (before he gives them) */}
      <Toon geom={G.box} color="#5a3a1e" position={[-1.0, 1.45, -2.85]} scale={[0.7, 0.04, 0.22]} outline={0.003} />
      {t < ITEMS[0] ? <group position={[-1.0, 1.5, -2.85]}><ItemMesh i={0} t={t} /></group> : null}
      {t < ITEMS[6] ? <group position={[-2.9, 1.75, -0.8]} rotation={[0, Math.PI / 2, 0]} scale={2.2}><ItemMesh i={6} t={t} /></group> : null}
      {/* a leaking roof drip into a bucket */}
      <Toon geom={G.cyl} color="#6a6a72" position={[1.9, 0.14, 1.6]} scale={[0.16, 0.28, 0.16]} outline={0.004} />
      {(() => { const k = (t * 0.9) % 1; return <mesh position={[1.9, 3 - k * 2.7, 1.6]} scale={[0.015, 0.03, 0.015]}><sphereGeometry args={[1, 6, 6]} /><meshBasicMaterial color="#9fc0e0" /></mesh>; })()}
    </group>
  );
};

const Outside: React.FC<{ t: number }> = ({ t }) => {
  const drops = useMemo(() => { const r = rng(4); return Array.from({ length: 300 }, () => ({ x: -4 + r() * 10, z: -11 + r() * 9, y0: r() * 6, sp: 7 + r() * 3 })); }, []);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, -8]}><planeGeometry args={[30, 12]} /><meshToonMaterial color="#1a1e24" /></mesh>
      {/* tin roof seen from outside */}
      <mesh position={[0, 3.25, -0.2]} rotation={[0.18, 0, 0]}><boxGeometry args={[6.6, 0.06, 6.8]} /><meshToonMaterial color="#6a6e78" /></mesh>
      {drops.map((d, k) => <mesh key={k} position={[d.x, 6 - ((d.y0 + t * d.sp) % 6), d.z]} rotation={[0, 0, 0.1]}><boxGeometry args={[0.008, 0.25, 0.008]} /><meshBasicMaterial color="#9fb0d0" transparent opacity={0.5} /></mesh>)}
      {/* distant huts */}
      {[[-5, -10, 2.2], [5.5, -9, 2.6], [-2, -14, 2.0]].map(([x, z, h], k) => (
        <group key={k} position={[x, 0, z]}>
          <mesh position={[0, h / 2, 0]}><boxGeometry args={[2.4, h, 2]} /><meshToonMaterial color="#3a3028" /></mesh>
          <mesh position={[0.3, h * 0.55, 1.01]}><planeGeometry args={[0.4, 0.4]} /><meshBasicMaterial color="#ffb860" /></mesh>
        </group>))}
    </group>
  );
};

// ------------------------------------------------------------------ camera
type Cam = { pos: [number, number, number]; target: [number, number, number]; fov: number; roll?: number };
const ITEM_CAMS: ((u: number) => Cam)[] = [
  (u) => ({ pos: [0.3, 1.55, 2.3], target: [0.18, 1.0, 0.45], fov: 42 - u }),                        // insert: hands to sack
  (u) => ({ pos: [0.75, 1.55, 1.75], target: [-0.4, 1.45, 0.45], fov: 40 - u }),                         // his face, from the thief's side
  (u) => ({ pos: [-1.0, 0.55, 2.5], target: [0.2, 1.25, 0.4], fov: 46, roll: 0.14 + 0.02 * u }),       // low dutch two-shot
  (u) => ({ pos: [0.3, 1.75, 1.6], target: [0.2, 0.95, 0.45], fov: 38 }),                               // from above onto the sack
  (u) => ({ pos: [lerp(1.7, 1.4, u / 2), 1.8, 3.3], target: [0, 1.2, 0.3], fov: 50 }),                  // wide room
];
function camAt(t: number): Cam {
  if (t < 3.75) {   // outside in the rain, crane down to the lit window
    const k = Easing.inOut(Easing.cubic)(t / 3.75);
    return { pos: lerp3([3.5, 5.5, -11], [1.6, 1.6, -5.4], k), target: lerp3([1.5, 1.5, -3], [1.5, 1.45, -3], k), fov: lerp(46, 40, k) };
  }
  if (t < 8.35) {   // inside, low by the floor: a shape climbs through the window
    const k = (t - 3.75) / 4.6;
    return { pos: [lerp(-0.6, -0.3, k), 0.4, 2.2], target: [lerp(1.4, 0.9, k), lerp(1.3, 1.1, k), lerp(-2.6, -0.5, k)], fov: 46 };
  }
  if (t < 11.95) {  // over his shoulder: the thief standing over him
    return { pos: [-2.0, 1.45, 1.15], target: [0.85, 1.4, 0.45], fov: 40 };
  }
  if (t < 15.85) {  // low dutch on the thief, sack held out
    const k = (t - 11.95) / 3.9;
    return { pos: [-0.15, 0.85, 1.75], target: [0.85, 1.4, 0.45], fov: lerp(42, 36, k), roll: -0.16 };
  }
  if (t < 19.0) {   // his face: a tear, a small smile
    const k = (t - 15.85) / 3.15;
    return { pos: [lerp(0.5, 0.35, k), 1.25, lerp(1.9, 1.7, k)], target: [-0.8, 1.1, 0.45], fov: 40 };
  }
  if (t < ITEMS[0]) {   // he stands; the camera drifts across his room (trophy, photo)
    const k = Easing.inOut(Easing.quad)((t - 19.0) / (ITEMS[0] - 19.0));
    return { pos: lerp3([1.0, 1.7, 2.9], [-0.3, 1.7, 2.2], k), target: lerp3([-0.4, 1.3, 0.4], [-2.6, 1.6, -0.9], k), fov: 46 };
  }
  if (t < 46.0) {
    const i = itemIdx(t), u = t - ITEMS[i];
    if (i === 6) return u < 1.0 ? { pos: [0.8, 1.5, 1.85], target: [-0.4, 1.35, 0.45], fov: 40 } : { pos: [-0.35, 1.65, 1.9], target: [0.85, 1.5, 0.45], fov: 40 };
    if (i === 7) return { pos: [0.7, 1.35, 1.8], target: [-0.4, 1.25, 0.45], fov: 40 };
    if (i === 9) return { pos: [-0.4, 1.65, 1.85], target: [0.85, 1.52, 0.45], fov: 40 };
    if (i === 11) {   // हालात: crane up over the whole broken room
      const k = Easing.inOut(Easing.cubic)(clamp(u / 2.2));
      return { pos: lerp3([0.5, 1.5, 2.7], [1.0, 2.85, 3.0], k), target: lerp3([0, 1.2, 0.4], [-0.2, 0.6, -0.2], k), fov: lerp(44, 52, k) };
    }
    return ITEM_CAMS[i % ITEM_CAMS.length](u);
  }
  // end: the thief sits beside him; slow pull back
  const k = Easing.inOut(Easing.cubic)(clamp((t - 46.0) / 2.1));
  return { pos: lerp3([0.4, 1.3, 2.4], [1.0, 1.8, 3.8], k), target: [-0.6, 0.95, 0.5], fov: 44 };
}

const CameraRig: React.FC<{ t: number }> = ({ t }) => {
  const { camera } = useThree();
  const c = camAt(t);
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(...c.pos); cam.up.set(Math.sin(c.roll ?? 0), Math.cos(c.roll ?? 0), 0);
  cam.fov = c.fov; cam.near = 0.03; cam.far = 120; cam.lookAt(V(...c.target)); cam.updateProjectionMatrix();
  return null;
};

const Scene: React.FC<{ t: number }> = ({ t }) => {
  const actors = t < 3.75 ? [] : [man(t), thief(t)];
  const it = itemState(t);
  const lightning = Math.max(0, 1 - Math.abs(t - 0.15) / 0.12, 1 - Math.abs(t - 2.6) / 0.1, 1 - Math.abs(t - 4.6) / 0.1);
  return (
    <>
      <CameraRig t={t} />
      <color attach="background" args={[lightning > 0.1 ? "#8a9ac0" : "#070a14"]} />
      <fog attach="fog" args={["#070a14", 8, 30]} />
      <ambientLight intensity={0.28 + lightning * 1.5} color="#8a9ad0" />
      <directionalLight position={[3, 5, -9]} intensity={0.55 + lightning * 3} color="#9fb4ff" castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024}
        shadow-camera-left={-5} shadow-camera-right={5} shadow-camera-top={5} shadow-camera-bottom={-5} shadow-bias={-0.001} />
      {/* cool rim from the window, soft fill from the front so the dark-clad thief reads */}
      <pointLight position={[1.6, 1.7, -2.4]} color="#7f9cff" intensity={2.2} distance={6} decay={1.2} />
      <pointLight position={[0.4, 2.0, 2.8]} color="#ffcf9a" intensity={0.9} distance={6} />
      <Room t={t} />
      <Outside t={t} />
      {actors.map((a, k) => (
        <group key={k} position={a.pos} rotation={[0, a.yaw, 0]} scale={a.s}>
          <Person look={a.look} pose={a.pose} handR={a.handR} handL={a.handL} />
        </group>
      ))}
      <Sack t={t} />
      {it ? (
        <group position={it.pos} scale={it.scale * (it.i === 6 ? 1.6 : 1.4)}>
          <ItemMesh i={it.i} t={t} />
          <pointLight color="#ffd8a0" intensity={0.5} distance={0.8} />
        </group>
      ) : null}
    </>
  );
};

export const Chor3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const line = LINES.find(([a, b]) => t >= a && t < b);
  let dip = 0;
  for (const c of CUTS) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.08);
  const flash = Math.max(0, 1 - Math.abs(t - 0.15) / 0.12, 1 - Math.abs(t - 2.6) / 0.1);
  const fade = Math.min(clamp(t / 0.3), clamp((END - t) / 1.0));
  const warm = t > 46.0 ? seg(t, 46.0, 47.5) : 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter: `saturate(${0.85 + 0.25 * warm}) contrast(1.05)` }}>
        <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
          <Scene t={t} />
        </ThreeCanvas>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(0,0,0,0.6) 100%)" }} />
      {line ? (
        <div style={{ position: "absolute", top: 1300, left: 50, right: 50, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 66, lineHeight: 1.35, color: "#faf6ee", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill",
          textShadow: "0 4px 14px rgba(0,0,0,0.75)" }}>{line[2]}</div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#dfe6ff", opacity: flash * 0.55 }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.4) }} />
    </AbsoluteFill>
  );
};
