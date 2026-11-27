import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { Sky } from "three/examples/jsm/objects/Sky.js";

// A grounded, "realistic-lighting" kit: PBR materials, canvas textures, a physical sky with image-based light,
// a proportioned human rig, a four-legged macaque, cloth caps and a banyan with thousands of leaves.

export function rng(seed: number) {
  let s = seed % 2147483647; if (s <= 0) s += 2147483646;
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}
const hash = (str: string) => { let h = 7; for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % 2147483647; return h; };
export const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const smooth = (x: number) => { const t = clamp(x); return t * t * (3 - 2 * t); };
export const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
export const V3 = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

// ------------------------------------------------------------------ textures (seeded: every render tab draws the same pixels)
const cache = new Map<string, THREE.Texture>();
type Draw = (x: CanvasRenderingContext2D, n: number, r: () => number) => void;
function canvasTex(key: string, size: number, draw: Draw, rep: [number, number] = [1, 1], srgb = true): THREE.Texture {
  const k = `${key}|${rep[0]}x${rep[1]}`;
  const hit = cache.get(k); if (hit) return hit;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const x = c.getContext("2d")!;
  draw(x, size, rng(hash(key)));
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep[0], rep[1]);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  cache.set(k, t); return t;
}
const speck = (x: CanvasRenderingContext2D, n: number, r: () => number, count: number, dark: string, light: string, a0: number, a1: number, s0: number, s1: number) => {
  for (let i = 0; i < count; i++) {
    x.globalAlpha = a0 + r() * (a1 - a0); x.fillStyle = r() < 0.5 ? dark : light;
    const s = s0 + r() * (s1 - s0); x.fillRect(r() * n, r() * n, s, s);
  }
  x.globalAlpha = 1;
};
export const dirtTex = (rep: number, base = "#8c6c4a") => canvasTex("dirt" + base, 512, (x, n, r) => {
  x.fillStyle = base; x.fillRect(0, 0, n, n);
  speck(x, n, r, 14000, "#3c2818", "#d2b48a", 0.06, 0.22, 1, 3);
  for (let i = 0; i < 260; i++) { x.fillStyle = `rgb(${130 + r() * 70 | 0},${112 + r() * 60 | 0},${92 + r() * 46 | 0})`; x.beginPath(); x.ellipse(r() * n, r() * n, 1 + r() * 3.2, 1 + r() * 2.4, r() * 3, 0, 7); x.fill(); }
  for (let i = 0; i < 50; i++) { x.strokeStyle = "rgba(50,34,20,0.12)"; x.lineWidth = 1; x.beginPath(); let px = r() * n, py = r() * n; x.moveTo(px, py); for (let k = 0; k < 5; k++) { px += (r() - 0.5) * 30; py += (r() - 0.5) * 30; x.lineTo(px, py); } x.stroke(); }
}, [rep, rep]);
export const barkTex = (rx: number, ry: number) => canvasTex("bark", 256, (x, n, r) => {
  x.fillStyle = "#5c4636"; x.fillRect(0, 0, n, n);
  for (let i = 0; i < 260; i++) {
    x.strokeStyle = r() < 0.55 ? `rgba(30,20,14,${0.2 + r() * 0.4})` : `rgba(150,128,104,${0.12 + r() * 0.25})`;
    x.lineWidth = 1 + r() * 3; const px = r() * n; x.beginPath(); x.moveTo(px, 0);
    for (let y = 0; y <= n; y += 16) x.lineTo(px + Math.sin(y * 0.05 + i) * 4 + (r() - 0.5) * 3, y); x.stroke();
  }
  speck(x, n, r, 3000, "#20160e", "#9a8a74", 0.05, 0.2, 1, 2);
}, [rx, ry]);
export const furTex = (base: string) => canvasTex("fur" + base, 256, (x, n, r) => {
  x.fillStyle = base; x.fillRect(0, 0, n, n);
  for (let i = 0; i < 9000; i++) {
    const px = r() * n, py = r() * n, a = Math.PI / 2 + (r() - 0.5) * 0.7, l = 3 + r() * 7;
    x.strokeStyle = r() < 0.5 ? `rgba(0,0,0,${0.08 + r() * 0.16})` : `rgba(255,240,220,${0.06 + r() * 0.14})`;
    x.lineWidth = 0.8; x.beginPath(); x.moveTo(px, py); x.lineTo(px + Math.cos(a) * l, py + Math.sin(a) * l); x.stroke();
  }
}, [2, 2]);
export const clothTex = (base: string, worn = 0) => canvasTex(`cloth${base}${worn}`, 256, (x, n, r) => {
  x.fillStyle = base; x.fillRect(0, 0, n, n);
  x.globalAlpha = 0.07; x.fillStyle = "#000";
  for (let i = 0; i < n; i += 2) { x.fillRect(i, 0, 1, n); x.fillRect(0, i + 1, n, 1); }
  x.globalAlpha = 1;
  speck(x, n, r, 2500, "#000000", "#ffffff", 0.02, 0.06, 1, 2);
  for (let i = 0; i < worn * 14; i++) { const g = x.createRadialGradient(0, 0, 0, 0, 0, 1); g.addColorStop(0, "rgba(90,64,36,0.22)"); g.addColorStop(1, "rgba(90,64,36,0)");
    x.save(); x.translate(r() * n, r() * n); x.scale(10 + r() * 30, 8 + r() * 24); x.fillStyle = g; x.beginPath(); x.arc(0, 0, 1, 0, 7); x.fill(); x.restore(); }
}, [2, 2]);
export const strawTex = (rep: number) => canvasTex("straw", 256, (x, n, r) => {
  x.fillStyle = "#a88a50"; x.fillRect(0, 0, n, n);
  for (let i = 0; i < 1800; i++) { x.strokeStyle = r() < 0.5 ? `rgba(60,44,20,${0.2 + r() * 0.3})` : `rgba(230,200,130,${0.2 + r() * 0.3})`;
    x.lineWidth = 1 + r(); const px = r() * n, py = r() * n; x.beginPath(); x.moveTo(px, py); x.lineTo(px + (r() - 0.5) * 6, py + 18 + r() * 30); x.stroke(); }
}, [rep, rep]);
export const mudTex = (rep: number, base = "#9a7450") => canvasTex("mud" + base, 256, (x, n, r) => {
  x.fillStyle = base; x.fillRect(0, 0, n, n);
  for (let i = 0; i < 90; i++) { x.fillStyle = r() < 0.5 ? "rgba(60,40,24,0.06)" : "rgba(220,190,150,0.06)"; x.beginPath(); x.arc(r() * n, r() * n, 8 + r() * 30, 0, 7); x.fill(); }
  speck(x, n, r, 4000, "#3a2818", "#d8c0a0", 0.04, 0.14, 1, 2);
  for (let i = 0; i < 22; i++) { x.strokeStyle = "rgba(40,26,16,0.22)"; x.lineWidth = 0.8; x.beginPath(); let px = r() * n, py = r() * n; x.moveTo(px, py); for (let k = 0; k < 4; k++) { px += (r() - 0.5) * 24; py += (r() - 0.5) * 24; x.lineTo(px, py); } x.stroke(); }
}, [rep, rep]);
export const ropeTex = (rep: number) => canvasTex("rope", 128, (x, n, r) => {
  x.fillStyle = "#6a5434"; x.fillRect(0, 0, n, n);
  for (let k = 0; k < 2; k++) for (let i = -n; i < n * 2; i += 10) {
    x.strokeStyle = k ? "#c8b07a" : "#b49a64"; x.lineWidth = 4; x.beginPath();
    if (k) { x.moveTo(i, 0); x.lineTo(i + n, n); } else { x.moveTo(i, n); x.lineTo(i + n, 0); } x.stroke();
  }
  speck(x, n, r, 800, "#2a1c0c", "#f0e0b0", 0.05, 0.2, 1, 2);
}, [rep, rep]);
export const woodTex = () => canvasTex("wood", 128, (x, n, r) => {
  x.fillStyle = "#7a5a3a"; x.fillRect(0, 0, n, n);
  for (let i = 0; i < 70; i++) { x.strokeStyle = `rgba(40,24,12,${0.1 + r() * 0.3})`; x.lineWidth = 1 + r() * 2; const py = r() * n; x.beginPath(); x.moveTo(0, py); x.bezierCurveTo(n / 3, py + (r() - 0.5) * 8, n * 2 / 3, py + (r() - 0.5) * 8, n, py); x.stroke(); }
}, [1, 1]);
// leaf and grass cards (RGBA, alpha-tested); tinted per instance
const leafTex = () => canvasTex("leaf", 128, (x, n) => {
  x.clearRect(0, 0, n, n);
  const g = x.createLinearGradient(0, 0, n, 0); g.addColorStop(0, "#b8c8a0"); g.addColorStop(0.5, "#f4f8ea"); g.addColorStop(1, "#b0c098");
  x.fillStyle = g; x.beginPath(); x.moveTo(n * 0.5, n * 0.02); x.bezierCurveTo(n * 0.98, n * 0.25, n * 0.9, n * 0.8, n * 0.5, n * 0.98); x.bezierCurveTo(n * 0.1, n * 0.8, n * 0.02, n * 0.25, n * 0.5, n * 0.02); x.fill();
  x.strokeStyle = "rgba(90,110,60,0.35)"; x.lineWidth = 1.5; x.beginPath(); x.moveTo(n * 0.5, n * 0.05); x.lineTo(n * 0.5, n * 0.97); x.stroke();
  x.lineWidth = 1; x.strokeStyle = "rgba(90,110,60,0.18)"; for (let k = 1; k < 7; k++) { const y = n * (0.12 + k * 0.12); x.beginPath(); x.moveTo(n * 0.5, y); x.lineTo(n * 0.22, y - n * 0.08); x.moveTo(n * 0.5, y); x.lineTo(n * 0.78, y - n * 0.08); x.stroke(); }
}, [1, 1]);
const grassTex = () => canvasTex("grass", 128, (x, n, r) => {
  x.clearRect(0, 0, n, n);
  for (let i = 0; i < 26; i++) { const px = 8 + r() * (n - 16), h = n * (0.45 + r() * 0.5), lean = (r() - 0.5) * 30;
    x.fillStyle = `rgb(${150 + r() * 70 | 0},${170 + r() * 60 | 0},${100 + r() * 50 | 0})`;
    x.beginPath(); x.moveTo(px - 2.5, n); x.quadraticCurveTo(px + lean * 0.3, n - h * 0.5, px + lean, n - h); x.quadraticCurveTo(px + lean * 0.3 + 1, n - h * 0.5, px + 2.5, n); x.fill(); }
}, [1, 1]);
export const flameTex = () => canvasTex("flame", 128, (x, n) => {
  x.clearRect(0, 0, n, n);
  const g = x.createRadialGradient(n / 2, n * 0.72, 2, n / 2, n * 0.62, n * 0.5);
  g.addColorStop(0, "rgba(255,250,220,1)"); g.addColorStop(0.25, "rgba(255,210,90,0.95)"); g.addColorStop(0.55, "rgba(255,120,30,0.6)"); g.addColorStop(1, "rgba(255,60,10,0)");
  x.fillStyle = g; x.beginPath(); x.moveTo(n / 2, n * 0.02); x.bezierCurveTo(n * 0.78, n * 0.4, n * 0.92, n * 0.7, n / 2, n * 0.98); x.bezierCurveTo(n * 0.08, n * 0.7, n * 0.22, n * 0.4, n / 2, n * 0.02); x.fill();
}, [1, 1]);
export const capTex = (base: string) => canvasTex("cap" + base, 256, (x, n, r) => {
  x.fillStyle = base; x.fillRect(0, 0, n, n);
  x.globalAlpha = 0.08; x.fillStyle = "#000"; for (let i = 0; i < n; i += 3) x.fillRect(0, i, n, 1); x.globalAlpha = 1;
  // gold embroidered band at the rim (top rows = v≈1 = the rim end of the lathe profile)
  x.fillStyle = "#c89a30"; x.fillRect(0, 0, n, n * 0.2);
  x.strokeStyle = "#f0d070"; x.lineWidth = 3; x.beginPath(); for (let i = 0; i <= n; i += 12) { x.lineTo(i, n * 0.05); x.lineTo(i + 6, n * 0.15); } x.stroke();
  x.fillStyle = "#7a5010"; x.fillRect(0, n * 0.2, n, 3);
  for (let i = 0; i < 40; i++) { x.fillStyle = "rgba(255,230,160,0.5)"; x.beginPath(); x.arc(r() * n, n * 0.3 + r() * n * 0.6, 1.5, 0, 7); x.fill(); }
  speck(x, n, r, 1200, "#000000", "#ffffff", 0.02, 0.06, 1, 2);
}, [1, 1]);

const std = (o: THREE.MeshStandardMaterialParameters) => new THREE.MeshStandardMaterial(o);
const matCache = new Map<string, THREE.Material>();
export function mat(key: string, make: () => THREE.Material): THREE.Material { const m = matCache.get(key); if (m) return m; const n = make(); matCache.set(key, n); return n; }
export const skinMat = (c: string) => mat("skin" + c, () => std({ color: c, roughness: 0.62, metalness: 0 }));
export const clothMat = (c: string, worn = 0) => mat(`cl${c}${worn}`, () => std({ color: "#ffffff", map: clothTex(c, worn), roughness: 0.95 }));
export const furMat = (c: string) => mat("fur" + c, () => { const t = furTex(c); return std({ color: "#ffffff", map: t, bumpMap: t, bumpScale: 0.6, roughness: 1 }); });
export const plainMat = (c: string, rough = 0.8, metal = 0) => mat(`p${c}${rough}${metal}`, () => std({ color: c, roughness: rough, metalness: metal }));
export const basicMat = (c: string) => mat("b" + c, () => new THREE.MeshBasicMaterial({ color: c }));

export const GEO = {
  sphere: new THREE.SphereGeometry(1, 28, 20),
  sphereLo: new THREE.SphereGeometry(1, 14, 10),
  capsule: new THREE.CapsuleGeometry(1, 1, 6, 14),
  box: new THREE.BoxGeometry(1, 1, 1),
  cyl: new THREE.CylinderGeometry(1, 1, 1, 18),
  lidTop: new THREE.SphereGeometry(1, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2),
  hairCap: new THREE.SphereGeometry(1, 28, 14, 0, Math.PI * 2, 0, Math.PI * 0.55),
  arc: new THREE.TorusGeometry(1, 0.2, 6, 18, Math.PI),
  cone: new THREE.ConeGeometry(1, 1, 16),
};
type MeshP = { g: THREE.BufferGeometry; m: THREE.Material; p?: [number, number, number]; r?: [number, number, number]; s?: [number, number, number] | number; shadow?: boolean };
export const M: React.FC<MeshP> = ({ g, m, p, r, s, shadow = true }) => (
  <mesh geometry={g} material={m} position={p} rotation={r} scale={typeof s === "number" ? [s, s, s] : s} castShadow={shadow} receiveShadow />
);

// a limb segment hanging down from its joint (local -y)
const Seg: React.FC<{ len: number; r0: number; r1?: number; m: THREE.Material }> = ({ len, r0, r1, m }) => (
  <mesh geometry={GEO.capsule} material={m} position={[0, -len / 2, 0]} scale={[(r0 + (r1 ?? r0)) / 2, Math.max(0.001, len / 2 - r0 * 0.3), (r0 + (r1 ?? r0)) / 2]} castShadow receiveShadow />
);

// ------------------------------------------------------------------ caps
const capGeo = (() => {
  const pts = [[0.0, 0.074], [0.035, 0.072], [0.064, 0.064], [0.084, 0.048], [0.094, 0.026], [0.098, 0.004], [0.098, 0.0]].map(([a, b]) => new THREE.Vector2(a, b));
  return new THREE.LatheGeometry(pts, 32);
})();
export const capMat = (c: string) => mat("cap" + c, () => std({ color: "#ffffff", map: capTex(c), roughness: 0.9, side: THREE.DoubleSide }));
export const Cap: React.FC<{ color: string; p?: [number, number, number]; r?: [number, number, number]; s?: number }> = ({ color, p, r, s = 1 }) => (
  <mesh geometry={capGeo} material={capMat(color)} position={p} rotation={r} scale={s} castShadow receiveShadow />
);
export const CAP_COLORS = ["#b8242a", "#2a4a9a", "#2a7a3a", "#d8a820", "#e8e4d8", "#d86a20", "#6a2a7a", "#d84a7a", "#1a6a7a", "#8a2a2a"];

// ------------------------------------------------------------------ human
export type HLook = {
  skin: string; hair: string; hairStyle: "short" | "bun" | "kid" | "kidgirl" | "bald";
  top: string; topStyle: "kurta" | "blouse" | "shirt" | "frock"; bottom: string; bottomStyle: "dhoti" | "saree" | "shorts" | "pants";
  pallu?: string; stubble?: string; moustache?: string; cap?: string; chappal?: "torn" | "plain"; worn?: number; bindi?: boolean; lip?: string;
};
export type HPose = {
  walk: number; phase: number; armL: [number, number]; armR: [number, number]; elbowL: number; elbowR: number;
  headYaw: number; headPitch: number; headRoll: number; spine: number; sit: number;
  eyes: number; brow: number; anger: number; mouth: number; smile: number; tear: number; lookX: number; lookY: number;
  capOnHead?: boolean; handR?: React.ReactNode; handL?: React.ReactNode;
};
export const hRest = (): HPose => ({ walk: 0, phase: 0, armL: [0, 0.1], armR: [0, -0.1], elbowL: -0.15, elbowR: -0.15, headYaw: 0, headPitch: 0, headRoll: 0,
  spine: 0, sit: 0, eyes: 1, brow: 0, anger: 0, mouth: 0, smile: 0.1, tear: 0, lookX: 0, lookY: 0, capOnHead: true });

const HeadR: React.FC<{ look: HLook; p: HPose }> = ({ look, p }) => {
  const sk = skinMat(look.skin);
  const lip = plainMat(look.lip ?? "#6e3a32", 0.5);
  const lid = (open: number) => lerp(1.62, -0.38, clamp(open));
  return (
    <group>
      <M g={GEO.sphere} m={sk} s={[0.104, 0.124, 0.114]} />
      <M g={GEO.sphere} m={sk} p={[0, -0.056, 0.028]} s={[0.086, 0.074, 0.088]} />
      {/* nose */}
      <M g={GEO.sphere} m={sk} p={[0, -0.006, 0.108]} r={[0.25, 0, 0]} s={[0.015, 0.03, 0.018]} />
      <M g={GEO.sphere} m={sk} p={[0, -0.028, 0.114]} s={[0.019, 0.013, 0.015]} />
      {/* ears */}
      {[-1, 1].map((s) => <M key={s} g={GEO.sphere} m={sk} p={[s * 0.103, -0.005, -0.006]} s={[0.016, 0.03, 0.021]} />)}
      {/* eyes: sclera, iris, pupil, catch-light, eyelid; brows */}
      {[-1, 1].map((s) => (
        <group key={s} position={[s * 0.037, 0.016, 0.09]}>
          <M g={GEO.sphereLo} m={plainMat("#ece4da", 0.3)} s={0.0165} shadow={false} />
          <M g={GEO.sphereLo} m={plainMat("#2c170a", 0.2)} p={[p.lookX * 0.005, p.lookY * 0.004, 0.0128]} s={[0.0088, 0.0088, 0.0045]} shadow={false} />
          <M g={GEO.sphereLo} m={basicMat("#050302")} p={[p.lookX * 0.005, p.lookY * 0.004, 0.0158]} s={[0.0042, 0.0042, 0.002]} shadow={false} />
          <M g={GEO.sphereLo} m={basicMat("#ffffff")} p={[p.lookX * 0.005 - 0.003, p.lookY * 0.004 + 0.003, 0.0168]} s={0.0013} shadow={false} />
          <M g={GEO.lidTop} m={sk} r={[lid(p.eyes), 0, 0]} s={0.0178} shadow={false} />
          {p.tear > 0 ? <M g={GEO.box} m={mat("tear", () => std({ color: "#d8e8f0", roughness: 0.02, metalness: 0.1, transparent: true, opacity: 0.55 }))} p={[s * 0.004, -0.014 - 0.03 * p.tear, 0.012 - 0.006 * p.tear]} r={[0.25, 0, 0]} s={[0.004, 0.06 * p.tear, 0.002]} shadow={false} /> : null}
          <M g={GEO.box} m={plainMat(look.hair === "#d8d4cc" ? "#8a8278" : "#1a120c", 0.9)} p={[0, 0.034 + p.brow * 0.005 - p.anger * 0.006, 0.012]} r={[0, 0, s * (0.38 * p.anger - 0.42 * p.brow)]} s={[0.03, 0.0055, 0.008]} shadow={false} />
        </group>
      ))}
      {/* mouth */}
      {p.mouth > 0.08 ? (
        <group position={[0, -0.066, 0.1]}>
          <M g={GEO.sphereLo} m={basicMat("#2a0c0c")} s={[0.02 + 0.004 * Math.abs(p.smile), 0.004 + 0.016 * p.mouth, 0.008]} shadow={false} />
          <M g={GEO.arc} m={lip} p={[0, 0.002 + 0.008 * p.mouth, 0.002]} s={[0.022, 0.008, 0.01]} shadow={false} />
          <M g={GEO.arc} m={lip} r={[0, 0, Math.PI]} p={[0, -0.002 - 0.012 * p.mouth, 0.002]} s={[0.022, 0.008, 0.01]} shadow={false} />
        </group>
      ) : (
        <M g={GEO.arc} m={lip} p={[0, -0.066 - (p.smile >= 0 ? 0.006 : -0.004) * Math.abs(p.smile), 0.101]} r={[0, 0, p.smile >= 0 ? Math.PI : 0]} s={[0.024, 0.006 + 0.01 * Math.abs(p.smile), 0.01]} shadow={false} />
      )}
      {look.stubble ? <M g={GEO.sphere} m={mat("stub" + look.stubble, () => std({ color: look.stubble, roughness: 1, transparent: true, opacity: 0.55, depthWrite: false }))} p={[0, -0.06, 0.03]} s={[0.09, 0.079, 0.092]} shadow={false} /> : null}
      {look.moustache ? <M g={GEO.capsule} m={plainMat(look.moustache, 1)} p={[0, -0.047, 0.106]} r={[0, 0, Math.PI / 2]} s={[0.007, 0.02, 0.008]} shadow={false} /> : null}
      {look.bindi ? <M g={GEO.sphereLo} m={basicMat("#b0101a")} p={[0, 0.05, 0.107]} s={[0.005, 0.005, 0.002]} shadow={false} /> : null}
      {/* hair */}
      {look.hairStyle !== "bald" ? <M g={GEO.hairCap} m={furMat(look.hair)} p={[0, 0.02, -0.012]} r={[-0.5, 0, 0]} s={[0.112, 0.118, 0.124]} /> : null}
      {look.hairStyle === "bun" ? <M g={GEO.sphere} m={furMat(look.hair)} p={[0, 0.0, -0.13]} s={[0.05, 0.045, 0.045]} /> : null}
      {look.hairStyle === "kidgirl" ? [-1, 1].map((s) => <M key={s} g={GEO.capsule} m={furMat(look.hair)} p={[s * 0.09, -0.08, -0.06]} s={[0.022, 0.06, 0.022]} />) : null}
      {look.hairStyle === "kid" ? <M g={GEO.sphere} m={furMat(look.hair)} p={[0, 0.085, 0.06]} r={[0.7, 0, 0]} s={[0.085, 0.03, 0.05]} /> : null}
      {look.cap && p.capOnHead !== false ? <Cap color={look.cap} p={[0, 0.07, -0.01]} r={[-0.18, 0, 0]} /> : null}
    </group>
  );
};

const Foot: React.FC<{ look: HLook; side: number }> = ({ look, side }) => (
  <group position={[0, -0.02, 0.035]}>
    <M g={GEO.sphere} m={skinMat(look.skin)} p={[0, -0.01, 0.02]} s={[0.042, 0.03, 0.105]} />
    {look.chappal ? (
      <group position={[0, -0.04, 0.02]}>
        {look.chappal === "torn" ? (
          <>
            <M g={GEO.box} m={plainMat("#5a4a3c", 0.9)} p={[0, 0, 0.075]} r={[0, 0.08 * side, 0]} s={[0.1, 0.016, 0.12]} />
            <M g={GEO.box} m={plainMat("#5a4a3c", 0.9)} p={[0.015 * side, -0.002, -0.075]} r={[0, -0.16 * side, 0.05]} s={[0.09, 0.014, 0.12]} />
            <M g={GEO.box} m={plainMat("#4a3020", 0.8)} p={[-0.03 * side, 0.03, 0.05]} r={[0.2, 0, 0.9 * side]} s={[0.01, 0.05, 0.012]} />
            <M g={GEO.box} m={plainMat("#4a3020", 0.8)} p={[0.05 * side, 0.004, 0.02]} r={[0.1, 0.6, 1.4]} s={[0.01, 0.045, 0.012]} />
          </>
        ) : (
          <>
            <M g={GEO.box} m={plainMat("#3a2a20", 0.9)} s={[0.1, 0.014, 0.25]} />
            {[-1, 1].map((k) => <M key={k} g={GEO.box} m={plainMat("#5a3a24", 0.8)} p={[k * 0.03, 0.03, 0.05]} r={[0.2, 0, -k * 0.9]} s={[0.01, 0.05, 0.012]} />)}
          </>
        )}
      </group>
    ) : null}
  </group>
);

// A proportioned person, ~1.75 m at scale 1. Origin at the feet, facing +z.
export const Human: React.FC<{ look: HLook; p: HPose }> = ({ look, p }) => {
  const top = clothMat(look.top, look.worn ?? 0);
  const bot = clothMat(look.bottom, look.worn ?? 0);
  const sk = skinMat(look.skin);
  const swing = Math.sin(p.phase) * 0.45 * p.walk;
  const bob = Math.abs(Math.cos(p.phase)) * 0.025 * p.walk;
  const hipY = lerp(0.88, 0.2, p.sit);
  const legCloth = look.bottomStyle === "dhoti" || look.bottomStyle === "pants" || look.bottomStyle === "saree";
  const longSleeve = look.topStyle === "kurta" || look.topStyle === "shirt";
  const skirt = look.bottomStyle === "saree" || look.topStyle === "frock" || look.topStyle === "kurta";
  const skirtLen = look.bottomStyle === "saree" ? lerp(0.86, 0.22, p.sit) : look.topStyle === "frock" ? lerp(0.42, 0.18, p.sit) : lerp(0.5, 0.16, p.sit);
  const skirtMat = look.bottomStyle === "saree" ? bot : top;
  return (
    <group position={[0, bob, 0]}>
      {/* legs */}
      {[-1, 1].map((s) => {
        const th = -2.2 * p.sit + (s < 0 ? swing : -swing);
        const kn = 2.1 * p.sit + p.walk * 0.55 * Math.max(0, Math.sin(p.phase + (s < 0 ? 0 : Math.PI)));
        return (
          <group key={s} position={[s * 0.09, hipY, 0]} rotation={[th, 0, s * 0.03]}>
            <Seg len={0.42} r0={legCloth ? 0.078 : 0.068} r1={legCloth ? 0.07 : 0.06} m={legCloth || look.bottomStyle === "shorts" ? bot : sk} />
            <group position={[0, -0.42, 0]} rotation={[kn, 0, 0]}>
              <Seg len={0.4} r0={0.052} r1={0.042} m={legCloth && look.bottomStyle !== "dhoti" ? bot : sk} />
              {look.bottomStyle === "dhoti" ? <mesh material={bot} position={[0, -0.1, 0]} castShadow receiveShadow><cylinderGeometry args={[0.072, 0.082, 0.22, 14, 1, true]} /></mesh> : null}
              <group position={[0, -0.4, 0]} rotation={[-(th + kn) * 0.6, 0, 0]}><Foot look={look} side={s} /></group>
            </group>
          </group>
        );
      })}
      {/* pelvis + upper body */}
      <group position={[0, hipY, 0]}>
        <M g={GEO.sphere} m={look.bottomStyle === "shorts" || look.bottomStyle === "dhoti" || look.bottomStyle === "pants" ? bot : skirtMat} p={[0, -0.03, 0]} s={[0.16, 0.12, 0.11]} />
        {skirt ? (
          <mesh material={skirtMat} position={[0, 0.08 - skirtLen / 2, 0.01]} rotation={[swing * 0.08 - p.sit * 0.35, 0, 0]} scale={[1, skirtLen, 1]} castShadow receiveShadow>
            <cylinderGeometry args={[0.165, look.bottomStyle === "saree" ? 0.23 : 0.24, 1, 22, 1, true]} />
          </mesh>
        ) : null}
        <group rotation={[p.spine, 0, 0]}>
          <M g={GEO.capsule} m={top} p={[0, 0.17, 0]} s={[0.135, 0.09, 0.095]} />
          <M g={GEO.sphere} m={top} p={[0, 0.36, 0]} s={[0.172, 0.2, 0.108]} />
          <M g={GEO.capsule} m={top} p={[0, 0.47, -0.005]} r={[0, 0, Math.PI / 2]} s={[0.06, 0.1, 0.07]} />
          {look.pallu ? <M g={GEO.box} m={clothMat(look.pallu)} p={[0.02, 0.3, 0.07]} r={[0.1, 0, 0.75]} s={[0.12, 0.55, 0.03]} /> : null}
          {look.pallu ? <M g={GEO.box} m={clothMat(look.pallu)} p={[-0.13, 0.3, -0.06]} r={[-0.1, 0, 0.1]} s={[0.1, 0.5, 0.02]} /> : null}
          {/* arms */}
          {[-1, 1].map((s) => {
            const arm = s < 0 ? p.armL : p.armR; const el = s < 0 ? p.elbowL : p.elbowR;
            return (
              <group key={s} position={[s * 0.18, 0.49, 0]} rotation={[arm[0] + (s < 0 ? -swing : swing) * 0.7, 0, arm[1]]}>
                <M g={GEO.sphere} m={top} s={[0.048, 0.05, 0.048]} />
                <Seg len={0.29} r0={0.044} r1={0.039} m={top} />
                <group position={[0, -0.29, 0]} rotation={[el, 0, 0]}>
                  <Seg len={0.26} r0={0.037} r1={0.032} m={longSleeve ? top : sk} />
                  <group position={[0, -0.27, 0.0]}>
                    <M g={GEO.sphere} m={sk} p={[0, -0.03, 0.005]} s={[0.032, 0.045, 0.018]} />
                    <M g={GEO.capsule} m={sk} p={[s * 0.022, -0.02, 0.016]} r={[0.5, 0, -s * 0.5]} s={[0.009, 0.02, 0.009]} />
                    <group position={[0, -0.07, 0.02]}>{s < 0 ? p.handL : p.handR}</group>
                  </group>
                </group>
              </group>
            );
          })}
          {/* neck + head */}
          <M g={GEO.cyl} m={sk} p={[0, 0.58, 0]} s={[0.045, 0.1, 0.045]} />
          <group position={[0, 0.72, 0.01]} rotation={[p.headPitch, p.headYaw, p.headRoll]}>
            <HeadR look={look} p={p} />
          </group>
        </group>
      </group>
    </group>
  );
};

// ------------------------------------------------------------------ macaque
export type MLook = { fur: string; furLow: string; chest: string; face: string; scar?: boolean };
export type MPose = {
  lean: number; headYaw: number; headPitch: number; headTilt: number;
  armL: [number, number]; armR: [number, number]; elbowL: number; elbowR: number;
  eyes: number; brow: number; mouth: number; grin: number; tail: number;
  capWorn?: string | null; capAskew?: number; capOverEyes?: boolean; capHeld?: string | null;
};
export const mRest = (): MPose => ({ lean: 0.15, headYaw: 0, headPitch: 0, headTilt: 0, armL: [-0.5, 0.15], armR: [-0.5, -0.15], elbowL: -0.7, elbowR: -0.7,
  eyes: 1, brow: 0, mouth: 0, grin: 0, tail: 0 });

// a rhesus macaque sitting on its haunches, ~0.45 m tall. Origin at the seat, facing +z.
export const Monkey: React.FC<{ look: MLook; p: MPose }> = ({ look, p }) => {
  const fur = furMat(look.fur), low = furMat(look.furLow), chest = furMat(look.chest);
  const face = skinMat(look.face);
  const lid = lerp(1.62, -0.38, clamp(p.eyes));
  return (
    <group>
      <M g={GEO.sphere} m={low} p={[0, 0.07, -0.02]} s={[0.1, 0.085, 0.11]} />
      {/* hind legs folded: knees up in front */}
      {[-1, 1].map((s) => (
        <group key={s} position={[s * 0.065, 0.06, 0.03]} rotation={[-1.25, 0, s * 0.18]}>
          <Seg len={0.12} r0={0.035} r1={0.028} m={low} />
          <group position={[0, -0.12, 0]} rotation={[2.3, 0, 0]}>
            <Seg len={0.11} r0={0.024} r1={0.02} m={low} />
            <M g={GEO.sphere} m={skinMat("#5a4038")} p={[0, -0.115, 0.02]} s={[0.022, 0.014, 0.04]} />
          </group>
        </group>
      ))}
      {/* tail hanging over the branch */}
      <group position={[0, 0.05, -0.11]}>
        {Array.from({ length: 9 }).map((_, k) => {
          const a = 0.35 + k * 0.17; const sway = Math.sin(p.tail + k * 0.5) * 0.02 * k;
          return <M key={k} g={GEO.sphereLo} m={low} p={[sway, -Math.sin(a) * 0.03 * k * 1.1, -0.02 - Math.cos(a) * 0.025 * k]} s={0.016 - k * 0.001} />;
        })}
      </group>
      <group position={[0, 0.07, 0]} rotation={[p.lean, 0, 0]}>
        <M g={GEO.sphere} m={fur} p={[0, 0.13, 0.0]} s={[0.088, 0.15, 0.082]} />
        <M g={GEO.sphere} m={chest} p={[0, 0.12, 0.045]} s={[0.068, 0.11, 0.048]} />
        {/* arms */}
        {[-1, 1].map((s) => {
          const arm = s < 0 ? p.armL : p.armR; const el = s < 0 ? p.elbowL : p.elbowR;
          return (
            <group key={s} position={[s * 0.07, 0.23, 0.01]} rotation={[arm[0], 0, arm[1]]}>
              <Seg len={0.125} r0={0.024} r1={0.02} m={fur} />
              <group position={[0, -0.125, 0]} rotation={[el, 0, 0]}>
                <Seg len={0.12} r0={0.019} r1={0.016} m={fur} />
                <M g={GEO.sphere} m={skinMat("#5e4840")} p={[0, -0.13, 0.004]} s={[0.019, 0.026, 0.011]} />
              </group>
            </group>
          );
        })}
        {p.capHeld ? <Cap color={p.capHeld} p={[0, 0.02, 0.13]} r={[-0.35, 0.3, 0.15]} s={0.9} /> : null}
        {/* head */}
        <group position={[0, 0.3, 0.02]} rotation={[p.headPitch, p.headYaw, p.headTilt]}>
          <M g={GEO.sphere} m={fur} s={[0.066, 0.064, 0.066]} />
          <M g={GEO.sphere} m={fur} p={[0, -0.012, 0.006]} s={[0.074, 0.066, 0.058]} />
          <M g={GEO.sphere} m={face} p={[0, -0.006, 0.048]} s={[0.047, 0.056, 0.03]} />
          <M g={GEO.sphere} m={skinMat(look.face === "#d48a7a" ? "#b87264" : "#a86a5c")} p={[0, 0.028, 0.06]} s={[0.046, 0.014, 0.022]} />
          {[-1, 1].map((s) => (
            <group key={s} position={[s * 0.02, 0.012, 0.071]}>
              <M g={GEO.sphereLo} m={plainMat("#4a2a0e", 0.12)} s={0.0105} shadow={false} />
              <M g={GEO.sphereLo} m={basicMat("#060302")} p={[0, 0, 0.008]} s={[0.0048, 0.0048, 0.003]} shadow={false} />
              <M g={GEO.sphereLo} m={basicMat("#ffffff")} p={[-0.0025, 0.0028, 0.0102]} s={0.0012} shadow={false} />
              <M g={GEO.lidTop} m={skinMat(look.face === "#d48a7a" ? "#dc9a8a" : "#cc8e80")} r={[lid, 0, 0]} s={0.0114} shadow={false} />
              <M g={GEO.box} m={plainMat("#7a5a48", 1)} p={[0, 0.016 + p.brow * 0.003, 0.004]} r={[0, 0, s * (-0.4 * p.brow)]} s={[0.018, 0.004, 0.006]} shadow={false} />
            </group>
          ))}
          <M g={GEO.sphere} m={face} p={[0, -0.028, 0.064]} s={[0.03, 0.026, 0.022]} />
          <M g={GEO.sphere} m={face} p={[0, -0.006, 0.074]} s={[0.012, 0.022, 0.01]} />
          {[-1, 1].map((s) => <M key={s} g={GEO.sphereLo} m={basicMat("#3a1c16")} p={[s * 0.0045, -0.016, 0.0855]} r={[0, 0, s * 0.5]} s={[0.0014, 0.0028, 0.001]} shadow={false} />)}
          <M g={GEO.sphereLo} m={basicMat("#2a0c0a")} p={[0, -0.044, 0.082]} s={[0.016 + 0.004 * p.grin, 0.0018 + 0.012 * Math.max(p.mouth, p.grin * 0.6), 0.008]} shadow={false} />
          {p.grin > 0.2 ? <M g={GEO.box} m={plainMat("#f0eadc", 0.3)} p={[0, -0.04, 0.089]} s={[0.022, 0.005, 0.003]} shadow={false} /> : null}
          {[-1, 1].map((s) => <M key={s} g={GEO.sphere} m={face} p={[s * 0.066, 0.004, -0.004]} s={[0.011, 0.02, 0.019]} />)}
          {look.scar ? <M g={GEO.box} m={plainMat("#e8c8b8", 0.6)} p={[0.024, 0.03, 0.068]} r={[0, 0, 0.8]} s={[0.003, 0.03, 0.003]} shadow={false} /> : null}
          {p.capWorn ? <Cap color={p.capWorn} p={p.capOverEyes ? [0, 0.012, 0.018] : [0, 0.035, -0.006]} r={p.capOverEyes ? [0.55, 0, 0.1] : [-0.15, 0, p.capAskew ?? 0]} s={0.82} /> : null}
        </group>
      </group>
    </group>
  );
};

// ------------------------------------------------------------------ foliage
type Blob = { c: [number, number, number]; r: number; n: number };
const LEAF_GREENS = ["#3d6a28", "#4c7a30", "#2e5a22", "#5a8a36", "#44702c", "#6a8a3a"];
export function useLeaves(blobs: Blob[], seed: number, size = 0.16): THREE.InstancedMesh {
  return useMemo(() => {
    const r = rng(seed);
    const total = blobs.reduce((a, b) => a + b.n, 0);
    const geo = new THREE.PlaneGeometry(size * 0.62, size);
    const tex = leafTex();
    const m = new THREE.MeshStandardMaterial({ map: tex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.75 });
    const mesh = new THREE.InstancedMesh(geo, m, total);
    mesh.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: tex, alphaTest: 0.5 });
    const o = new THREE.Object3D(); const col = new THREE.Color();
    let i = 0;
    for (const b of blobs) for (let k = 0; k < b.n; k++) {
      const u = r() * 2 - 1, th = r() * Math.PI * 2, rad = b.r * (0.55 + 0.45 * Math.sqrt(r()));
      const d = V3(Math.sqrt(1 - u * u) * Math.cos(th), u * 0.72, Math.sqrt(1 - u * u) * Math.sin(th));
      o.position.set(b.c[0] + d.x * rad, b.c[1] + d.y * rad, b.c[2] + d.z * rad);
      o.lookAt(o.position.x + d.x + (r() - 0.5), o.position.y + d.y + 0.6 + (r() - 0.5), o.position.z + d.z + (r() - 0.5));
      o.rotateZ(r() * Math.PI * 2);
      const s = 0.75 + r() * 0.6; o.scale.set(s, s, s);
      o.updateMatrix(); mesh.setMatrixAt(i, o.matrix);
      col.set(LEAF_GREENS[Math.floor(r() * LEAF_GREENS.length)]).multiplyScalar(0.85 + r() * 0.3); mesh.setColorAt(i, col);
      i++;
    }
    mesh.instanceMatrix.needsUpdate = true; if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.castShadow = true; mesh.receiveShadow = true; mesh.computeBoundingSphere();
    return mesh;
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps
}
export function useGrass(n: number, seed: number, area: (r: () => number) => [number, number] | null, h = 0.28, tint = "#7a8a40"): THREE.InstancedMesh {
  return useMemo(() => {
    const r = rng(seed);
    const geo = new THREE.PlaneGeometry(0.3, h); geo.translate(0, h / 2, 0);
    const tex = grassTex();
    const m = new THREE.MeshStandardMaterial({ map: tex, alphaTest: 0.45, side: THREE.DoubleSide, roughness: 0.9, color: tint });
    const mesh = new THREE.InstancedMesh(geo, m, n);
    const o = new THREE.Object3D(); const col = new THREE.Color();
    let i = 0, guard = 0;
    while (i < n && guard++ < n * 20) {
      const pt = area(r); if (!pt) continue;
      o.position.set(pt[0], 0, pt[1]); o.rotation.set(0, r() * Math.PI, 0); const s = 0.6 + r() * 0.9; o.scale.set(s, s, s);
      o.updateMatrix(); mesh.setMatrixAt(i, o.matrix);
      col.setHSL(0.16 + r() * 0.08, 0.35 + r() * 0.2, 0.5 + r() * 0.2); mesh.setColorAt(i, col); i++;
    }
    mesh.count = i;
    mesh.instanceMatrix.needsUpdate = true; if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.receiveShadow = true; mesh.computeBoundingSphere();
    return mesh;
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps
}

// a tapered cylinder from a to b
export const Branch: React.FC<{ a: [number, number, number]; b: [number, number, number]; r0: number; r1: number; m: THREE.Material }> = ({ a, b, r0, r1, m }) => {
  const { pos, quat, len } = useMemo(() => {
    const A = V3(...a), B = V3(...b); const d = B.clone().sub(A); const len = d.length();
    const quat = new THREE.Quaternion().setFromUnitVectors(V3(0, 1, 0), d.normalize());
    return { pos: A.clone().add(B).multiplyScalar(0.5), quat, len };
  }, [a, b]);
  return (
    <mesh position={pos} quaternion={quat} material={m} castShadow receiveShadow>
      <cylinderGeometry args={[r1, r0, len, 14, 1]} />
    </mesh>
  );
};

// ------------------------------------------------------------------ sky + image-based light
export type SkyPreset = { sunElev: number; sunAz: number; turbidity: number; rayleigh: number; exposure: number; env: number };
export const SkyEnv: React.FC<{ preset: SkyPreset; name: string }> = ({ preset, name }) => {
  const { gl, scene } = useThree();
  const sun = useMemo(() => { const phi = THREE.MathUtils.degToRad(90 - preset.sunElev), th = THREE.MathUtils.degToRad(preset.sunAz); return new THREE.Vector3().setFromSphericalCoords(1, phi, th); }, [name]);  // eslint-disable-line react-hooks/exhaustive-deps
  const make = () => { const s = new Sky(); s.scale.setScalar(900); const u = s.material.uniforms;
    u.turbidity.value = preset.turbidity; u.rayleigh.value = preset.rayleigh; u.mieCoefficient.value = 0.005; u.mieDirectionalG.value = 0.82; u.sunPosition.value.copy(sun); return s; };
  const sky = useMemo(() => { const s = make(); s.material.fragmentShader = s.material.fragmentShader.replace("gl_FragColor = vec4( retColor, 1.0 );", "gl_FragColor = vec4( retColor * 0.62, 1.0 );"); return s; }, [name]);  // eslint-disable-line react-hooks/exhaustive-deps
  const env = useMemo(() => { const pm = new THREE.PMREMGenerator(gl); const sc = new THREE.Scene(); sc.add(make()); const rt = pm.fromScene(sc, 0.02); pm.dispose(); return rt.texture; }, [name]);  // eslint-disable-line react-hooks/exhaustive-deps
  scene.environment = env; scene.environmentIntensity = preset.env; gl.toneMappingExposure = preset.exposure;
  return <primitive object={sky} />;
};
export const sunDir = (p: SkyPreset) => { const phi = THREE.MathUtils.degToRad(90 - p.sunElev), th = THREE.MathUtils.degToRad(p.sunAz); return new THREE.Vector3().setFromSphericalCoords(1, phi, th); };

export const nightSkyMat = () => new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false,
  uniforms: { top: { value: new THREE.Color("#030612") }, bottom: { value: new THREE.Color("#1a2440") } },
  vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ",
  fragmentShader: "uniform vec3 top; uniform vec3 bottom; varying vec3 vP; float h1(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,45.164)))*43758.5453);} " +
    "void main(){ float h = clamp(vP.y*1.4+0.08,0.0,1.0); vec3 c = mix(bottom, top, h); vec3 q = floor(vP*300.0); float s = step(0.997, h1(q)) * smoothstep(0.05,0.35,vP.y); c += vec3(s*0.9); gl_FragColor = vec4(c,1.0);} ",
});
