import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { G, Look, Person, Pose, Toon, restPose } from "./Character";
import { rng, skyMat } from "./World";

// "सब कहते हैं, कबूतरों ने एक साथ उड़ने का फैसला किया…" (ReelAudio-68829): the pigeons-and-net tale from the farmer's side.
export const DURATION = 2421; // 80.7 s
const FPS = 30;
const END = DURATION / FPS;
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (x: number) => { const t = clamp(x); return t * t * (3 - 2 * t); };
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: number[], b: number[], t: number) => a.map((v, i) => lerp(v, b[i], t)) as [number, number, number];
const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

const SUBS: [number, number, string][] = [
  [0.0, 3.5, "सब कहते हैं, कबूतरों ने एक साथ उड़ने का फ़ैसला किया।"],
  [3.5, 8.14, "लेकिन सच ये है कि उस जाल की हर खूँटी किसान ने ही ढीली गाड़ी थी।"],
  [8.14, 12.62, "पिछले साल भी किसान ने खेती की थी, पर कबूतर सारी फ़सल चट कर गए।"],
  [12.62, 14.2, "सिर पर कर्ज़ चढ़ गया।"],
  [14.2, 16.4, "इस साल उसने दिन-रात पसीना बहाया।"],
  [16.4, 19.4, "कभी पानी की चिंता, कभी मौसम का डर।"],
  [19.4, 22.0, "तब जाकर खेत सुनहरी फ़सल से भर पाया।"],
  [22.0, 25.76, "पर तभी आसमान में फिर वही कबूतरों का झुंड मँडराने लगा।"],
  [25.76, 27.96, "मजबूर होकर उसने जाल बिछाया।"],
  [27.96, 30.4, "पर सोचो, उसने जाल ढीला क्यों छोड़ा?"],
  [30.4, 34.06, "क्योंकि वो कबूतरों को मारना नहीं, बस डराना चाहता था।"],
  [34.06, 36.78, "उसे सिर्फ़ अपनी मेहनत का फल चाहिए था।"],
  [36.78, 39.42, "वो जानता था कि कबूतर जाल में फँसेंगे,"],
  [39.42, 44.0, "लेकिन ढीली खूँटियाँ उन्हें मौका देंगी कि वो अपनी ताकत से निकल सकें।"],
  [44.0, 47.22, "सुबह कबूतर उतरे, जाल गिरा, सब घबरा गए।"],
  [47.22, 50.8, "राजा चिल्लाया, “घबराओ मत, सब एक साथ ऊपर उठो।”"],
  [50.8, 54.98, "सबने ज़ोर लगाया और वो ढीली खूँटियाँ ज़मीन से उखड़ गईं।"],
  [54.98, 57.5, "किसान कुछ दूर दौड़ा, फिर रुक गया।"],
  [57.5, 59.72, "हाथ खाली थे, पर दिल हल्का।"],
  [59.72, 63.04, "पूरी दुनिया ने कबूतरों की एकता पर ताली बजाई।"],
  [63.04, 64.8, "किसी ने किसान को नहीं देखा।"],
  [64.8, 68.9, "हमारे घरों में भी कोई चुपचाप हमारे लिए खूँटियाँ ढीली करता है।"],
  [68.9, 73.24, "हम अपनी जीत की ताली बटोरते हैं, पर पीछे का वो हाथ भूल जाते हैं।"],
  [73.24, 77.84, "कहीं तुम्हारी उड़ान के पीछे भी किसी का ढीला छोड़ा हुआ जाल तो नहीं?"],
  [77.84, 80.6, "ऐसी ही अनसुनी कहानियों के लिए मुझे follow करें।"],
];
const S = { truth: 3.5, last: 8.14, sweat: 14.2, worry: 16.4, grow: 19.4, flock: 22.0, spread: 25.76, why: 27.96, fruit: 34.06, pegs: 36.78,
  land: 44.0, drop: 45.34, king: 47.22, lift: 50.8, pop: 52.6, run: 54.98, light: 57.5, clap: 59.72, home: 64.8, hand: 68.9, crane: 73.24, cta: 77.84 };

// ------------------------------------------------------------------ looks
const FARMER: Look = { skin: "#a8724e", hair: "#e8902a", hairStyle: "turban", shirt: "#f2ede0", inner: "#e0d8c4", pants: "#f4f0e4", shoes: "#6a4424", face: true, moustache: "#1a1410" };
const BETI: Look = { skin: "#b67c56", hair: "#140e0c", hairStyle: "ponytail", shirt: "#e84a7a", inner: "#ffd0e0", pants: "#e84a7a", shoes: "#ffcc40", face: true };
const VILLAGERS: Look[] = [
  { skin: "#b07850", hair: "#1a1410", hairStyle: "short", shirt: "#3a7ab8", inner: "#eee", pants: "#3a3a48", shoes: "#5a3a22", face: true },
  { skin: "#c08a66", hair: "#120e0c", hairStyle: "bun", shirt: "#d8a030", inner: "#a03030", pants: "#d8a030", shoes: "#5a3a22", face: true },
  { skin: "#9a6a48", hair: "#e8e4dc", hairStyle: "receding", shirt: "#e8e0cc", inner: "#ccc", pants: "#7a6a5a", shoes: "#5a3a22", face: true, beard: "#e0dcd2" },
];

// ------------------------------------------------------------------ places
const NET = V(0, 0, -1.4);       // centre of the net in the field
const NET_W = 2.6, NET_D = 1.8;
const PEGS: [number, number][] = [[-1, -1], [0, -1], [1, -1], [-1, 1], [0, 1], [1, 1], [-1, 0], [1, 0]];
const HUT = V(-4.6, 0, 2.8);

// ------------------------------------------------------------------ a pigeon
const Pigeon: React.FC<{ flap: number; t: number; color?: string; king?: boolean; peck?: number; panic?: number }> = ({ flap, t, color = "#8a92a2", king, peck = 0, panic = 0 }) => {
  const wing = flap > 0 ? Math.sin(t * (18 + 10 * panic)) * 0.9 * flap : 0.15;
  const neck = color === "#8a92a2" ? "#5a7a7a" : color;
  return (
    <group>
      <Toon geom={G.sphere} color={color} position={[0, 0.12, 0]} scale={[0.09, 0.08, 0.14]} outline={0.006} />
      <group position={[0, 0.2 - peck * 0.08, 0.1 + peck * 0.04]} rotation={[peck * 0.9, 0, 0]}>
        <Toon geom={G.sphere} color={neck} scale={[0.06, 0.06, 0.06]} outline={0.006} />
        <mesh position={[0, -0.005, 0.07]} rotation={[Math.PI / 2, 0, 0]} scale={[0.015, 0.035, 0.015]}><coneGeometry args={[1, 1, 6]} /><meshToonMaterial color="#e8a040" /></mesh>
        {[-1, 1].map((s) => <mesh key={s} position={[s * 0.04, 0.015, 0.03]} scale={0.012}><sphereGeometry args={[1, 6, 6]} /><meshBasicMaterial color={panic > 0.3 ? "#fff" : "#c03a1a"} /></mesh>)}
        {king ? <group position={[0, 0.07, 0]}>{[0, 1, 2, 3, 4].map((k) => <mesh key={k} position={[Math.cos(k * 1.256) * 0.025, 0.015, Math.sin(k * 1.256) * 0.025]} scale={[0.008, 0.025, 0.008]}><coneGeometry args={[1, 1, 4]} /><meshStandardMaterial color="#ffd040" metalness={0.8} roughness={0.3} /></mesh>)}
          <mesh scale={[0.03, 0.01, 0.03]}><cylinderGeometry args={[1, 1, 1, 12]} /><meshStandardMaterial color="#ffd040" metalness={0.8} roughness={0.3} /></mesh></group> : null}
      </group>
      {[-1, 1].map((s) => (
        <group key={s} position={[s * 0.07, 0.15, 0]} rotation={[0, 0, s * (0.2 + wing)]}>
          <mesh position={[s * 0.1, 0, -0.02]} scale={[0.12, 0.012, 0.09]}><sphereGeometry args={[1, 10, 6]} /><meshToonMaterial color={king ? "#f4f4f4" : "#9aa2b2"} /></mesh>
        </group>
      ))}
      <mesh position={[0, 0.13, -0.16]} rotation={[-0.3, 0, 0]} scale={[0.06, 0.01, 0.07]}><sphereGeometry args={[1, 8, 6]} /><meshToonMaterial color="#5a6272" /></mesh>
      {[-1, 1].map((s) => <mesh key={s} position={[s * 0.03, 0.03, 0]} scale={[0.008, 0.04, 0.008]}><cylinderGeometry args={[1, 1, 1, 4]} /><meshToonMaterial color="#d8603a" /></mesh>)}
    </group>
  );
};

// the flock: 14 birds, one king; where each one is at time t
const FLOCK = (() => { const r = rng(31); return Array.from({ length: 14 }, (_, i) => ({ i, a: r() * Math.PI * 2, rad: 1.2 + r() * 1.6, h: 3.4 + r() * 1.4, sp: 0.5 + r() * 0.3,
  nx: (r() - 0.5) * (NET_W - 0.5), nz: (r() - 0.5) * (NET_D - 0.4), ph: r() * 6, color: r() < 0.25 ? "#a8a8b4" : "#8a92a2" })); })();

type Bird = { pos: [number, number, number]; yaw: number; flap: number; peck: number; panic: number; king: boolean; color: string };
function birdsAt(t: number, netY: number): Bird[] {
  return FLOCK.map((b) => {
    const king = b.i === 0;
    const circle = (cx: number, cz: number, h: number): Bird => {
      const a = b.a + t * b.sp;
      return { pos: [cx + Math.cos(a) * b.rad, h + 0.2 * Math.sin(t * 2 + b.ph), cz + Math.sin(a) * b.rad], yaw: -a, flap: 1, peck: 0, panic: 0, king, color: king ? "#f2f2f2" : b.color };
    };
    const onNet = (): [number, number, number] => [NET.x + b.nx, NET.y, NET.z + b.nz];
    if (t < S.truth) { const p = onNet(); return { pos: [p[0], netY + 0.05, p[2]], yaw: b.ph, flap: 1, peck: 0, panic: 0.5, king, color: king ? "#f2f2f2" : b.color }; }   // carrying the net away
    if (t >= S.last && t < S.sweat) {   // last year: feasting on the crop
      return { pos: [NET.x + b.nx * 1.4, 0, NET.z + b.nz * 1.6 + 0.6], yaw: b.ph, flap: 0, peck: Math.max(0, Math.sin(t * 9 + b.ph)), panic: 0, king, color: king ? "#f2f2f2" : b.color };
    }
    if (t >= S.flock && t < S.land) return circle(NET.x, NET.z, b.h);
    if (t >= S.land && t < S.lift) {
      const k = seg(t, S.land + b.ph * 0.05, S.land + 1.0 + b.ph * 0.05);
      const c = circle(NET.x, NET.z, b.h); const p = onNet();
      const pos = lerp3(c.pos, [p[0], 0, p[2]], k) as [number, number, number];
      const panic = t > S.drop ? 1 : 0;
      return { pos: [pos[0] + (panic ? 0.03 * Math.sin(t * 30 + b.ph) : 0), pos[1] + (panic ? 0.05 * Math.abs(Math.sin(t * 20 + b.ph)) : 0), pos[2]], yaw: king ? 0.5 : b.ph, flap: k < 1 ? 1 : panic, peck: k >= 1 && !panic ? Math.max(0, Math.sin(t * 9 + b.ph)) : 0, panic, king, color: king ? "#f2f2f2" : b.color };
    }
    if (t >= S.lift && t < S.clap + 3) { const p = onNet(); return { pos: [p[0], netY + 0.02, p[2]], yaw: 0, flap: 1, peck: 0, panic: 0.3, king, color: king ? "#f2f2f2" : b.color }; }
    return { pos: [0, -50, 0], yaw: 0, flap: 0, peck: 0, panic: 0, king, color: b.color };
  });
}

function netState(t: number): { y: number; show: boolean; spread: number; drift: [number, number] } {
  if (t < S.truth) { const k = clamp(t / S.truth); return { y: lerp(1.6, 4.2, k), show: true, spread: 1, drift: [0.8 * k, -0.5 * k] }; }
  if (t >= S.spread && t < S.land) return { y: 0.03, show: true, spread: seg(t, S.spread, S.spread + 1.6), drift: [0, 0] };
  if (t >= S.land && t < S.lift) return { y: t < S.drop ? 1.4 : lerp(1.4, 0.06, seg(t, S.drop, S.drop + 0.3)), show: t >= S.drop - 0.05, spread: 1, drift: [0, 0] };
  if (t >= S.lift && t < S.clap + 3) { const k = seg(t, S.pop, S.pop + 6); return { y: lerp(0.08, 6.5, k) + (t < S.pop ? 0.05 * Math.sin(t * 25) : 0), show: true, spread: 1, drift: [1.5 * k, -1.2 * k] }; }
  return { y: 0, show: false, spread: 0, drift: [0, 0] };
}

const netTex = (() => {
  if (typeof document === "undefined") return undefined;
  const c = document.createElement("canvas"); c.width = c.height = 256;
  const x = c.getContext("2d")!;
  x.clearRect(0, 0, 256, 256); x.strokeStyle = "rgba(230,220,190,0.95)"; x.lineWidth = 3;
  for (let i = 0; i <= 256; i += 21) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, 256); x.stroke(); x.beginPath(); x.moveTo(0, i); x.lineTo(256, i); x.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(2, 1.4); return t;
})();

const Net: React.FC<{ t: number }> = ({ t }) => {
  const n = netState(t);
  if (!n.show) return null;
  const wobble = n.y > 0.3 ? 0.08 * Math.sin(t * 3) : 0;
  return (
    <group position={[NET.x + n.drift[0], n.y, NET.z + n.drift[1]]} rotation={[-Math.PI / 2 + wobble, 0, 0.04 * Math.sin(t * 2)]} scale={[n.spread, n.spread, 1]}>
      <mesh><planeGeometry args={[NET_W, NET_D, 8, 6]} /><meshBasicMaterial map={netTex} transparent side={THREE.DoubleSide} depthWrite={false} /></mesh>
      <mesh><planeGeometry args={[NET_W + 0.04, NET_D + 0.04]} /><meshBasicMaterial color="#d8c8a0" wireframe /></mesh>
    </group>
  );
};

const Pegs: React.FC<{ t: number }> = ({ t }) => {
  if (!(t >= S.spread && t < S.clap + 3) && !(t >= S.truth && t < S.last)) return null;
  const n = netState(t);
  return (
    <group>
      {PEGS.map(([px, pz], k) => {
        const base: [number, number, number] = [NET.x + px * NET_W / 2, 0.06, NET.z + pz * NET_D / 2];
        const loose = 0.12 * Math.sin(t * 6 + k);   // a little loose, it wobbles
        let pos = base, rot: [number, number, number] = [loose * (t >= S.pegs && t < S.land ? 1 : 0.2), 0, 0];
        if (t >= S.pop) { const kk = seg(t, S.pop + k * 0.05, S.pop + 0.4 + k * 0.05); pos = [base[0] + n.drift[0] * kk, lerp(0.06, n.y - 0.15, kk), base[2] + n.drift[1] * kk]; rot = [kk * 2 + k, k, kk]; }
        return (
          <group key={k} position={pos} rotation={rot}>
            <Toon geom={G.cyl} color="#8a5a2e" scale={[0.03, 0.22, 0.03]} outline={0.006} />
            <mesh position={[0, 0.11, 0]} scale={0.04}><sphereGeometry args={[1, 8, 6]} /><meshToonMaterial color="#6a4020" /></mesh>
          </group>
        );
      })}
      {t >= S.pop && t < S.pop + 1.2 ? PEGS.map(([px, pz], k) => (   // dirt puffs where the pegs come out
        <mesh key={"d" + k} position={[NET.x + px * NET_W / 2, 0.08 + (t - S.pop) * 0.3, NET.z + pz * NET_D / 2]} scale={0.08 + (t - S.pop) * 0.2}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#8a6a4a" transparent opacity={0.6 * (1 - (t - S.pop) / 1.2)} /></mesh>
      )) : null}
    </group>
  );
};

// ------------------------------------------------------------------ field and village
function wheatGrowth(t: number): { h: number; gold: number; ruined: boolean } {
  if (t < S.last) return { h: 1, gold: 1, ruined: false };
  if (t < S.sweat) return { h: 0.35, gold: 0.4, ruined: true };
  if (t < S.grow) return { h: lerp(0.1, 0.4, seg(t, S.sweat, S.grow)), gold: 0, ruined: false };
  if (t < S.flock) return { h: lerp(0.4, 1, seg(t, S.grow, S.grow + 2.2)), gold: seg(t, S.grow + 0.5, S.grow + 2.4), ruined: false };
  return { h: 1, gold: 1, ruined: false };
}
const Field: React.FC<{ t: number }> = ({ t }) => {
  const stalks = useMemo(() => { const r = rng(5); const out: { x: number; z: number; h: number; lean: number }[] = [];
    for (let i = 0; i < 520; i++) { const x = -5 + r() * 10, z = -6 + r() * 5.4; if (Math.abs(x - NET.x) < NET_W / 2 + 0.2 && Math.abs(z - NET.z) < NET_D / 2 + 0.2) continue; out.push({ x, z, h: 0.7 + r() * 0.35, lean: (r() - 0.5) * 0.3 }); } return out; }, []);
  const g = wheatGrowth(t);
  const green = new THREE.Color("#6aa03a"), gold = new THREE.Color("#e8b84a"), dead = new THREE.Color("#8a7a4a");
  const col = g.ruined ? dead : green.clone().lerp(gold, g.gold);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -3]} receiveShadow><planeGeometry args={[11, 6.4]} /><meshToonMaterial color="#7a5a3a" /></mesh>
      {stalks.map((s, k) => {
        const h = s.h * g.h, sway = 0.08 * Math.sin(t * 1.5 + s.x * 0.7);
        return (
          <group key={k} position={[s.x, 0, s.z]} rotation={[0, 0, s.lean + sway]}>
            <mesh position={[0, h / 2, 0]}><cylinderGeometry args={[0.008, 0.012, h, 4]} /><meshToonMaterial color={col} /></mesh>
            {g.h > 0.5 && !g.ruined ? <mesh position={[0, h, 0]} scale={[0.025, 0.08, 0.025]}><sphereGeometry args={[1, 6, 5]} /><meshToonMaterial color={col} /></mesh> : null}
          </group>
        );
      })}
      {/* grain scattered under the net */}
      {t >= S.spread && t < S.lift ? Array.from({ length: 40 }).map((_, k) => <mesh key={k} position={[NET.x + ((k * 0.37) % 2.2) - 1.1, 0.012, NET.z + ((k * 0.61) % 1.5) - 0.75]} scale={0.02}><sphereGeometry args={[1, 5, 4]} /><meshToonMaterial color="#e8c060" /></mesh>) : null}
    </group>
  );
};
const Village: React.FC = () => (
  <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow><planeGeometry args={[60, 60]} /><meshToonMaterial color="#8aa04a" /></mesh>
    <group position={HUT}>
      <Toon geom={G.box} color="#c8a070" position={[0, 0.8, 0]} scale={[2.2, 1.6, 1.8]} outline={0.004} />
      <mesh position={[0, 1.9, 0]} rotation={[0, Math.PI / 4, 0]}><coneGeometry args={[1.9, 1.0, 4]} /><meshToonMaterial color="#c8a040" /></mesh>
      <Toon geom={G.box} color="#5a3a20" position={[0.4, 0.55, 0.91]} scale={[0.5, 1.0, 0.02]} outline={0} />
      <mesh position={[-0.5, 0.95, 0.91]}><planeGeometry args={[0.35, 0.35]} /><meshBasicMaterial color="#ffd080" /></mesh>
    </group>
    {[[4.5, -6.5], [-6.5, -4], [6.5, 1.5]].map(([x, z], k) => (
      <group key={k} position={[x, 0, z]}>
        <mesh position={[0, 1.2, 0]}><cylinderGeometry args={[0.15, 0.22, 2.4, 8]} /><meshToonMaterial color="#5a3a24" /></mesh>
        {[[0, 2.8, 0, 1.2], [0.6, 2.4, 0.2, 0.8], [-0.6, 2.5, -0.1, 0.85]].map(([a, b, c, r], j) => <Toon key={j} geom={G.sphere} color="#3a6a30" position={[a, b, c]} scale={r} outline={0.005} />)}
      </group>
    ))}
  </group>
);

// rupee signs circling the farmer's head (debt)
const Debt: React.FC<{ t: number; at: [number, number, number] }> = ({ t, at }) => {
  const tex = useMemo(() => {
    if (typeof document === "undefined") return undefined;
    const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d")!;
    x.fillStyle = "#c81a1a"; x.font = "900 100px 'Noto Sans Devanagari', sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText("₹", 64, 68);
    const tt = new THREE.CanvasTexture(c); tt.colorSpace = THREE.SRGBColorSpace; return tt;
  }, []);
  return <group position={at}>{Array.from({ length: 6 }).map((_, k) => {
    const a = t * 1.6 + k * (Math.PI / 3);
    return <mesh key={k} position={[Math.cos(a) * 0.45, 0.1 * Math.sin(t * 3 + k) + 0.2, Math.sin(a) * 0.45]} scale={0.22 * seg(t, S.last + 4.3, S.last + 4.8)}><planeGeometry /><meshBasicMaterial map={tex} transparent side={THREE.DoubleSide} /></mesh>;
  })}</group>;
};

// a dark cloud with lightning (fear of the weather)
const StormCloud: React.FC<{ t: number }> = ({ t }) => {
  const show = t >= S.worry + 1.2 && t < S.grow;
  if (!show) return null;
  const flash = Math.max(0, 1 - Math.abs(((t - S.worry) % 0.9) - 0.1) / 0.06);
  return (
    <group position={[0.5, 4.2, -3]}>
      {[[0, 0, 1.0], [0.9, -0.2, 0.8], [-0.9, -0.1, 0.85], [0.3, 0.4, 0.8]].map(([x, y, r], k) => <Toon key={k} geom={G.sphere} color="#4a4e5a" position={[x, y, 0]} scale={[r * 1.2, r * 0.7, r]} outline={0.004} />)}
      {flash > 0.2 ? <mesh position={[0.2, -1.4, 0.5]} rotation={[0, 0, 0.2]} scale={[0.06, 1.6, 0.02]}><boxGeometry /><meshBasicMaterial color="#fff8b0" /></mesh> : null}
      <pointLight position={[0, -1, 1]} color="#dfe8ff" intensity={flash * 30} distance={12} />
    </group>
  );
};

// ------------------------------------------------------------------ farmer and others
type Actor = { look: Look; pose: Pose; pos: [number, number, number]; yaw: number; s?: number; handR?: React.ReactNode; handL?: React.ReactNode };
const P = (f: (p: Pose) => void) => { const p = restPose(); f(p); return p; };
const Hoe: React.FC = () => (
  <group rotation={[0.3, 0, 0]}>
    <mesh position={[0, 0.25, 0]} scale={[0.015, 0.7, 0.015]}><cylinderGeometry args={[1, 1, 1, 6]} /><meshToonMaterial color="#8a5a2e" /></mesh>
    <Toon geom={G.box} color="#6a6e78" position={[0, 0.6, 0.06]} scale={[0.12, 0.03, 0.14]} outline={0.006} />
  </group>
);
const Mallet: React.FC = () => (
  <group><mesh position={[0, 0.1, 0]} scale={[0.012, 0.25, 0.012]}><cylinderGeometry args={[1, 1, 1, 6]} /><meshToonMaterial color="#8a5a2e" /></mesh>
    <Toon geom={G.cyl} color="#6a4424" position={[0, 0.22, 0]} rotation={[0, 0, Math.PI / 2]} scale={[0.04, 0.12, 0.04]} outline={0.006} /></group>
);

function actorsAt(t: number): Actor[] {
  const out: Actor[] = [];
  const f = restPose();
  f.smile = 0.2; f.brow = 0.4;
  let pos: [number, number, number] = [1.8, 0, 0.2], yaw = -Math.PI / 2;
  let handR: React.ReactNode;
  if (t < S.truth) { f.headPitch = -0.4; f.smile = 0.5; f.brow = 0.5; pos = [2.6, 0, 0.8]; yaw = -2.4; }   // watches them fly off with the net
  else if (t < S.last) {   // kneeling at a peg, loosening it
    f.sit = 1; f.armR = [-1.2, -0.1]; f.elbowR = -0.6 + 0.2 * Math.sin(t * 8); f.armL = [-1.0, 0.2]; f.elbowL = -0.4; f.headPitch = 0.5; f.smile = 0.35; f.lookY = -0.8;
    pos = [1.85, -0.18, 0.0]; yaw = -2.3;
    if (t > 6.0) { f.headPitch = -0.1; f.headYaw = 0.5; f.lookY = 0; f.smile = 0.45; f.eyes = 0.8; }
  } else if (t < S.sweat) {   // last year: sits on the ruined field, head in his hands
    f.sit = 1; f.armL = [-1.4, 0.4]; f.armR = [-1.4, -0.4]; f.elbowL = -2.0; f.elbowR = -2.0; f.headPitch = 0.5; f.eyes = 0.3; f.brow = 1; f.smile = -0.6;
    if (t < S.last + 2) { f.sit = 0; f.armL = [0, 0.1]; f.armR = [0, -0.1]; f.elbowL = 0.15; f.elbowR = 0.15; f.headPitch = 0.1; f.eyes = 1.1; f.mouthO = 0.8; f.brow = 0.6; }
    pos = [1.6, t < S.last + 2 ? 0 : -0.18, -0.2]; yaw = -2.0;
  } else if (t < S.worry) {   // sweat: swings the hoe
    const sw = Math.sin(t * 5);
    f.armR = [-1.6 + 1.0 * sw, -0.15]; f.armL = [-1.5 + 1.0 * sw, 0.15]; f.elbowR = -0.4; f.elbowL = -0.4; f.headPitch = 0.3; f.brow = 0.7; f.smile = -0.1;
    pos = [0.8, 0, -2.4]; yaw = 0.3; handR = <Hoe />;
  } else if (t < S.grow) {   // worry: looks at the sky, a pot of water
    f.headPitch = -0.45; f.brow = 1; f.eyes = 1.05; f.smile = -0.4; f.armR = [-0.9, -0.2]; f.elbowR = -1.0;
    pos = [0.4, 0, -2.0]; yaw = -0.3;
    handR = <Toon geom={G.sphere} color="#b0602a" position={[0, -0.05, 0.06]} scale={[0.12, 0.12, 0.12]} outline={0.006} />;
  } else if (t < S.flock) {  // the golden field: arms open, smile
    const k = seg(t, S.grow + 0.8, S.grow + 1.6);
    f.armL = [-0.4, 1.3 * k]; f.armR = [-0.4, -1.3 * k]; f.elbowL = -0.1; f.elbowR = -0.1; f.smile = 1; f.happyEyes = true; f.eyes = 0; f.headPitch = -0.2; f.blush = 0.5;
    pos = [0.2, 0, -1.0]; yaw = 0.2;
  } else if (t < S.spread) { f.headPitch = -0.5; f.brow = 1; f.eyes = 1.1; f.smile = -0.4; pos = [1.4, 0, 0.0]; yaw = -2.6; }   // the flock is back
  else if (t < S.why) {      // spreading the net
    f.armL = [-1.3, 0.6]; f.armR = [-1.3, -0.6]; f.elbowL = -0.2; f.elbowR = -0.2; f.headPitch = 0.4; f.brow = 0.8; f.smile = -0.2;
    pos = [NET.x, 0, NET.z + NET_D / 2 + 0.5]; yaw = Math.PI;
  } else if (t < S.fruit) {  // hammers a peg, softly, and leaves it loose
    f.sit = 1; f.armR = [-1.3 + 0.35 * Math.abs(Math.sin(t * 4)), -0.1]; f.elbowR = -0.8; f.headPitch = 0.45; f.smile = 0.3; f.lookY = -0.8;
    if (t > 30.4) { f.smile = 0.5; f.eyes = 0.7; }
    pos = [1.85, -0.18, 0.0]; yaw = -2.3; handR = <Mallet />;
  } else if (t < S.pegs) {   // a handful of grain: the fruit of his work
    f.armR = [-1.3, -0.1]; f.elbowR = -0.8; f.headPitch = 0.3; f.smile = 0.6; f.brow = 0.3; f.lookY = -0.6;
    pos = [0.9, 0, -0.4]; yaw = -2.0;
    handR = <group position={[0, 0.02, 0.03]}>{Array.from({ length: 8 }).map((_, k) => <mesh key={k} position={[((k * 0.37) % 0.08) - 0.04, 0.01 * (k % 3), ((k * 0.53) % 0.06) - 0.03]} scale={0.014}><sphereGeometry args={[1, 5, 4]} /><meshToonMaterial color="#e8c060" /></mesh>)}<pointLight color="#ffd060" intensity={0.8} distance={0.6} /></group>;
  } else if (t < S.land) {   // dusk: he goes home, glancing back at the loose pegs
    const k = seg(t, S.pegs + 1, S.land);
    f.walk = 1; f.phase = t * 6; f.headYaw = 0.6 * Math.sin(t * 0.6); f.smile = 0.3;
    pos = [lerp(1.5, HUT.x + 1.5, k), 0, lerp(0.2, HUT.z - 0.5, k)]; yaw = Math.atan2(HUT.x + 1.5 - 1.5, HUT.z - 0.5 - 0.2);
  } else if (t < S.run) {    // morning: from behind a tree he watches
    f.headPitch = t > S.lift ? -0.45 : 0; f.brow = 0.6; f.eyes = 1.05; f.smile = t > S.pop ? 0.3 : 0;
    pos = [2.8, 0, 0.6]; yaw = -2.3;
  } else if (t < S.light) {  // runs a few steps, then stops
    const k = seg(t, S.run, S.run + 1.3);
    f.walk = k < 1 ? 1 : 0; f.phase = t * 10; f.armR = [-1.6 * (1 - k), -0.2]; f.headPitch = -0.4;
    pos = [lerp(2.8, 1.4, k), 0, lerp(0.6, -0.4, k)]; yaw = -2.3;
  } else if (t < S.clap) {   // empty hands, light heart
    f.armL = [-0.9, 0.3]; f.armR = [-0.9, -0.3]; f.elbowL = -0.3; f.elbowR = -0.3; f.headPitch = -0.3; f.smile = 0.75; f.eyes = 0.5; f.brow = 0.3;
    pos = [1.4, 0, -0.4]; yaw = -2.3;
  } else if (t < S.home) {   // the world claps for the pigeons; no one sees him
    f.headPitch = -0.3; f.smile = 0.4; f.brow = 0.4; pos = [2.2, 0, 2.8]; yaw = -2.6;
  } else {                   // walking home at dusk; his daughter runs to him
    const k = seg(t, S.home, S.home + 4);
    f.walk = k < 1 ? 1 : 0; f.phase = t * 6; f.smile = 0.6;
    pos = [lerp(0.5, HUT.x + 1.6, k), 0, lerp(0.0, HUT.z + 0.4, k)]; yaw = -2.0;
    if (t > S.home + 4.2) { f.walk = 0; f.armL = [-1.1, 0.5]; f.armR = [-1.1, -0.5]; f.elbowL = -1.0; f.elbowR = -1.0; f.headPitch = 0.45; f.eyes = 0; f.happyEyes = true; f.smile = 1; yaw = -2.0; }
  }
  out.push({ look: FARMER, pose: f, pos, yaw, s: 0.86, handR });
  // sweat drops on his face while he works
  if (t >= S.sweat && t < S.worry) out.push({ look: FARMER, pose: f, pos: [99, 0, 99], yaw: 0 });
  // villagers clapping at the sky
  if (t >= S.clap && t < S.home) VILLAGERS.forEach((v, k) => out.push({ look: v, pose: P((p) => { p.armL = [-1.5, 0.4 - 0.35 * Math.abs(Math.sin(t * 10 + k))]; p.armR = [-1.5, -0.4 + 0.35 * Math.abs(Math.sin(t * 10 + k))]; p.elbowL = -0.6; p.elbowR = -0.6; p.headPitch = -0.5; p.smile = 1; p.happyEyes = true; p.eyes = 0; }),
    pos: [-0.6 + k * 0.8, 0, 1.4 + (k % 2) * 0.3], yaw: Math.PI + 0.2 * (k - 1), s: 0.82 }));
  // his daughter
  if (t >= S.home + 1.5) {
    const k = seg(t, S.home + 1.5, S.home + 4.2);
    out.push({ look: BETI, pose: P((p) => { p.walk = k < 1 ? 1 : 0; p.phase = t * 11; p.smile = 1; p.happyEyes = k >= 1; p.eyes = k >= 1 ? 0 : 1; if (k >= 1) { p.armL = [-1.6, 0.6]; p.armR = [-1.6, -0.6]; p.elbowL = -0.8; p.elbowR = -0.8; p.headPitch = -0.4; } }),
      pos: [lerp(HUT.x + 0.4, HUT.x + 1.25, k), 0, lerp(HUT.z + 1.0, HUT.z + 0.15, k)], yaw: lerp(0.4, 1.1, k), s: 0.5 });
  }
  return out;
}

// ------------------------------------------------------------------ camera
type Cam = { pos: [number, number, number]; target: [number, number, number]; fov: number; roll?: number };
function camAt(t: number): Cam {
  if (t < S.truth) { const k = clamp(t / S.truth); return { pos: lerp3([3.2, 0.6, 2.6], [2.8, 0.9, 2.2], k), target: lerp3([0.4, 2.2, -1.4], [0.8, 3.6, -1.8], k), fov: 50 }; }
  if (t < S.last) { if (t < 6.0) return { pos: [0.55, 0.55, -1.25], target: [1.45, 0.35, -0.3], fov: 44 };   // the hand loosening the peg
    return { pos: [0.45, 1.15, -1.55], target: [1.75, 0.9, -0.1], fov: 40 }; }
  if (t < S.sweat) { const k = (t - S.last) / (S.sweat - S.last); return { pos: lerp3([-0.8, 1.7, -2.0], [-0.3, 1.3, -1.6], k), target: [1.6, 0.75, -0.2], fov: 46 }; }
  if (t < S.worry) return { pos: [3.2, 1.2, 0.4], target: [0.8, 1.0, -2.4], fov: 44 };
  if (t < S.grow) return { pos: [1.2, 0.5, -0.4], target: [0.4, 2.2, -2.6], fov: 50 };                                  // low, looking up past him at the cloud
  if (t < S.flock) { const k = Easing.inOut(Easing.cubic)((t - S.grow) / (S.flock - S.grow)); return { pos: lerp3([0.6, 1.0, 0.8], [1.8, 3.2, 3.2], k), target: [0.1, 0.9, -1.6], fov: 48 }; }
  if (t < S.spread) return { pos: [2.9, 0.7, 1.3], target: [0.2, 3.2, -1.4], fov: 58 };                                   // up past him at the circling flock
  if (t < S.why) return { pos: [1.4, 2.6, 1.8], target: [0, 0, -1.2], fov: 46 };
  if (t < S.fruit) return { pos: [0.2, 1.3, -1.9], target: [1.6, 0.75, -0.2], fov: 44 };
  if (t < S.pegs) return { pos: [-1.1, 1.4, -1.3], target: [0.9, 1.15, -0.4], fov: 40 };
  if (t < S.land) { if (t < 39.42) return { pos: [NET.x + 0.9, 0.3, NET.z + NET_D / 2 + 0.8], target: [NET.x + 0.6, 0.08, NET.z + NET_D / 2], fov: 40 };   // the loose pegs wobble
    return { pos: [3.0, 2.2, 3.0], target: [-0.5, 0.5, 0], fov: 50 }; }
  if (t < S.king) { const k = (t - S.land) / (S.king - S.land); return { pos: lerp3([2.6, 1.3, 1.2], [2.2, 1.0, 0.8], k), target: [0, 0.2, -1.4], fov: 46 }; }
  if (t < S.lift) return { pos: [NET.x + FLOCK[0].nx + 0.5, 0.38, NET.z + FLOCK[0].nz + 0.9], target: [NET.x + FLOCK[0].nx, 0.22, NET.z + FLOCK[0].nz], fov: 40 };   // the king pigeon
  if (t < S.run) { const k = (t - S.lift) / (S.run - S.lift); return { pos: [2.4, 0.3, 1.4], target: lerp3([0, 0.3, -1.4], [0.6, 2.6, -2.2], k), fov: 54 }; }
  if (t < S.light) return { pos: [-0.8, 1.3, -2.4], target: [1.9, 1.0, 0.1], fov: 46 };
  if (t < S.clap) return { pos: [-0.1, 1.5, -1.75], target: [1.4, 1.55, -0.4], fov: 40 };
  if (t < S.home) return { pos: [0.8, 1.25, -3.2], target: [0.9, 1.5, 1.8], fov: 60 };
  if (t < S.hand) { const k = (t - S.home) / (S.hand - S.home); return { pos: lerp3([2.6, 1.4, 3.4], [-1.2, 1.2, 4.6], k), target: lerp3([0.5, 1.0, 0], [HUT.x + 1.3, 0.8, HUT.z + 0.3], k), fov: 46 }; }
  if (t < S.crane) return { pos: [HUT.x + 1.9, 0.8, HUT.z + 1.4], target: [HUT.x + 1.35, 0.7, HUT.z + 0.3], fov: 38 };
  const k = Easing.inOut(Easing.cubic)(clamp((t - S.crane) / (END - S.crane)));
  return { pos: lerp3([HUT.x + 2.2, 1.0, HUT.z + 2.2], [HUT.x + 5, 4.5, HUT.z + 6], k), target: lerp3([HUT.x + 1.3, 0.8, HUT.z + 0.3], [0, 1.5, -2], k), fov: 46 };
}
const CameraRig: React.FC<{ t: number }> = ({ t }) => {
  const { camera } = useThree();
  const c = camAt(t);
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(...c.pos); cam.up.set(Math.sin(c.roll ?? 0), Math.cos(c.roll ?? 0), 0);
  cam.fov = c.fov; cam.near = 0.03; cam.far = 120; cam.lookAt(V(...c.target)); cam.updateProjectionMatrix();
  return null;
};

// time of day: 0 day, 1 dusk, 2 night, 3 dawn
function tod(t: number): number {
  if (t >= S.last && t < S.sweat) return 1;               // last year: grey-gold despair
  if (t >= S.pegs + 1 && t < S.land) return lerp(0, 1, seg(t, S.pegs + 1, S.pegs + 3));
  if (t >= S.land && t < S.king) return 3;
  if (t >= S.home) return 1;
  return 0;
}

const Scene: React.FC<{ t: number }> = ({ t }) => {
  const d = tod(t);
  const skyD = useMemo(() => skyMat("#5aa8f0", "#f4ecd0", 0), []);
  const skyDusk = useMemo(() => skyMat("#3a3a7a", "#ff9a50", 0.2), []);
  const skyDawn = useMemo(() => skyMat("#6a8ad0", "#ffd0a0", 0), []);
  const sk = d > 2 ? skyDawn : d > 0.5 ? skyDusk : skyD;
  const n = netState(t);
  const birds = birdsAt(t, n.y);
  const dusk = d > 0.5 && d < 2;
  return (
    <>
      <CameraRig t={t} />
      <mesh material={sk} scale={100}><sphereGeometry args={[1, 32, 16]} /></mesh>
      <fog attach="fog" args={[dusk ? "#e8a070" : "#e8eef0", 16, 60]} />
      <ambientLight intensity={dusk ? 0.75 : 1.0} color={dusk ? "#ffd0a0" : "#ffffff"} />
      <hemisphereLight args={["#9ad0ff", "#5a6a2a", 0.5]} />
      <directionalLight position={dusk ? [-10, 5, -4] : [8, 12, 6]} intensity={dusk ? 1.6 : 2.0} color={dusk ? "#ff9a50" : d > 2 ? "#ffd8a8" : "#fff4e0"} castShadow
        shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-8} shadow-camera-right={8} shadow-camera-top={8} shadow-camera-bottom={-8} shadow-bias={-0.001} />
      <Village />
      <Field t={t} />
      <Net t={t} />
      <Pegs t={t} />
      <StormCloud t={t} />
      {birds.map((b, k) => b.pos[1] > -10 ? (
        <group key={k} position={b.pos} rotation={[0, b.yaw, 0]} scale={b.king ? 1.25 : 1}><Pigeon flap={b.flap} t={t + k} color={b.color} king={b.king} peck={b.peck} panic={b.panic} /></group>
      ) : null)}
      {actorsAt(t).map((a, k) => a.pos[0] > 50 ? null : (
        <group key={k} position={a.pos} rotation={[0, a.yaw, 0]} scale={a.s ?? 0.86}><Person look={a.look} pose={a.pose} handR={a.handR} handL={a.handL} /></group>
      ))}
      {t >= S.last + 4.3 && t < S.sweat ? <Debt t={t} at={[1.6, 1.25, -0.2]} /> : null}
      {/* sweat drops */}
      {t >= S.sweat && t < S.worry ? [0, 1, 2].map((k) => { const u = ((t * 1.4 + k * 0.33) % 1); return <mesh key={k} position={[0.8 + 0.08 * (k - 1), 1.62 - u * 0.4, -2.4 + 0.12]} scale={[0.015, 0.025, 0.015]}><sphereGeometry args={[1, 6, 6]} /><meshBasicMaterial color="#bfe0ff" transparent opacity={1 - u} /></mesh>; }) : null}
      {/* a light heart for "दिल हल्का" */}
      {t >= S.light && t < S.clap ? <group position={[1.4, 1.95 + 0.25 * seg(t, S.light, S.clap), -0.4]} rotation={[0, 0.6, Math.PI]} scale={0.18 * seg(t, S.light, S.light + 0.4)}>
        <mesh><extrudeGeometry args={[(() => { const s = new THREE.Shape(); s.moveTo(0, -0.3); s.bezierCurveTo(-0.6, 0.1, -0.35, 0.55, 0, 0.25); s.bezierCurveTo(0.35, 0.55, 0.6, 0.1, 0, -0.3); return s; })(), { depth: 0.08, bevelEnabled: false }]} /><meshBasicMaterial color="#ff8aa8" transparent opacity={0.9} /></mesh>
        <pointLight color="#ffb0c0" intensity={1.2} distance={1.5} /></group> : null}
    </>
  );
};

export const Kabootar3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const sub = SUBS.find(([a, b]) => t >= a && t < b);
  const cuts = (Object.keys(S) as (keyof typeof S)[]).map((k) => S[k]).filter((c) => [S.drop, S.pop, S.light].indexOf(c) < 0);
  let dip = 0; for (const c of cuts) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.1);
  const fade = Math.min(clamp(t / 0.4), clamp((END - t) / 1.2));
  const past = t >= S.last && t < S.sweat;
  const filter = past ? "sepia(0.5) saturate(0.8) contrast(1.05)" : "none";
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ filter }}>
        <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
          <Scene t={t} />
        </ThreeCanvas>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)" }} />
      {past ? <div style={{ position: "absolute", top: 140, left: 0, right: 0, textAlign: "center", color: "#f4e8d0", fontFamily: "'Noto Serif Devanagari', serif", fontSize: 40, fontWeight: 700, letterSpacing: 2, textShadow: "0 2px 8px rgba(0,0,0,0.7)" }}>पिछला साल</div> : null}
      {sub ? (
        <div style={{ position: "absolute", top: 1300, left: 60, right: 60, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 54, lineHeight: 1.4, color: "#faf6ee", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill",
          textShadow: "0 4px 14px rgba(0,0,0,0.75)" }}>{sub[2]}</div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.35) }} />
    </AbsoluteFill>
  );
};
