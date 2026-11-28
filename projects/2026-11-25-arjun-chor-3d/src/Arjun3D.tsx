import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { G, Look, Person, Pose, Toon, restPose } from "./Character";
import { rng } from "./World";

// "रात आया मेरे घर एक चोर…" (ReelAudio-33727): Arjun, 24, gives a night thief his whole life, one memory per line.
// Twist: under the mask the thief is Arjun himself, his own pain. Then morning.
export const DURATION = 1443; // 48.1 s
const FPS = 30;
const END = DURATION / FPS;
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (x: number) => { const t = clamp(x); return t * t * (3 - 2 * t); };
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: number[], b: number[], t: number) => a.map((v, i) => lerp(v, b[i], t)) as [number, number, number];
const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

const ITEMS = [21.85, 23.88, 25.9, 27.88, 29.9, 31.9, 33.9, 35.85, 37.88, 39.95, 41.95, 43.93];
const MEM_END = 45.95;
const ITEM_TEXT = ["मेरी जीत भी ले जा", "मेरी हार भी ले जा", "मेरा डर भी ले जा", "मेरा घर भी ले जा", "मेरे ख़्वाब भी ले जा", "मेरे राज़ भी ले जा",
  "मेरा ग़म भी ले जा", "हर ज़ख़्म भी ले जा", "मेरी जात भी ले जा", "औक़ात भी ले जा", "मेरी बात भी ले जा", "हालात भी ले जा"];
const LINES: [number, number, string][] = [
  [0.0, 3.6, "रात आया"], [3.75, 7.9, "मेरे घर एक चोर"], [8.35, 11.5, "आके बोला"], [11.95, 15.5, "दे दे मुझे जो भी तेरा है"], [15.85, 19.6, "मैंने बोला"],
  ...ITEMS.map((s, i) => [s, i + 1 < ITEMS.length ? ITEMS[i + 1] - 0.03 : 46.3, ITEM_TEXT[i]] as [number, number, string]),
];
const memIdx = (t: number) => (t >= ITEMS[0] && t < MEM_END ? ITEMS.filter((s) => t >= s).length - 1 : -1);
const memU = (t: number) => { const i = memIdx(t); return i < 0 ? 0 : t - ITEMS[i]; };

// ------------------------------------------------------------------ looks
const ARJUN: Look = { skin: "#c08560", hair: "#1c1410", hairStyle: "short", shirt: "#7a1f2e", inner: "#1a1a1e", pants: "#22242c", shoes: "#f2f2f2", face: true };
const THIEF: Look = { skin: "#c08560", hair: "#2a2f3c", hairStyle: "hood", shirt: "#2b3345", inner: "#363f55", pants: "#232a3a", shoes: "#14161c", face: true, eyeMask: true };
const THIEF_UNMASKED: Look = { ...THIEF, eyeMask: false };
const MAA: Look = { skin: "#b8835e", hair: "#8a8580", hairStyle: "bun", shirt: "#a8344a", inner: "#e0b040", pants: "#a8344a", shoes: "#6a4a2a", face: true };
const GIRL: Look = { skin: "#d6a07c", hair: "#140e0c", hairStyle: "long", shirt: "#e8c8d8", inner: "#fff", pants: "#4a5a8a", shoes: "#fff", face: true };
const RIVAL: Look = { skin: "#c49070", hair: "#18120e", hairStyle: "curly", shirt: "#2a5a8a", inner: "#eee", pants: "#2a2a30", shoes: "#ddd", face: true };
const BOYS: Look[] = [
  { skin: "#c48e6a", hair: "#1a1410", hairStyle: "short", shirt: "#d0a030", inner: "#eee", pants: "#3a3a48", shoes: "#eee", face: true },
  { skin: "#b07850", hair: "#120e0c", hairStyle: "curly", shirt: "#3a8a5a", inner: "#ddd", pants: "#2a2a30", shoes: "#c33", face: true },
  { skin: "#cf9a76", hair: "#2a1c14", hairStyle: "short", shirt: "#5a5aa0", inner: "#eee", pants: "#2c3e5a", shoes: "#eee", face: true },
];

type Actor = { look: Look; pose: Pose; pos: [number, number, number]; yaw: number; s?: number; rot?: [number, number, number]; handR?: React.ReactNode; handL?: React.ReactNode };
const ActorView: React.FC<{ a: Actor }> = ({ a }) => (
  <group position={a.pos} rotation={[0, a.yaw, 0]}>
    <group rotation={a.rot ?? [0, 0, 0]} scale={a.s ?? 0.85}><Person look={a.look} pose={a.pose} handR={a.handR} handL={a.handL} /></group>
  </group>
);
const P = (f: (p: Pose) => void): Pose => { const p = restPose(); f(p); return p; };

// ------------------------------------------------------------------ small props and textures
const canvasTex = (w: number, h: number, draw: (x: CanvasRenderingContext2D) => void) => {
  if (typeof document === "undefined") return undefined;
  const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d")!);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
};
const REJECT_TEX = canvasTex(256, 180, (x) => {
  x.fillStyle = "#f2ede0"; x.fillRect(0, 0, 256, 180); x.fillStyle = "#555"; for (let i = 0; i < 6; i++) x.fillRect(20, 30 + i * 18, 200 - (i % 2) * 50, 6);
  x.save(); x.translate(128, 100); x.rotate(-0.25); x.strokeStyle = "#c81a1a"; x.lineWidth = 6; x.strokeRect(-95, -28, 190, 56);
  x.fillStyle = "#c81a1a"; x.font = "900 40px Inter, sans-serif"; x.textAlign = "center"; x.fillText("REJECTED", 0, 14); x.restore();
});
const PAPA_TEX = canvasTex(128, 160, (x) => {
  const g = x.createLinearGradient(0, 0, 0, 160); g.addColorStop(0, "#cdb88e"); g.addColorStop(1, "#8a7350"); x.fillStyle = g; x.fillRect(0, 0, 128, 160);
  x.fillStyle = "#3a2a20"; x.beginPath(); x.ellipse(64, 58, 30, 22, 0, Math.PI, 0); x.fill();
  x.fillStyle = "#b07a55"; x.beginPath(); x.ellipse(64, 72, 26, 31, 0, 0, Math.PI * 2); x.fill();
  x.fillStyle = "#2a1a12"; x.fillRect(48, 82, 32, 6);
  x.fillStyle = "#1a1010"; x.beginPath(); x.arc(54, 68, 3, 0, 7); x.arc(74, 68, 3, 0, 7); x.fill();
  x.fillStyle = "#e8e0d0"; x.fillRect(26, 110, 76, 50);
});
const Garland: React.FC<{ w: number; h: number }> = ({ w, h }) => (
  <group>{Array.from({ length: 16 }).map((_, k) => {
    const a = Math.PI * (0.05 + 0.9 * (k / 15));
    return <mesh key={k} position={[Math.cos(a) * w, h * 0.35 - Math.sin(a) * h, 0.02]} scale={0.03}><sphereGeometry args={[1, 6, 5]} /><meshToonMaterial color={k % 2 ? "#f08a1a" : "#f6c030"} /></mesh>;
  })}</group>
);
const Trophy: React.FC = () => (
  <group>
    <Toon geom={G.cyl} color="#e0b040" position={[0, 0.12, 0]} scale={[0.07, 0.1, 0.07]} outline={0.01} emissive="#6a4a00" emissiveIntensity={0.7} />
    <Toon geom={G.box} color="#3a2a1a" position={[0, 0.0, 0]} scale={[0.08, 0.04, 0.08]} outline={0.01} />
    <pointLight color="#ffd060" intensity={1.2} distance={1.2} />
  </group>
);
const Guitar: React.FC = () => (
  <group rotation={[0, 0, -0.9]}>
    <Toon geom={G.sphere} color="#b0672a" position={[0, -0.1, 0]} scale={[0.14, 0.17, 0.05]} outline={0.008} />
    <mesh position={[0, -0.1, 0.051]} scale={0.04}><circleGeometry args={[1, 16]} /><meshBasicMaterial color="#1a1010" /></mesh>
    <Toon geom={G.box} color="#3a2414" position={[0, 0.2, 0]} scale={[0.04, 0.4, 0.025]} outline={0.006} />
  </group>
);
const Letter: React.FC = () => (
  <group><Toon geom={G.box} color="#f4c0d0" scale={[0.14, 0.09, 0.01]} outline={0.01} />
    <mesh position={[0, 0, 0.006]} rotation={[0, 0, Math.PI / 4]} scale={[0.07, 0.07, 1]}><planeGeometry /><meshBasicMaterial color="#e05a7a" /></mesh></group>
);
const Wallet: React.FC<{ open: number }> = ({ open }) => (
  <group>
    <Toon geom={G.box} color="#4a2a1a" position={[-0.05, 0, 0]} rotation={[0, open * 0.8, 0]} scale={[0.1, 0.07, 0.012]} outline={0.008} />
    <Toon geom={G.box} color="#3a2010" position={[0.05, 0, 0]} rotation={[0, -open * 0.8, 0]} scale={[0.1, 0.07, 0.012]} outline={0.008} />
  </group>
);
const Phone: React.FC<{ glow?: number }> = ({ glow = 1 }) => (
  <group rotation={[0.2, 0, 0]}>
    <mesh scale={[0.07, 0.14, 0.012]}><boxGeometry /><meshBasicMaterial color="#111" /></mesh>
    <mesh position={[0, 0, 0.007]} scale={[0.062, 0.125, 1]}><planeGeometry /><meshBasicMaterial color={new THREE.Color("#a8d0ff").multiplyScalar(0.7 + 0.5 * glow)} /></mesh>
    <pointLight position={[0, 0, 0.2]} color="#9fc8ff" intensity={0.9 * glow} distance={1.2} />
  </group>
);
const heartGeo = (() => {
  const s = new THREE.Shape();
  s.moveTo(0, -0.3); s.bezierCurveTo(-0.6, 0.1, -0.35, 0.55, 0, 0.25); s.bezierCurveTo(0.35, 0.55, 0.6, 0.1, 0, -0.3);
  return new THREE.ExtrudeGeometry(s, { depth: 0.08, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 });
})();

const Rain: React.FC<{ t: number; box: [number, number, number, number]; n?: number }> = ({ t, box, n = 220 }) => {
  const d = useMemo(() => { const r = rng(9); return Array.from({ length: 400 }, () => ({ x: r(), z: r(), y0: r() * 5, sp: 7 + r() * 3 })); }, []);
  const [x0, x1, z0, z1] = box;
  return <group>{d.slice(0, n).map((p, k) => (
    <mesh key={k} position={[lerp(x0, x1, p.x), 5 - ((p.y0 + t * p.sp) % 5), lerp(z0, z1, p.z)]} rotation={[0, 0, 0.1]}><boxGeometry args={[0.008, 0.25, 0.008]} />
      <meshBasicMaterial color="#a8b8d8" transparent opacity={0.5} /></mesh>))}</group>;
};
const Confetti: React.FC<{ t: number }> = ({ t }) => {
  const d = useMemo(() => { const r = rng(21); return Array.from({ length: 70 }, () => ({ x: (r() - 0.5) * 3, z: (r() - 0.5) * 1.5, y0: r() * 3, c: ["#ffd040", "#ff5a7a", "#5ad0ff", "#9aff6a"][Math.floor(r() * 4)], s: r() * 6 })); }, []);
  return <group>{d.map((p, k) => (
    <mesh key={k} position={[p.x + Math.sin(t * 2 + p.s) * 0.1, 3.2 - ((p.y0 + t * 1.2) % 3.2), p.z]} rotation={[t * 3 + p.s, t * 2, 0]} scale={[0.03, 0.02, 0.003]}>
      <boxGeometry /><meshBasicMaterial color={p.c} /></mesh>))}</group>;
};
const Crowd: React.FC<{ n: number; z: number; w: number; t: number }> = ({ n, z, w, t }) => (
  <group>{Array.from({ length: n }).map((_, k) => {
    const x = -w / 2 + (k / (n - 1)) * w, bob = Math.abs(Math.sin(t * 6 + k * 1.7)) * 0.06;
    return <group key={k} position={[x, 0, z + (k % 2) * 0.3]}>
      <mesh position={[0, 1.0 + bob, 0]} scale={[0.16, 0.18, 0.16]}><sphereGeometry args={[1, 10, 8]} /><meshBasicMaterial color="#0e0a10" /></mesh>
      <mesh position={[0, 0.5 + bob, 0]} scale={[0.26, 0.45, 0.18]}><sphereGeometry args={[1, 10, 8]} /><meshBasicMaterial color="#0e0a10" /></mesh>
      {k % 3 === 0 ? <mesh position={[0.14, 1.3 + bob, 0]} rotation={[0, 0, -0.3]} scale={[0.04, 0.25, 0.04]}><boxGeometry /><meshBasicMaterial color="#0e0a10" /></mesh> : null}
    </group>;
  })}</group>
);

// ------------------------------------------------------------------ the PG room (present day)
const Room: React.FC<{ t: number; dawn: number }> = ({ t, dawn }) => {
  const wall = "#5a6070", wall2 = "#4e5464";
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[6, 6]} /><meshToonMaterial color="#3a3a42" /></mesh>
      <mesh position={[-1, 1.5, -3]} receiveShadow><boxGeometry args={[4, 3, 0.15]} /><meshToonMaterial color={wall} /></mesh>
      <mesh position={[2.5, 1.5, -3]}><boxGeometry args={[1, 3, 0.15]} /><meshToonMaterial color={wall} /></mesh>
      <mesh position={[1.5, 0.5, -3]}><boxGeometry args={[1, 1, 0.15]} /><meshToonMaterial color={wall} /></mesh>
      <mesh position={[1.5, 2.5, -3]}><boxGeometry args={[1, 1, 0.15]} /><meshToonMaterial color={wall} /></mesh>
      {[1.0, 2.0].map((x) => <mesh key={x} position={[x, 1.5, -3]}><boxGeometry args={[0.06, 1.0, 0.2]} /><meshToonMaterial color="#2a2a30" /></mesh>)}
      <mesh position={[1.5, 1.5, -3.6]}><planeGeometry args={[3, 3]} /><meshBasicMaterial color={new THREE.Color("#0a1022").lerp(new THREE.Color("#ffb070"), dawn)} /></mesh>
      <mesh position={[-3, 1.5, 0]} rotation={[0, Math.PI / 2, 0]}><boxGeometry args={[6, 3, 0.15]} /><meshToonMaterial color={wall2} /></mesh>
      <mesh position={[3, 1.5, 0]} rotation={[0, Math.PI / 2, 0]}><boxGeometry args={[6, 3, 0.15]} /><meshToonMaterial color={wall2} /></mesh>
      <mesh position={[0, 3.02, 0]} rotation={[Math.PI / 2, 0, 0]}><planeGeometry args={[6, 6]} /><meshToonMaterial color="#44464e" side={THREE.DoubleSide} /></mesh>
      {/* bed with mattress + pillow */}
      <group position={[-1.6, 0, -0.25]}>
        <Toon geom={G.box} color="#3a2a20" position={[0, 0.2, 0]} scale={[1.0, 0.4, 2.0]} outline={0.003} />
        <Toon geom={G.box} color="#c8ccd8" position={[0, 0.46, 0]} scale={[0.95, 0.12, 1.95]} outline={0.003} />
        <Toon geom={G.box} color="#e8e8f0" position={[0, 0.58, -0.75]} scale={[0.6, 0.12, 0.35]} outline={0.003} />
      </group>
      {/* desk, laptop glow, posters, guitar against the wall */}
      <Toon geom={G.box} color="#5a3e2a" position={[2.4, 0.75, 0.6]} scale={[0.6, 0.05, 1.2]} outline={0.003} />
      <mesh position={[2.35, 0.95, 0.6]} rotation={[0, -Math.PI / 2, 0.2]}><planeGeometry args={[0.45, 0.3]} /><meshBasicMaterial color="#8ab4ff" /></mesh>
      <pointLight position={[2.0, 1.1, 0.6]} color="#7aa4ff" intensity={1.2} distance={3} />
      {[[-2.2, 2.0, "#e05a3a"], [-0.6, 2.1, "#3a8ae0"]].map(([x, y, c], k) => (
        <mesh key={k} position={[x as number, y as number, -2.92]}><planeGeometry args={[0.6, 0.8]} /><meshBasicMaterial color={c as string} /></mesh>))}
      <group position={[2.7, 0.6, -2.4]} rotation={[0.1, -0.6, 0.2]} scale={1.6}><Guitar /></group>
      {/* bedside lamp */}
      <pointLight position={[-0.8, 1.0, -1.4]} color="#ffb070" intensity={2.4 + 0.2 * Math.sin(t * 9)} distance={6} decay={1.4} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-bias={-0.002} />
      <mesh position={[-0.8, 0.85, -1.4]}><sphereGeometry args={[0.08, 12, 10]} /><meshBasicMaterial color="#ffd8a0" /></mesh>
      <Rain t={t} box={[0.6, 2.4, -6, -3.3]} n={dawn > 0.5 ? 0 : 120} />
    </group>
  );
};

// ------------------------------------------------------------------ the memories (one small set each, far from the room)
const MEM_ORIGIN = (i: number) => V(40 + i * 14, 0, 0);
type Mem = { bg: string; amb: number; key: string; actors: (u: number) => Actor[]; set: (u: number, t: number) => React.ReactNode; cam: (u: number) => { pos: [number, number, number]; target: [number, number, number]; fov: number; roll?: number } };

const MEMS: Mem[] = [
  { // जीत: college stage, trophy up, confetti
    bg: "#1a0e08", amb: 0.5, key: "#ffcf70",
    actors: (u) => [{ look: ARJUN, pose: P((p) => { p.armR = [-2.9, -0.2]; p.elbowR = -0.2; p.armL = [-0.3, 0.6]; p.smile = 1; p.eyes = 0; p.happyEyes = true; p.headPitch = -0.15 - 0.05 * Math.sin(u * 8); p.blush = 0.6; }),
      pos: [0, 0.4, 0], yaw: 0, handR: <group position={[0, 0.02, 0]}><Trophy /></group> }],
    set: (u, t) => <>
      <Toon geom={G.box} color="#5a2a1a" position={[0, 0.2, 0]} scale={[4, 0.4, 2]} outline={0} />
      <mesh position={[0, 2, -1.2]}><planeGeometry args={[6, 4]} /><meshToonMaterial color="#6a1a2a" /></mesh>
      <spotLight position={[0, 4.5, 1.5]} angle={0.4} penumbra={0.5} intensity={30} distance={10} color="#fff0c8" />
      <group position={[0, 0.4, 0]}><Confetti t={t} /></group>
      <Crowd n={7} z={1.8} w={3.6} t={u} />
    </>,
    cam: (u) => ({ pos: [0.2, 1.0, 3.6], target: [0, 1.7, 0], fov: lerp(44, 38, u / 2) }),
  },
  { // हार: walking out of the interview, REJECTED letter flying away
    bg: "#20262e", amb: 0.9, key: "#c8d8ff",
    actors: (u) => [{ look: ARJUN, pose: P((p) => { p.walk = 1; p.phase = u * 6; p.armSwing = 0.3; p.headPitch = 0.45; p.lookY = -0.8; p.brow = 0.9; p.smile = -0.4; p.eyes = 0.6; }), pos: [0, 0, lerp(-0.6, 0.4, u / 2)], yaw: 0 }],
    set: (u) => <>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[8, 8]} /><meshToonMaterial color="#8a8e96" /></mesh>
      <mesh position={[0, 1.5, -1.5]}><planeGeometry args={[6, 3]} /><meshToonMaterial color="#c8ccd2" /></mesh>
      <Toon geom={G.box} color="#2a2e36" position={[0, 1.1, -1.45]} scale={[1.2, 2.2, 0.05]} outline={0} />
      <mesh position={[0, 1.1, -1.42]}><planeGeometry args={[1.05, 2.05]} /><meshBasicMaterial color="#8ab0c8" transparent opacity={0.6} /></mesh>
      <mesh position={[lerp(0.3, 1.6, u / 2), lerp(1.0, 2.2, u / 2), lerp(0.5, 1.2, u / 2)]} rotation={[0.3, u * 2, u * 1.5]}><planeGeometry args={[0.3, 0.21]} /><meshBasicMaterial map={REJECT_TEX} side={THREE.DoubleSide} /></mesh>
    </>,
    cam: (u) => ({ pos: [0.5, 1.45, 3.0], target: [0, 1.3, 0], fov: 40 - u }),
  },
  { // डर: alone in the rain under a street light, shivering
    bg: "#05070e", amb: 0.35, key: "#9fb4ff",
    actors: (u) => [{ look: ARJUN, pose: P((p) => { p.armL = [-1.2, 0.9]; p.armR = [-1.2, -0.9]; p.elbowL = -2.0; p.elbowR = -2.0; p.headPitch = 0.3 + 0.03 * Math.sin(u * 40); p.brow = 1; p.eyes = 1.1; p.smile = -0.5; p.mouthO = 0.4; }), pos: [0.03 * Math.sin(u * 50), 0, 0], yaw: 0.3 }],
    set: (u, t) => <>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[10, 10]} /><meshStandardMaterial color="#1c2230" roughness={0.3} metalness={0.4} /></mesh>
      <mesh position={[0.9, 1.7, -0.3]}><cylinderGeometry args={[0.04, 0.05, 3.4, 10]} /><meshToonMaterial color="#2a2e38" /></mesh>
      <spotLight position={[0.5, 3.3, -0.2]} angle={0.6} penumbra={0.6} intensity={14} distance={6} color="#ffd8a0" />
      <Rain t={t} box={[-2, 2, -2, 2]} n={260} />
      {Math.abs(u - 0.5) < 0.08 ? <pointLight position={[0, 6, 2]} intensity={40} color="#c8d8ff" distance={20} /> : null}
    </>,
    cam: (u) => ({ pos: [1.8, 0.55, 3.2], target: [0, 1.25, 0], fov: 42, roll: 0.12 + 0.01 * u }),
  },
  { // घर: leaving home, Maa waving at the bus
    bg: "#f0d8b0", amb: 1.2, key: "#ffe0a8",
    actors: (u) => [
      { look: MAA, pose: P((p) => { p.armR = [-2.6, -0.3 + 0.25 * Math.sin(u * 9)]; p.elbowR = -0.4; p.smile = 0.3; p.brow = 0.8; p.tear = clamp(u / 1.5); p.tearAlpha = 0.9; }), pos: [-0.6, 0, 0.9], yaw: 2.27, s: 0.78 },
      { look: ARJUN, pose: P((p) => { p.brow = 0.8; p.smile = 0.2; p.armL = [-0.3, 0.2]; p.armR = [-1.6, -0.3]; p.elbowR = -0.3; p.tear = clamp((u - 0.6) / 1); p.tearAlpha = 0.9; }), pos: [0.75, 0.35, -0.15], yaw: -0.87,
        handL: <Toon geom={G.box} color="#3a4a6a" position={[0, -0.1, 0]} scale={[0.25, 0.3, 0.12]} outline={0.01} /> },
    ],
    set: (u) => <>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[12, 12]} /><meshToonMaterial color="#b89a70" /></mesh>
      <group position={[lerp(1.2, 1.6, smooth((u - 1.2) / 0.8)), 0, -1.2]}>
        <Toon geom={G.box} color="#d84a2a" position={[0, 1.2, 0]} scale={[3.5, 2.0, 1.6]} outline={0.004} />
        <Toon geom={G.box} color="#f2e2c0" position={[0, 1.55, 0.81]} scale={[3.3, 0.5, 0.02]} outline={0} />
        {[-1.2, 1.2].map((x) => <mesh key={x} position={[x, 0.25, 0.81]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.25, 0.25, 0.1, 16]} /><meshToonMaterial color="#1a1a1a" /></mesh>)}
      </group>
      <Toon geom={G.box} color="#8a8a90" position={[0.75, 0.17, -0.15]} scale={[0.6, 0.35, 0.4]} outline={0} />
    </>,
    cam: (u) => ({ pos: [-1.7, 1.5, 2.8], target: [0.45, 1.35, -0.2], fov: 46 - u }),
  },
  { // ख़्वाब: rooftop at night, guitar, a dream bubble of a stage
    bg: "#060a1a", amb: 0.4, key: "#a0b8ff",
    actors: (u) => [{ look: ARJUN, pose: P((p) => { p.sit = 1; p.armR = [-0.6, -0.4]; p.elbowR = -1.2 + 0.2 * Math.sin(u * 14); p.armL = [-0.8, 0.5]; p.elbowL = -1.0; p.headPitch = -0.3; p.eyes = 0; p.happyEyes = true; p.smile = 0.8; }),
      pos: [0, 0.55, 0], yaw: 0.3, handR: <group position={[-0.05, 0.05, 0.12]}><Guitar /></group> }],
    set: (u) => <>
      <Toon geom={G.box} color="#6a6a72" position={[0, 0.27, 0]} scale={[3, 0.55, 0.4]} outline={0} />
      <mesh position={[0, -0.2, -6]}><planeGeometry args={[30, 8]} /><meshBasicMaterial color="#0a0e20" /></mesh>
      {Array.from({ length: 40 }).map((_, k) => <mesh key={k} position={[-8 + (k * 0.41) % 16, 0.5 + (k * 0.73) % 3, -5.8]} scale={0.04}><planeGeometry /><meshBasicMaterial color="#ffd890" /></mesh>)}
      <group position={[0.9, 2.25, -0.3]} scale={smooth(u / 0.4)}>
        {[[0, 0, 0.5], [-0.35, -0.2, 0.32], [0.4, -0.15, 0.34], [0.05, 0.3, 0.38]].map(([x, y, r], k) => (
          <mesh key={k} position={[x, y, 0]} scale={r}><sphereGeometry args={[1, 18, 14]} /><meshBasicMaterial color="#d8e4ff" transparent opacity={0.85} /></mesh>))}
        {Array.from({ length: 9 }).map((_, k) => <mesh key={k} position={[-0.4 + k * 0.1, -0.15 + 0.06 * Math.sin(u * 8 + k), 0.52]} scale={0.035}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color={k % 2 ? "#ff5a9a" : "#ffd040"} /></mesh>)}
        <pointLight color="#ffd8ff" intensity={1.5} distance={3} />
      </group>
      {[0.6, 0.85, 1.05].map((y, k) => <mesh key={k} position={[0.25 + k * 0.18, 0.9 + y * 0.9, 0]} scale={0.03 + k * 0.015}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#d8e4ff" /></mesh>)}
    </>,
    cam: (u) => ({ pos: [lerp(-1.6, -1.3, u / 2), 1.2, 2.8], target: [0.4, 1.5, 0], fov: 46 }),
  },
  { // राज़: a letter he never gave; she reads on a bench
    bg: "#f4b88a", amb: 1.0, key: "#ffc890",
    actors: (u) => [
      { look: GIRL, pose: P((p) => { p.sit = 1; p.armL = [-0.9, 0.2]; p.armR = [-0.9, -0.2]; p.elbowL = -1.4; p.elbowR = -1.4; p.headPitch = 0.35; p.smile = 0.4; }), pos: [0.8, 0, 0], yaw: -0.5, s: 0.8,
        handR: <Toon geom={G.box} color="#3a6a9a" scale={[0.14, 0.18, 0.03]} outline={0.006} /> },
      { look: ARJUN, pose: P((p) => { p.armR = [0.7, -0.1]; p.elbowR = -0.9; p.smile = 0.6; p.blush = 0.9; p.headYaw = -0.5; p.eyes = 0.9; p.lookX = -0.8; }), pos: [-0.9, 0, -0.4], yaw: 0.6,
        handR: <group position={[0, 0, -0.05]}><Letter /></group> },
    ],
    set: () => <>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[12, 12]} /><meshToonMaterial color="#7a9a5a" /></mesh>
      <Toon geom={G.box} color="#7a5634" position={[0.8, 0.42, 0]} scale={[1.4, 0.06, 0.45]} outline={0.004} />
      <Toon geom={G.box} color="#7a5634" position={[0.8, 0.72, -0.2]} scale={[1.4, 0.45, 0.05]} outline={0.004} />
      <group position={[-1.3, 0, -0.9]}>
        <mesh position={[0, 1.1, 0]}><cylinderGeometry args={[0.12, 0.16, 2.2, 10]} /><meshToonMaterial color="#4a3020" /></mesh>
        {[[0, 2.5, 0, 0.9], [0.5, 2.2, 0.2, 0.7], [-0.45, 2.25, -0.1, 0.72]].map(([x, y, z, r], k) => <Toon key={k} geom={G.sphere} color="#4a7a3a" position={[x, y, z]} scale={r} outline={0.005} />)}
      </group>
    </>,
    cam: (u) => ({ pos: [0.0, 1.35, 4.2], target: [-0.05, 1.05, -0.2], fov: 50 - u }),
  },
  { // ग़म: papa's garlanded photo, a diya; he touches the frame
    bg: "#100806", amb: 0.35, key: "#ffb060",
    actors: (u) => [{ look: ARJUN, pose: P((p) => { p.armR = [-1.9, -0.1]; p.elbowR = -0.3; p.headPitch = 0.1; p.eyes = 0.1; p.brow = 1; p.smile = -0.3; p.tear = clamp(u / 1.2); p.tearAlpha = 0.95; }), pos: [0.25, 0, 0.6], yaw: Math.PI - 0.55 }],
    set: (u, t) => <>
      <mesh position={[0, 1.5, -0.3]}><planeGeometry args={[6, 4]} /><meshToonMaterial color="#6a4a32" /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[6, 6]} /><meshToonMaterial color="#3a2a1e" /></mesh>
      <group position={[0, 1.7, -0.27]}>
        <Toon geom={G.box} color="#3a2414" scale={[0.5, 0.62, 0.04]} outline={0.006} />
        <mesh position={[0, 0, 0.022]}><planeGeometry args={[0.42, 0.53]} /><meshBasicMaterial map={PAPA_TEX} /></mesh>
        <Garland w={0.26} h={0.4} />
      </group>
      <Toon geom={G.box} color="#5a3a22" position={[0, 1.05, -0.15]} scale={[0.8, 0.05, 0.3]} outline={0.004} />
      <mesh position={[0.25, 1.12, -0.1]} scale={[0.05, 0.02, 0.05]}><sphereGeometry args={[1, 10, 8]} /><meshToonMaterial color="#b0602a" /></mesh>
      <mesh position={[0.25, 1.17 + 0.005 * Math.sin(t * 20), -0.1]} scale={[0.012, 0.03, 0.012]}><sphereGeometry args={[1, 8, 8]} /><meshBasicMaterial color="#ffd060" /></mesh>
      <pointLight position={[0.25, 1.25, 0.05]} color="#ffa040" intensity={2.5 + 0.4 * Math.sin(t * 17)} distance={3} />
    </>,
    cam: (u) => ({ pos: [lerp(1.6, 1.4, u / 2), 1.55, 1.3], target: [0.0, 1.55, -0.1], fov: 42 }),
  },
  { // ज़ख़्म: she walks away holding someone else's hand; his heart cracks
    bg: "#0a0c18", amb: 0.5, key: "#8aa0ff",
    actors: (u) => [
      { look: GIRL, pose: P((p) => { p.walk = 1; p.phase = u * 6; p.armR = [0.1, -0.3]; }), pos: [0.2, 0, lerp(-2.0, -3.2, u / 2)], yaw: Math.PI, s: 0.8 },
      { look: RIVAL, pose: P((p) => { p.walk = 1; p.phase = u * 6 + 3; p.armL = [0.1, 0.3]; }), pos: [0.75, 0, lerp(-2.0, -3.2, u / 2)], yaw: Math.PI, s: 0.85 },
      { look: ARJUN, pose: P((p) => { p.headPitch = 0.1; p.brow = 1; p.eyes = 0.6; p.smile = -0.5; p.armL = [0, 0.1]; p.armR = [0, -0.1]; }), pos: [-0.6, 0, 0.8], yaw: Math.PI * 0.95 },
    ],
    set: (u, t) => <>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[12, 14]} /><meshStandardMaterial color="#1c2030" roughness={0.4} metalness={0.3} /></mesh>
      <spotLight position={[0.5, 4, -2.5]} angle={0.7} penumbra={0.6} intensity={12} distance={8} color="#ffd8a0" />
      <group position={[-0.6, 1.35, 0.75]} rotation={[0, Math.PI, Math.PI]} scale={0.22}>
        <mesh geometry={heartGeo}><meshBasicMaterial color="#e0203a" /></mesh>
        <mesh position={[0, 0, -0.1]} rotation={[0, 0, 0.3]} scale={[0.03 * smooth(u / 0.8), 0.55, 0.03]}><boxGeometry /><meshBasicMaterial color="#1a0505" /></mesh>
        <pointLight color="#ff2a3a" intensity={1.4} distance={1.5} />
      </group>
      <Rain t={t} box={[-2, 2, -4, 2]} n={120} />
    </>,
    cam: (u) => ({ pos: [-1.9, 1.7, 2.3], target: [0.3, 1.1, -2.0], fov: 42 }),
  },
  { // जात: they laugh at where he comes from
    bg: "#2a2622", amb: 0.7, key: "#ffe8c8",
    actors: (u) => [
      ...BOYS.map((b, k) => ({ look: b, pose: P((p) => { p.armR = [-1.4, -0.05]; p.elbowR = -0.1; p.smile = 1; p.eyes = Math.sin(u * 12 + k) > 0 ? 0 : 1; p.happyEyes = true; p.smirk = 0.6; p.headPitch = -0.2 + 0.1 * Math.sin(u * 14 + k); }),
        pos: [-0.9 + k * 0.9, 0, -1.0 - (k % 2) * 0.3] as [number, number, number], yaw: 0 })),
      { look: ARJUN, pose: P((p) => { p.headPitch = 0.5; p.brow = 1; p.eyes = 0.5; p.smile = -0.4; p.armL = [0, 0.15]; p.armR = [0, -0.15]; }), pos: [0, 0, 1.1], yaw: Math.PI },
    ],
    set: () => <>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[12, 12]} /><meshToonMaterial color="#b8b0a0" /></mesh>
      <mesh position={[0, 1.5, -2.4]}><planeGeometry args={[8, 4]} /><meshToonMaterial color="#6a5a4a" /></mesh>
    </>,
    cam: (u) => ({ pos: [2.3, 0.85, 2.7], target: [0, 1.3, -0.1], fov: 52, roll: -0.12 }),
  },
  { // औक़ात: café, friends pay, his wallet is empty
    bg: "#3a2418", amb: 0.8, key: "#ffc890",
    actors: (u) => [
      { look: BOYS[0], pose: P((p) => { p.sit = 1; p.armR = [-1.2, -0.1]; p.elbowR = -0.5; p.smile = 0.8; p.headYaw = 0.4; }), pos: [-0.75, 0, -0.5], yaw: 0.6, handR: <Toon geom={G.box} color="#c8e8ff" scale={[0.08, 0.05, 0.005]} outline={0} /> },
      { look: BOYS[2], pose: P((p) => { p.sit = 1; p.smile = 0.9; p.eyes = 0; p.happyEyes = true; }), pos: [0.75, 0, -0.5], yaw: -0.6 },
      { look: ARJUN, pose: P((p) => { p.sit = 1; p.armL = [-1.1, 0.2]; p.armR = [-1.1, -0.2]; p.elbowL = -0.8; p.elbowR = -0.8; p.headPitch = 0.45; p.lookY = -0.8; p.brow = 0.9; p.smile = 0.1; }), pos: [0, 0, 0.55], yaw: Math.PI,
        handR: <group position={[0.06, 0, 0.05]}><Wallet open={smooth(u / 0.5)} /></group> },
    ],
    set: (u) => <>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[10, 10]} /><meshToonMaterial color="#5a3a26" /></mesh>
      <Toon geom={G.cyl} color="#f2ece0" position={[0, 0.72, 0]} scale={[0.6, 0.04, 0.6]} outline={0.004} />
      <mesh position={[0, 0.36, 0]}><cylinderGeometry args={[0.04, 0.06, 0.72, 8]} /><meshToonMaterial color="#2a2a2a" /></mesh>
      {[[-0.2, -0.1], [0.2, -0.15], [0.05, 0.2]].map(([x, z], k) => <Toon key={k} geom={G.cyl} color="#ffffff" position={[x, 0.8, z]} scale={[0.05, 0.08, 0.05]} outline={0.006} />)}
      {/* a tiny moth flutters out of the empty wallet */}
      <mesh position={[0.06 + u * 0.15, 0.85 + u * 0.35 + 0.05 * Math.sin(u * 30), 0.6]} scale={[0.03 * (1 + 0.5 * Math.sin(u * 60)), 0.02, 0.005]}><boxGeometry /><meshBasicMaterial color="#d8c8a8" /></mesh>
      <pointLight position={[0, 2.2, 0]} color="#ffc890" intensity={3} distance={4} />
    </>,
    cam: (u) => ({ pos: [1.9, 1.35, 1.1], target: [0, 0.9, 0.2], fov: 42 - u }),
  },
  { // बात: an unsent message to Maa (the phone UI is drawn on top in HTML)
    bg: "#05060c", amb: 0.25, key: "#9fc8ff",
    actors: (u) => [{ look: ARJUN, pose: P((p) => { p.armR = [-1.4, -0.2]; p.elbowR = -1.3; p.headPitch = 0.3; p.lookY = -0.6; p.brow = 0.9; p.tear = 1; p.tearAlpha = 0.9; }), pos: [0, 0, 0], yaw: 0, handR: <Phone /> }],
    set: () => <mesh rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[6, 6]} /><meshToonMaterial color="#14161c" /></mesh>,
    cam: (u) => ({ pos: [0.3, 1.5, 1.4], target: [0, 1.45, 0], fov: 40 }),
  },
  { // हालात: alone on the edge of a rooftop, the whole city
    bg: "#04060e", amb: 0.35, key: "#a0b8ff",
    actors: () => [{ look: ARJUN, pose: P((p) => { p.sit = 1; p.armL = [-0.9, 0.3]; p.armR = [-0.9, -0.3]; p.elbowL = -1.3; p.elbowR = -1.3; p.headPitch = 0.2; p.eyes = 0.6; p.brow = 0.8; }), pos: [0, 0.55, 0], yaw: Math.PI }],
    set: () => <>
      <Toon geom={G.box} color="#5a5a62" position={[0, 0.27, 0]} scale={[2.5, 0.55, 0.4]} outline={0} />
      {Array.from({ length: 22 }).map((_, k) => {
        const x = -10 + k, h = 2 + ((k * 7) % 5) * 1.2, z = -4 - (k % 3) * 2;
        return <group key={k} position={[x, -3, z]}>
          <mesh position={[0, h / 2, 0]}><boxGeometry args={[0.8, h, 0.8]} /><meshToonMaterial color="#1a1e2a" /></mesh>
          {Array.from({ length: Math.floor(h / 0.5) }).map((_, j) => (j + k) % 3 ? <mesh key={j} position={[0, 0.3 + j * 0.5, 0.41]}><planeGeometry args={[0.18, 0.18]} /><meshBasicMaterial color="#ffd080" /></mesh> : null)}
        </group>;
      })}
    </>,
    cam: (u) => { const k = Easing.inOut(Easing.cubic)(clamp(u / 2)); return { pos: lerp3([0.4, 1.3, 1.8], [1.6, 3.2, 4.2], k), target: lerp3([0, 1.1, 0], [0, 0.4, -3], k), fov: lerp(40, 54, k) }; },
  },
];

// ------------------------------------------------------------------ the present (room) actors
function present(t: number): Actor[] {
  const out: Actor[] = [];
  // Arjun
  if (t < 8.35) {   // lying on the bed, phone over his face (rejection mails)
    out.push({ look: ARJUN, pose: P((p) => { p.armR = [-1.6, -0.1]; p.elbowR = -1.2; p.brow = 0.8; p.eyes = 0.6; p.lookY = 0.6; p.smile = -0.3; }), pos: [-1.6, 0.55, 0.65], yaw: Math.PI, rot: [-Math.PI / 2, 0, 0], handR: <Phone /> });
  } else if (t < MEM_END) {
    const stand = seg(t, 17.6, 18.6);
    out.push({ look: ARJUN, pose: P((p) => {
      p.sit = stand < 0.5 ? 1 : 0;
      p.headPitch = -0.15; p.eyes = 1.1; p.brow = -0.3; p.mouthO = t < 11.95 ? 0.7 : 0;
      if (t > 11.95) { p.mouthO = 0; p.brow = 0.7; p.eyes = 0.8; }
      if (t > 15.85) { p.smile = lerp(0, 0.6, seg(t, 16.0, 16.8)); p.eyes = 0.4; p.tear = clamp((t - 16.3) / 1.2); p.tearAlpha = 0.9; p.headRoll = 0.1 * Math.sin(t * 7) * (t < 17.5 ? 1 : 0); }   // a broken laugh
      if (t > 19.3) { const k = seg(t, 19.3, 20.2); p.armL = [-0.4, 1.4 * k]; p.armR = [-0.4, -1.4 * k]; p.elbowL = -0.1; p.elbowR = -0.1; p.headPitch = -0.25; p.smile = 0.5; }   // "le ja, sab le ja"
    }), pos: [lerp(-1.1, -0.65, stand), 0, -0.1], yaw: Math.PI / 2 });
  } else {          // the twist, then morning at the window
    out.push({ look: ARJUN, pose: P((p) => { p.eyes = t > 47.0 ? 0.9 : 1.15; p.brow = 0.5; p.smile = t > 47.0 ? 0.7 : 0; p.headYaw = t > 47.0 ? 0 : 0; p.tear = 1; p.tearAlpha = 0.6; }),
      pos: t > 47.0 ? [1.5, 0, -2.4] : [-0.65, 0, -0.1], yaw: t > 47.0 ? 0 : Math.PI / 2 });
  }
  // thief
  if (t >= 3.75 && t < 47.0) {
    let pos: [number, number, number] = [0.65, 0, -0.1], yaw = -Math.PI / 2;
    const pose = restPose();
    if (t < 8.35) {
      if (t < 6.4) { const k = seg(t, 4.0, 6.2); pos = [lerp(1.5, 1.4, k), lerp(0.75, 0, seg(t, 5.2, 6.2)), lerp(-3.6, -2.4, k)]; yaw = 0; pose.armL = [-2.6, 0.3]; pose.armR = [-2.6, -0.3]; }
      else { const k = seg(t, 6.4, 8.2); pos = [lerp(1.4, 0.65, k), 0, lerp(-2.4, -0.1, k)]; yaw = lerp(0, -Math.PI / 2, seg(t, 6.4, 7.2)); pose.walk = k > 0 && k < 1 ? 1 : 0; pose.phase = t * 7; }
    } else {
      pose.armL = [-0.9, 0.25]; pose.armR = [-0.9, -0.25]; pose.elbowL = -0.8; pose.elbowR = -0.8; pose.brow = -0.6; pose.eyes = 0.8;
      if (t > 11.95 && t < 15.6) { pose.armR = [-1.4, -0.1]; pose.elbowR = -0.1; }
      if (t > 15.85) { pose.brow = lerp(-0.6, 0.4, seg(t, 16.5, 19.5)); pose.eyes = 1.05; }
      if (t >= MEM_END) {   // he pulls the mask and hood off: it is Arjun's own face
        pose.armR = [-2.3 * seg(t, 45.95, 46.15) + 2.0 * seg(t, 46.2, 46.4), -0.2]; pose.elbowR = -1.4; pose.brow = 0.8; pose.eyes = 0.8; pose.smile = 0.3; pose.tear = 1; pose.tearAlpha = 0.9;
      }
    }
    const unmasked = t >= 46.2;
    out.push({ look: unmasked ? THIEF_UNMASKED : THIEF, pose, pos, yaw, s: 0.86,
      handL: t >= 8.35 && t < MEM_END + 0.3 ? <Sack n={Math.max(0, memIdx(t) + 1)} t={t} /> : undefined });
  }
  return out;
}

const Sack: React.FC<{ n: number; t: number }> = ({ n, t }) => {
  const r = 0.14 + 0.012 * n;
  return (
    <group position={[0.12, -0.1, 0.12]}>
      <Toon geom={G.sphere} color="#b8925e" scale={[r * 0.85, r * 1.2, r * 0.7]} outline={0.008} />
      <Toon geom={G.cyl} color="#a8824e" position={[0, r * 1.2, 0]} scale={[r * 0.28, r * 0.3, r * 0.28]} outline={0.006} />
      <pointLight position={[0, r * 1.4, 0]} color="#ffd080" intensity={0.3 + n * 0.12 + 0.2 * Math.sin(t * 6)} distance={1.5} />
    </group>
  );
};

// ------------------------------------------------------------------ cameras for the present
type Cam = { pos: [number, number, number]; target: [number, number, number]; fov: number; roll?: number };
function presentCam(t: number): Cam {
  if (t < 3.75) {   // outside in the rain, push in on his window
    const k = Easing.inOut(Easing.cubic)(t / 3.75);
    return { pos: lerp3([3.0, 3.5, -10], [1.6, 1.6, -5.2], k), target: [1.5, 1.45, -3], fov: lerp(46, 40, k) };
  }
  if (t < 8.35) {   // inside: he lies there; a shape fills the window
    const k = (t - 3.75) / 4.6;
    return { pos: [lerp(-0.3, 0.0, k), 1.3, 2.6], target: [lerp(0.4, 0.6, k), 1.0, -1.2], fov: 50 };
  }
  if (t < 11.95) return { pos: [-2.2, 1.5, 1.2], target: [0.65, 1.4, -0.1], fov: 40 };              // over his shoulder at the thief
  if (t < 15.85) { const k = (t - 11.95) / 3.9; return { pos: [-0.3, 0.85, 1.6], target: [0.65, 1.4, -0.1], fov: lerp(42, 36, k), roll: -0.16 }; }
  if (t < 19.3) { const k = (t - 15.85) / 3.45; return { pos: [lerp(0.45, 0.3, k), 1.3, lerp(1.7, 1.5, k)], target: [-1.1, 1.15, -0.1], fov: 40 }; }   // the broken laugh
  if (t < ITEMS[0]) { const k = (t - 19.3) / (ITEMS[0] - 19.3); const a = lerp(-0.4, 0.5, k);   // arms open, slow orbit
    return { pos: [-0.65 + 2.6 * Math.sin(a), 1.4, -0.1 + 2.6 * Math.cos(a)], target: [-0.3, 1.3, -0.1], fov: 46 }; }
  if (t < 46.35) return { pos: [-0.3, 1.5, 1.4], target: [0.65, 1.5, -0.1], fov: 38 };               // the thief's face
  if (t < 47.0) return { pos: [-0.3, 1.5, 1.3], target: [0.65, 1.5, -0.1], fov: 34 };                // ...it is Arjun
  const k = seg(t, 47.0, 48.1);
  return { pos: lerp3([1.2, 1.5, 0.2], [1.0, 1.6, 0.9], k), target: [1.5, 1.45, -2.6], fov: 44 };  // morning at the window
}

const CameraRig: React.FC<{ t: number }> = ({ t }) => {
  const { camera } = useThree();
  const i = memIdx(t);
  let c: Cam;
  if (i >= 0) {
    const m = MEMS[i].cam(memU(t)); const o = MEM_ORIGIN(i);
    c = { ...m, pos: [m.pos[0] + o.x, m.pos[1] + o.y, m.pos[2] + o.z], target: [m.target[0] + o.x, m.target[1] + o.y, m.target[2] + o.z] };
  } else c = presentCam(t);
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(...c.pos); cam.up.set(Math.sin(c.roll ?? 0), Math.cos(c.roll ?? 0), 0);
  cam.fov = c.fov; cam.near = 0.03; cam.far = 80; cam.lookAt(V(...c.target)); cam.updateProjectionMatrix();
  return null;
};

const Scene: React.FC<{ t: number }> = ({ t }) => {
  const i = memIdx(t);
  const dawn = t > 47.0 ? seg(t, 47.0, 47.8) : 0;
  const lightning = Math.max(0, 1 - Math.abs(t - 0.15) / 0.12, 1 - Math.abs(t - 2.6) / 0.1, 1 - Math.abs(t - 4.6) / 0.1);
  if (i >= 0) {
    const m = MEMS[i], o = MEM_ORIGIN(i), u = memU(t);
    return (
      <>
        <CameraRig t={t} />
        <color attach="background" args={[m.bg]} />
        <ambientLight intensity={m.amb} />
        <directionalLight position={[o.x + 3, 6, 5]} intensity={1.1} color={m.key} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024}
          shadow-camera-left={-5} shadow-camera-right={5} shadow-camera-top={5} shadow-camera-bottom={-5} shadow-bias={-0.001} />
        <pointLight position={[o.x + 1.5, 2.5, 3]} color="#ffe8d0" intensity={1.2} distance={8} />
        <group position={o}>
          {m.set(u, t)}
          {m.actors(u).map((a, k) => <ActorView key={k} a={a} />)}
        </group>
      </>
    );
  }
  return (
    <>
      <CameraRig t={t} />
      <color attach="background" args={[lightning > 0.1 ? "#8a9ac0" : "#060912"]} />
      <ambientLight intensity={0.35 + lightning * 1.4 + dawn * 0.8} color={dawn > 0 ? "#ffd8b0" : "#8a9ad0"} />
      <directionalLight position={[3, 5, -9]} intensity={0.6 + lightning * 3 + dawn * 2.5} color={dawn > 0 ? "#ffb070" : "#9fb4ff"} castShadow
        shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-5} shadow-camera-right={5} shadow-camera-top={5} shadow-camera-bottom={-5} shadow-bias={-0.001} />
      <pointLight position={[1.6, 1.7, -2.4]} color={dawn > 0 ? "#ffb070" : "#7f9cff"} intensity={2.2 + dawn * 3} distance={6} decay={1.2} />
      <pointLight position={[0.3, 2.0, 2.6]} color="#ffcf9a" intensity={0.9} distance={6} />
      <Room t={t} dawn={dawn} />
      {t < 3.75 ? <Rain t={t} box={[-3, 5, -11, -3.4]} n={260} /> : null}
      {present(t).map((a, k) => <ActorView key={k} a={a} />)}
    </>
  );
};

// the unsent message drawn as a phone screen on top
const PhoneUI: React.FC<{ u: number }> = ({ u }) => {
  const full = "Maa, main theek hoon. Khaana kha liya ❤️";
  const typed = u < 1.2 ? full.slice(0, Math.floor((u / 1.2) * full.length)) : full.slice(0, Math.max(0, Math.floor(full.length * (1 - (u - 1.35) / 0.45))));
  return (
    <div style={{ position: "absolute", left: 250, top: 330, width: 580, height: 860, borderRadius: 60, background: "#0b0d12", border: "10px solid #222", boxShadow: "0 0 80px rgba(120,160,255,0.35)", overflow: "hidden", fontFamily: "Inter, sans-serif" }}>
      <div style={{ padding: "40px 34px 20px", color: "#fff", fontWeight: 800, fontSize: 38, borderBottom: "1px solid #222" }}>Maa ❤️<div style={{ fontSize: 22, color: "#7a8", fontWeight: 500 }}>online</div></div>
      <div style={{ margin: "30px 30px 0 auto", width: 380, background: "#1e2430", color: "#dde", borderRadius: 26, padding: "18px 24px", fontSize: 28 }}>Beta, khaana khaya? Bahut din ho gaye phone nahi kiya…</div>
      <div style={{ position: "absolute", left: 24, right: 24, bottom: 36, background: "#1a1d24", borderRadius: 30, padding: "22px 26px", color: "#fff", fontSize: 30, minHeight: 40 }}>
        {typed}<span style={{ opacity: Math.floor(u * 4) % 2 ? 1 : 0 }}>|</span>
      </div>
    </div>
  );
};

export const Arjun3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const line = LINES.find(([a, b]) => t >= a && t < b);
  const i = memIdx(t), u = memU(t);
  // memories: warm sepia; each one is pulled into the dark at the end (zoom + blur + darken), with a flash at the start
  const isMem = i >= 0;
  const pull = isMem ? seg(u, 1.65, 2.0) : 0;
  const flashIn = isMem ? Math.max(0, 1 - u / 0.12) : 0;
  const cutFlash = Math.max(0, 1 - Math.abs(t - 0.15) / 0.12, 1 - Math.abs(t - 2.6) / 0.1, 1 - Math.abs(t - 46.35) / 0.1);
  const fade = Math.min(clamp(t / 0.3), clamp((END - t) / 0.8));
  const dips = [3.75, 8.35, 11.95, 15.85, MEM_END, 47.0];
  let dip = 0; for (const c of dips) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.09);
  const filter = isMem ? `sepia(${i === 10 ? 0.1 : 0.35}) saturate(1.15) brightness(${1 - 0.6 * pull}) blur(${pull * 6}px)` : "none";
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter, transform: `scale(${1 + 0.18 * pull})` }}>
        <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
          <Scene t={t} />
        </ThreeCanvas>
        {i === 10 ? <PhoneUI u={u} /> : null}
      </AbsoluteFill>
      {isMem ? <AbsoluteFill style={{ background: `radial-gradient(ellipse at center, rgba(0,0,0,0) ${45 - 30 * pull}%, rgba(8,4,12,${0.6 + 0.4 * pull}) 100%)` }} /> : null}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.5) 100%)" }} />
      {line ? (
        <div style={{ position: "absolute", top: 1300, left: 50, right: 50, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 66, lineHeight: 1.35, color: "#faf6ee", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill",
          textShadow: "0 4px 14px rgba(0,0,0,0.75)" }}>{line[2]}</div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#fff8ee", opacity: Math.max(flashIn * 0.7, cutFlash * 0.5) }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.4) }} />
    </AbsoluteFill>
  );
};
