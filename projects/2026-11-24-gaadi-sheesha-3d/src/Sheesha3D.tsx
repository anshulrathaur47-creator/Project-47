import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { G, Look, Person, Pose, Toon, restPose } from "./Character";

// "किसी गाड़ी के शीशे पर जमी धूल पर…" (ReelAudio-74390), 3D.
export const DURATION = 629; // 20.97 s at 30 fps
const FPS = 30;
const END = DURATION / FPS;

// ------------------------------------------------------------------------------------ helpers
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (x: number) => {
  const t = clamp(x);
  return t * t * (3 - 2 * t);
};
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: number[], b: number[], t: number) => a.map((v, i) => lerp(v, b[i], t)) as [number, number, number];
const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// lyric lines (Whisper word timings); the audience's "वाह" gets no text
const LINES: [number, number, string][] = [
  [0.1, 3.06, "किसी गाड़ी के शीशे पर जमी धूल पर"],
  [3.08, 6.04, "मैं उसका और मेरा नाम लिखा करता हूँ"],
  [6.66, 8.42, "कोई देख ना ले इसी डर से"],
  [8.44, 9.84, "फिर मिटा दिया करता हूँ"],
  [9.86, 12.28, "वो मुझसे मोहब्बत नहीं करने वाली"],
  [12.3, 13.5, "ये बात पता है मुझे"],
  [13.52, 15.44, "फिर भी उसका नाम सुनते ही"],
  [15.46, 16.85, "मैं मुस्कुरा दिया करता हूँ"],
];
const CUTS = [1.55, 3.08, 4.9, 6.66, 7.5, 8.44, 9.84, 12.3, 13.52, 15.46, 16.8];

// ------------------------------------------------------------------------------------ the car and its dusty windshield
const CX = -1.3;             // car centre x (front faces +z)
const WS_W = 1.5;            // windshield width
const WS_BOT = { y: 0.95, z: 0.9 };
const WS_TOP = { y: 1.5, z: 0.2 };
const WS_ANG = -Math.atan2(WS_BOT.z - WS_TOP.z, WS_TOP.y - WS_BOT.y);
const WS_H = Math.hypot(WS_BOT.z - WS_TOP.z, WS_TOP.y - WS_BOT.y);
const CW = 1024, CH = Math.round((1024 * WS_H) / WS_W);

// canvas pixel -> world point on the glass (slightly in front of it)
function glassPoint(px: number, py: number, out = 0.025): THREE.Vector3 {
  const u = px / CW, v = 1 - py / CH;
  const normal = V(0, -Math.sin(WS_ANG), Math.cos(WS_ANG));   // glass faces up and forward
  return V(CX - WS_W / 2 + u * WS_W, WS_BOT.y + v * (WS_TOP.y - WS_BOT.y), WS_BOT.z + v * (WS_TOP.z - WS_BOT.z)).addScaledVector(normal, out);
}

// heart on the right half of the glass (his side), names inside it
const HEART = { cx: 735, cy: CH * 0.47, s: 9.2 };
function heartPt(k: number): [number, number] {
  const a = Math.PI * 2 * k;   // starts at the top notch
  const x = 16 * Math.sin(a) ** 3;
  const y = 13 * Math.cos(a) - 5 * Math.cos(2 * a) - 2 * Math.cos(3 * a) - Math.cos(4 * a);
  return [HEART.cx + x * HEART.s, HEART.cy - y * HEART.s - 2];
}
const NAMES: { text: string; y: number; a: number; b: number; size: number }[] = [
  { text: "मीरा", y: HEART.cy - 28, a: 3.86, b: 4.5, size: 70 },
  { text: "+ विहान", y: HEART.cy + 52, a: 4.52, b: 5.4, size: 62 },
];
const HEART_A = 1.72, HEART_B = 3.02;     // heart drawn (inside-car shot)
const WIPE_A = 8.62, WIPE_B = 9.38;       // sleeve wipe

type Ink = { heart: number; names: number[]; wipe: number };
function inkAt(t: number): Ink {
  return {
    heart: clamp((t - HEART_A) / (HEART_B - HEART_A)),
    names: NAMES.map((n) => clamp((t - n.a) / (n.b - n.a))),
    wipe: clamp((t - WIPE_A) / (WIPE_B - WIPE_A)),
  };
}

// where his finger (or sleeve) is on the glass, in canvas pixels
function fingerAt(t: number): [number, number] | null {
  const ink = inkAt(t);
  if (t >= HEART_A - 0.25 && t < HEART_B + 0.1) return heartPt(Math.max(ink.heart, 0.001));
  for (let i = 0; i < NAMES.length; i++) {
    const n = NAMES[i];
    if (t >= n.a - 0.15 && t < n.b + 0.12) {
      const w = n.size * (n.text.length * 0.52);
      const x0 = HEART.cx - w / 2;
      return [x0 + w * ink.names[i], n.y - n.size * 0.3 + Math.sin(t * 40) * n.size * 0.18];
    }
  }
  if (t >= WIPE_A - 0.2 && t < WIPE_B + 0.05) {
    const k = ink.wipe;
    return [lerp(980, 430, k), HEART.cy + Math.sin(k * Math.PI * 3) * 70];
  }
  return null;
}

function makeDustBase(): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = CW;
  c.height = CH;
  const x = c.getContext("2d")!;
  const img = x.createImageData(CW, CH);
  const r = rng(42);
  for (let j = 0; j < CH; j++)
    for (let i = 0; i < CW; i++) {
      const n = r();
      const edge = Math.min(i, CW - i, j, CH - j) / 90;      // dust collects at the edges
      const streak = 0.5 + 0.5 * Math.sin(i * 0.11 + Math.sin(j * 0.02) * 3);
      const a = clamp(0.5 + 0.16 * n + 0.08 * streak + 0.2 * (1 - clamp(edge)));
      const o = (j * CW + i) * 4;
      const tone = 150 + n * 30;
      img.data[o] = tone + 18;
      img.data[o + 1] = tone + 6;
      img.data[o + 2] = tone - 16;
      img.data[o + 3] = a * 255;
    }
  x.putImageData(img, 0, 0);
  // a few dried rain drip marks
  x.globalCompositeOperation = "destination-out";
  for (let k = 0; k < 40; k++) {
    const px = r() * CW, py = r() * CH * 0.6, len = 40 + r() * 140;
    x.strokeStyle = `rgba(0,0,0,${0.15 + r() * 0.2})`;
    x.lineWidth = 2 + r() * 3;
    x.beginPath();
    x.moveTo(px, py);
    x.lineTo(px + (r() - 0.5) * 8, py + len);
    x.stroke();
  }
  return c;
}

function makeNameMask(i: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = CW;
  c.height = CH;
  const x = c.getContext("2d")!;
  const n = NAMES[i];
  x.fillStyle = "#000";
  x.font = `400 ${n.size}px 'Noto Sans Devanagari'`;
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillText(n.text, HEART.cx, n.y);
  return c;
}

// draws the heart + names into ctx with the current composite op
function drawInk(x: CanvasRenderingContext2D, ink: Ink, masks: HTMLCanvasElement[], alpha: number, width = 15) {
  x.save();
  x.globalAlpha = alpha;
  if (ink.heart > 0) {
    x.strokeStyle = "#000";
    x.lineWidth = width;
    x.lineCap = "round";
    x.lineJoin = "round";
    x.beginPath();
    const steps = Math.ceil(160 * ink.heart);
    for (let i = 0; i <= steps; i++) {
      const [px, py] = heartPt((i / 160) * 1);
      if (i === 0) x.moveTo(px, py);
      else x.lineTo(px, py);
    }
    x.stroke();
  }
  NAMES.forEach((n, i) => {
    const k = ink.names[i];
    if (k <= 0) return;
    const w = n.size * (n.text.length * 0.52) + 30;
    const x0 = HEART.cx - w / 2;
    x.save();
    x.beginPath();
    x.rect(0, 0, x0 + w * k, CH);
    x.clip();
    x.drawImage(masks[i], 0, 0);
    x.restore();
  });
  x.restore();
}

const GlassMat: React.FC<{ t: number }> = ({ t }) => {
  const res = useMemo(() => {
    const out = document.createElement("canvas");
    out.width = CW;
    out.height = CH;
    const dust = document.createElement("canvas");
    dust.width = CW;
    dust.height = CH;
    const tex = new THREE.CanvasTexture(out);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    return { out, dust, tex, base: makeDustBase(), masks: NAMES.map((_, i) => makeNameMask(i)) };
  }, []);
  const ink = inkAt(t);
  // dust layer: base, minus the finger lines, minus the sleeve wipe
  const d = res.dust.getContext("2d")!;
  d.globalCompositeOperation = "source-over";
  d.clearRect(0, 0, CW, CH);
  d.drawImage(res.base, 0, 0);
  d.globalCompositeOperation = "destination-out";
  const sweepX = lerp(1000, 380, ink.wipe);           // sleeve moves right -> left
  if (ink.wipe > 0) {
    // untouched part keeps crisp lines, the wiped part keeps only a faint trace
    d.save();
    d.beginPath();
    d.rect(0, 0, sweepX, CH);
    d.clip();
    drawInk(d, ink, res.masks, 1);
    d.restore();
    d.save();
    d.beginPath();
    d.rect(sweepX, 0, CW, CH);
    d.clip();
    drawInk(d, ink, res.masks, 0.22);
    // smudgy streaks of the sleeve
    d.lineCap = "round";
    const r = rng(9);
    for (let s = 0; s < 16; s++) {
      d.globalAlpha = 0.22 + r() * 0.25;
      d.lineWidth = 26 + r() * 40;
      d.beginPath();
      const yy = HEART.cy - 190 + s * 26 + (r() - 0.5) * 30;
      d.moveTo(1010, yy + (r() - 0.5) * 50);
      d.bezierCurveTo(840, yy + (r() - 0.5) * 90, 600, yy + (r() - 0.5) * 90, 340 + r() * 80, yy + (r() - 0.5) * 70);
      d.stroke();
    }
    d.restore();
  } else {
    drawInk(d, ink, res.masks, 1);
  }
  // final: tinted glass + sheen + dust
  const o = res.out.getContext("2d")!;
  o.globalCompositeOperation = "source-over";
  o.clearRect(0, 0, CW, CH);
  o.fillStyle = "rgba(14,20,32,0.42)";
  o.fillRect(0, 0, CW, CH);
  const sheenX = lerp(-400, CW + 400, clamp((t - 1.5) / 0.5));   // "शीशे": a glint runs across the glass
  if (t > 1.5 && t < 2.0) {
    const g = o.createLinearGradient(sheenX - 160, 0, sheenX + 160, CH * 0.5);
    g.addColorStop(0, "rgba(255,255,255,0)");
    g.addColorStop(0.5, "rgba(255,250,235,0.5)");
    g.addColorStop(1, "rgba(255,255,255,0)");
    o.fillStyle = g;
    o.fillRect(0, 0, CW, CH);
  }
  o.drawImage(res.dust, 0, 0);
  res.tex.needsUpdate = true;
  return <meshStandardMaterial map={res.tex} transparent side={THREE.DoubleSide} roughness={0.55} metalness={0.05} depthWrite={false} />;
};

// a glowing copy of the faint heart for the outro: the street light catches the trace
const HeartTrace: React.FC<{ glow: number }> = ({ glow }) => {
  const tex = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = CW;
    c.height = CH;
    const x = c.getContext("2d")!;
    x.shadowColor = "rgba(255,210,140,1)";
    x.shadowBlur = 26;
    x.strokeStyle = "rgba(255,226,170,1)";
    x.lineWidth = 12;
    x.lineCap = "round";
    x.beginPath();
    for (let i = 0; i <= 160; i++) {
      const [px, py] = heartPt(i / 160);
      if (i === 0) x.moveTo(px, py);
      else x.lineTo(px, py);
    }
    x.stroke();
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, []);
  if (glow <= 0.01) return null;
  return (
    <mesh position={[CX, (WS_BOT.y + WS_TOP.y) / 2, (WS_BOT.z + WS_TOP.z) / 2]} rotation={[WS_ANG, 0, 0]}>
      <planeGeometry args={[WS_W, WS_H]} />
      <meshBasicMaterial map={tex} transparent opacity={glow} blending={THREE.AdditiveBlending} depthWrite={false} polygonOffset polygonOffsetFactor={-2} />
    </mesh>
  );
};

const Car: React.FC<{ pos: [number, number, number]; color: string; rotY?: number; t?: number; dusty?: boolean }> = ({ pos, color, rotY = 0, t = 0, dusty }) => {
  const side = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-WS_BOT.z, WS_BOT.y);
    s.lineTo(-WS_TOP.z, WS_TOP.y);
    s.lineTo(1.2, 1.5);
    s.lineTo(1.7, 0.95);
    s.lineTo(-WS_BOT.z, WS_BOT.y);
    return new THREE.ShapeGeometry(s);
  }, []);
  const rearAng = Math.atan2(0.5, 0.55);
  return (
    <group position={pos} rotation={[0, rotY, 0]}>
      <group position={[-CX, 0, 0]}>
        {/* lower body */}
        <Toon geom={G.box} color={color} position={[CX, 0.625, 0]} scale={[1.7, 0.65, 4.1]} outline={0.003} />
        <Toon geom={G.box} color="#2a2a2e" position={[CX, 0.38, 2.08]} scale={[1.72, 0.16, 0.12]} outline={0} />
        <Toon geom={G.box} color="#2a2a2e" position={[CX, 0.38, -2.08]} scale={[1.72, 0.16, 0.12]} outline={0} />
        {/* roof and pillars */}
        <Toon geom={G.box} color={color} position={[CX, 1.5, -0.5]} scale={[1.52, 0.06, 1.45]} outline={0.004} />
        {[-1, 1].map((s) => (
          <group key={s}>
            <mesh position={[CX + s * 0.75, (WS_BOT.y + WS_TOP.y) / 2, (WS_BOT.z + WS_TOP.z) / 2]} rotation={[WS_ANG, 0, 0]}>
              <boxGeometry args={[0.06, WS_H, 0.05]} />
              <meshToonMaterial color={color} />
            </mesh>
            <mesh position={[CX + s * 0.75, 1.225, -1.45]} rotation={[-rearAng, 0, 0]}>
              <boxGeometry args={[0.06, 0.75, 0.05]} />
              <meshToonMaterial color={color} />
            </mesh>
            <mesh position={[CX + s * 0.75, 1.22, -0.45]}>
              <boxGeometry args={[0.05, 0.55, 0.08]} />
              <meshToonMaterial color={color} />
            </mesh>
            {/* side windows */}
            <mesh geometry={side} position={[CX + s * 0.755, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
              <meshStandardMaterial color="#141a26" transparent opacity={0.8} roughness={0.25} metalness={0.3} side={THREE.DoubleSide} />
            </mesh>
            {/* wheels */}
            {[1.35, -1.35].map((z) => (
              <mesh key={z} position={[CX + s * 0.8, 0.3, z]} rotation={[0, 0, Math.PI / 2]} castShadow>
                <cylinderGeometry args={[0.3, 0.3, 0.2, 20]} />
                <meshToonMaterial color="#17171a" />
              </mesh>
            ))}
            {[1.35, -1.35].map((z) => (
              <mesh key={"h" + z} position={[CX + s * 0.905, 0.3, z]} rotation={[0, 0, Math.PI / 2]}>
                <cylinderGeometry args={[0.15, 0.15, 0.02, 16]} />
                <meshToonMaterial color="#9a9aa2" />
              </mesh>
            ))}
            {/* lights */}
            <mesh position={[CX + s * 0.6, 0.75, 2.06]} scale={[0.17, 0.09, 0.02]}>
              <sphereGeometry args={[1, 14, 10]} />
              <meshBasicMaterial color="#e8e4d4" />
            </mesh>
            <mesh position={[CX + s * 0.65, 0.78, -2.06]} scale={[0.12, 0.08, 0.02]}>
              <sphereGeometry args={[1, 12, 8]} />
              <meshBasicMaterial color="#8a1a1a" />
            </mesh>
          </group>
        ))}
        <mesh position={[CX, 0.5, 2.15]}>
          <boxGeometry args={[0.45, 0.12, 0.02]} />
          <meshBasicMaterial color="#e8e2c8" />
        </mesh>
        {/* interior: dashboard, steering wheel, seats */}
        <mesh position={[CX, 0.99, 0.75]}>
          <boxGeometry args={[1.45, 0.1, 0.3]} />
          <meshToonMaterial color="#1c1c20" />
        </mesh>
        <mesh position={[CX - 0.38, 1.1, 0.48]} rotation={[-1.0, 0, 0]}>
          <torusGeometry args={[0.17, 0.02, 8, 24]} />
          <meshToonMaterial color="#111114" />
        </mesh>
        {[-0.38, 0.38].map((dx) => (
          <group key={dx}>
            <mesh position={[CX + dx, 0.75, -0.25]}>
              <boxGeometry args={[0.5, 0.15, 0.5]} />
              <meshToonMaterial color="#3a2e2a" />
            </mesh>
            <mesh position={[CX + dx, 1.05, -0.5]} rotation={[-0.2, 0, 0]}>
              <boxGeometry args={[0.48, 0.6, 0.12]} />
              <meshToonMaterial color="#3a2e2a" />
            </mesh>
          </group>
        ))}
        {/* windshield + rear window */}
        <mesh position={[CX, (WS_BOT.y + WS_TOP.y) / 2, (WS_BOT.z + WS_TOP.z) / 2]} rotation={[WS_ANG, 0, 0]} renderOrder={2}>
          <planeGeometry args={[WS_W, WS_H]} />
          {dusty ? <GlassMat t={t} /> : <meshStandardMaterial color="#141a26" transparent opacity={0.75} roughness={0.2} metalness={0.3} side={THREE.DoubleSide} />}
        </mesh>
        <mesh position={[CX, 1.225, -1.45]} rotation={[-rearAng, 0, 0]}>
          <planeGeometry args={[1.45, 0.75]} />
          <meshStandardMaterial color="#141a26" transparent opacity={0.8} roughness={0.2} metalness={0.3} side={THREE.DoubleSide} />
        </mesh>
      </group>
    </group>
  );
};

// ------------------------------------------------------------------------------------ the lane at night
const skyMat = () =>
  new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: { top: { value: new THREE.Color("#060a1c") }, bottom: { value: new THREE.Color("#33365e") } },
    vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ",
    fragmentShader:
      "uniform vec3 top; uniform vec3 bottom; varying vec3 vP; float h1(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,45.164)))*43758.5453);} " +
      "void main(){ float h = clamp(vP.y*1.5+0.1,0.0,1.0); vec3 c = mix(bottom, top, h); " +
      "vec3 q = floor(vP*260.0); float s = step(0.9965, h1(q)) * smoothstep(0.1,0.4,vP.y); c += vec3(s*0.8); gl_FragColor = vec4(c,1.0);} ",
  });

const Buildings: React.FC = () => {
  const data = useMemo(() => {
    const r = rng(17);
    const b: { x: number; z: number; w: number; h: number; d: number; col: string }[] = [];
    const win: { x: number; y: number; z: number; side: number; on: boolean; col: string }[] = [];
    for (const side of [-1, 1]) {
      let z = 16;
      while (z > -46) {
        const d = 3 + r() * 3, h = 4 + r() * 7, w = 3;
        b.push({ x: side * (4.2 + w / 2), z: z - d / 2, w, h, d: d - 0.2, col: ["#4c4a5c", "#3e4658", "#5a4c4e", "#424a50"][Math.floor(r() * 4)] });
        for (let yy = 1.6; yy < h - 0.6; yy += 1.3)
          for (let zz = z - 0.7; zz > z - d + 0.4; zz -= 1.1)
            win.push({ x: side * 4.19, y: yy, z: zz, side, on: r() < 0.5, col: r() < 0.7 ? "#ffcf86" : "#a8d0ff" });
        z -= d;
      }
    }
    return { b, win };
  }, []);
  return (
    <group>
      {data.b.map((o, i) => (
        <mesh key={i} position={[o.x, o.h / 2, o.z]} receiveShadow>
          <boxGeometry args={[o.w, o.h, o.d]} />
          <meshToonMaterial color={o.col} />
        </mesh>
      ))}
      {data.win.map((w, i) => (
        <mesh key={"w" + i} position={[w.x, w.y, w.z]} rotation={[0, (w.side * -Math.PI) / 2, 0]}>
          <planeGeometry args={[0.55, 0.7]} />
          <meshBasicMaterial color={w.on ? w.col : "#1e2232"} />
        </mesh>
      ))}
    </group>
  );
};

const Lamp: React.FC<{ base: [number, number, number]; dir: 1 | -1; target: [number, number, number]; intensity?: number; shadow?: boolean }> = ({
  base, dir, target, intensity = 22, shadow,
}) => {
  const tgt = useMemo(() => new THREE.Object3D(), []);
  tgt.position.set(...target);
  const head: [number, number, number] = [base[0] + dir * 0.55, base[1] + 3.3, base[2]];
  return (
    <group>
      <primitive object={tgt} />
      <mesh position={[base[0], base[1] + 1.7, base[2]]} castShadow>
        <cylinderGeometry args={[0.045, 0.06, 3.4, 12]} />
        <meshToonMaterial color="#30343e" />
      </mesh>
      <mesh position={[base[0] + dir * 0.28, base[1] + 3.38, base[2]]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.03, 0.03, 0.6, 8]} />
        <meshToonMaterial color="#30343e" />
      </mesh>
      <mesh position={head}>
        <sphereGeometry args={[0.11, 16, 12]} />
        <meshBasicMaterial color="#fff2cc" />
      </mesh>
      <spotLight position={[head[0], head[1] - 0.05, head[2]]} target={tgt} angle={0.8} penumbra={0.65} intensity={intensity}
        distance={10} decay={1.5} color="#ffcf8a" castShadow={shadow} shadow-mapSize-width={1024} shadow-mapSize-height={1024}
        shadow-bias={-0.0008} shadow-normalBias={0.03} />
      <mesh position={[head[0], head[1] / 2, head[2]]}>
        <coneGeometry args={[1.3, head[1], 32, 1, true]} />
        <meshBasicMaterial color="#ffd9a0" transparent opacity={0.06} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
};

const Tree: React.FC<{ pos: [number, number, number]; s?: number }> = ({ pos, s = 1 }) => (
  <group position={pos} scale={s}>
    <mesh position={[0, 1.1, 0]} castShadow>
      <cylinderGeometry args={[0.09, 0.13, 2.2, 10]} />
      <meshToonMaterial color="#3a2a22" />
    </mesh>
    {[[0, 2.6, 0, 0.95], [0.5, 2.3, 0.2, 0.7], [-0.45, 2.35, -0.1, 0.72], [0.1, 3.1, -0.2, 0.7]].map(([x, y, z, r], i) => (
      <Toon key={i} geom={G.sphere} color={i % 2 ? "#1f3a2c" : "#25463a"} position={[x, y, z]} scale={r} outline={0.006} />
    ))}
  </group>
);

const Street: React.FC = () => (
  <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -12]} receiveShadow>
      <planeGeometry args={[8.4, 80]} />
      <meshStandardMaterial color="#2a2c34" roughness={0.85} />
    </mesh>
    {[-1, 1].map((s) => (
      <mesh key={s} position={[s * 3.2, 0.08, -12]} receiveShadow>
        <boxGeometry args={[2, 0.16, 80]} />
        <meshToonMaterial color="#6c6a68" />
      </mesh>
    ))}
    {Array.from({ length: 14 }).map((_, i) => (
      <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[0.35, 0.005, 14 - i * 5]}>
        <planeGeometry args={[0.1, 2]} />
        <meshBasicMaterial color="#8a8676" />
      </mesh>
    ))}
  </group>
);

// ------------------------------------------------------------------------------------ the people (new looks)
const HIM: Look = { skin: "#c68c66", hair: "#2b1d16", hairStyle: "short", shirt: "#6e7f8e", inner: "#e9e4d8", pants: "#4c5638",
  shoes: "#b8322e", face: true };
const HER: Look = { skin: "#d9a882", hair: "#120c0a", hairStyle: "long", shirt: "#a98ad6", inner: "#f2e8fa", pants: "#e8e0d2",
  shoes: "#e6c26a", face: true };
const FRIEND_A: Look = { skin: "#b97f5c", hair: "#2e1c12", hairStyle: "ponytail", shirt: "#3fa58c", inner: "#f0f0e8", pants: "#262a36",
  shoes: "#f0f0f0", face: true };
const FRIEND_B: Look = { skin: "#d39a74", hair: "#1a1210", hairStyle: "ponytail", shirt: "#e0784a", inner: "#fbe8d8", pants: "#3a5a8a",
  shoes: "#ffffff", face: true };

type Him = { pos: [number, number, number]; yaw: number; lean: number; pose: Pose; visible: boolean; ik: THREE.Vector3 | null; sleeve: boolean };
const WRITE = { x: -0.32, z: 0.45, yaw: -Math.PI / 2, lean: 0.3 };
const LEAN_AT = { x: -0.3, z: -0.05, yaw: Math.PI / 2 };

const pockets = (p: Pose) => {
  p.armL = [0.12, 0.2]; p.armR = [0.12, -0.2]; p.elbowL = -0.55; p.elbowR = -0.55; p.armSwing = 0.15;
};

function himAt(t: number): Him {
  const p = restPose();
  p.blush = 0.35;
  // 1) walks up to the car, hands in pockets, a little bounce
  if (t < 1.55) {
    pockets(p);
    const k = clamp(t / 1.4);
    const x = lerp(0.35, WRITE.x, k), z = lerp(3.4, WRITE.z, k);
    p.walk = k < 1 ? 1 : 0;
    p.phase = t * 8.5;
    p.smile = 0.55;
    p.headYaw = -0.5 * seg(t, 0.7, 1.3);
    const yaw = lerp(Math.PI, WRITE.yaw + Math.PI * 2, seg(t, 1.1, 1.5)) % (Math.PI * 2);
    return { pos: [x, 0, z], yaw, lean: 0, pose: p, visible: true, ik: null, sleeve: false };
  }
  // 2) writing: heart (inside-car shot) and the names (over the shoulder)
  if (t < 4.9) {
    p.armL = [-0.2, 0.35]; p.elbowL = -0.6;
    p.hideArmR = true;
    p.headPitch = 0.42; p.headYaw = 0.25; p.lookY = -0.5;
    p.smile = lerp(0.5, 0.95, seg(t, 3.9, 4.6));
    p.blush = lerp(0.35, 0.75, seg(t, 4.0, 4.8));
    const f = fingerAt(t);
    return { pos: [WRITE.x, 0, WRITE.z], yaw: WRITE.yaw, lean: WRITE.lean, pose: p, visible: true, ik: f ? glassPoint(f[0], f[1], 0.03) : glassPoint(HEART.cx + 60, HEART.cy + 120, 0.06), sleeve: false };
  }
  // 3) stands back and admires it, dreamy; eyes close on "वाह"
  if (t < 6.66) {
    p.headPitch = 0.12; p.headYaw = 0.35;
    p.armL = [0.0, 0.15]; p.armR = [-0.35, -0.2]; p.elbowR = -1.2;
    p.smile = 1; p.blush = 0.85;
    p.lookY = -0.2;
    if (t > 5.95) { p.eyes = 0; p.happyEyes = true; p.headPitch = -0.08; p.headRoll = 0.12; }
    return { pos: [WRITE.x + 0.12, 0, WRITE.z + 0.15], yaw: WRITE.yaw + 0.25, lean: 0.05, pose: p, visible: true, ik: null, sleeve: false };
  }
  // 4) footsteps and laughter: he startles and whips round
  if (t < 8.44) {
    const k = seg(t, 6.7, 6.9);
    p.headYaw = lerp(0.35, -1.25, k);
    p.headPitch = lerp(0.12, -0.05, k);
    p.eyes = lerp(1, 1.3, k); p.mouthO = k; p.brow = -0.4 * k; p.smile = 0;
    p.lookX = -0.8 * k;
    p.armR = [-0.6, -0.3]; p.elbowR = -1.4; p.armL = [-0.2, 0.3]; p.elbowL = -0.8;
    return { pos: [WRITE.x + 0.12, 0, WRITE.z + 0.15], yaw: WRITE.yaw + 0.25, lean: 0, pose: p, visible: true, ik: null, sleeve: false };
  }
  // 5) panic wipe with the sleeve, eyes still on them; then he straightens up
  if (t < 9.84) {
    const f = fingerAt(t);
    const done = t > WIPE_B + 0.05;
    p.headYaw = -1.0; p.headPitch = 0.0; p.eyes = 1.15; p.mouthO = 0.6; p.brow = -0.3; p.lookX = -0.9;
    p.armL = [-0.2, 0.3]; p.elbowL = -0.7;
    if (done) {
      pockets(p);
      p.mouthO = 0; p.smile = 0.1; p.eyes = 1;
      return { pos: [WRITE.x + 0.1, 0, WRITE.z], yaw: WRITE.yaw, lean: 0, pose: p, visible: true, ik: null, sleeve: false };
    }
    p.hideArmR = true;
    return { pos: [WRITE.x, 0, WRITE.z], yaw: WRITE.yaw, lean: WRITE.lean * 0.9, pose: p, visible: true, ik: f ? glassPoint(f[0], f[1], 0.04) : null, sleeve: true };
  }
  // 6) leans on the car pretending to be casual while she passes; she never looks
  if (t < 13.52) {
    pockets(p);
    const her = herAt(t);
    const dz = her.pos[2] - LEAN_AT.z, dx = her.pos[0] - LEAN_AT.x;
    const ang = Math.atan2(dz, dx);          // 0 = straight ahead (+x)
    p.headYaw = t < 12.3 ? clamp(-ang * 0.9, -1.2, 1.2) : 0.15;
    p.smile = t < 11.2 ? 0.45 : lerp(0.45, 0.05, seg(t, 11.2, 11.9));
    p.brow = t < 11.2 ? 0 : lerp(0, 0.6, seg(t, 11.2, 11.9));
    if (t >= 12.3) {   // "ये बात पता है मुझे": knowing, sad little smile, eyes down
      p.smile = lerp(0.05, 0.3, seg(t, 12.5, 12.9)); p.brow = 0.85; p.eyes = 0.55; p.headPitch = 0.32; p.lookY = -0.7;
      p.headRoll = -0.06;
    }
    return { pos: [LEAN_AT.x, 0, LEAN_AT.z], yaw: LEAN_AT.yaw, lean: -0.1, pose: p, visible: true, ik: null, sleeve: false };
  }
  // 7) someone calls her name; he hears it and looks up
  if (t < 15.46) {
    pockets(p);
    const up = seg(t, 14.55, 14.95);
    p.headYaw = lerp(0.15, -1.15, up);
    p.headPitch = lerp(0.32, -0.04, up);
    p.eyes = lerp(0.55, 1.05, up); p.brow = lerp(0.85, 0.1, up); p.smile = lerp(0.3, 0.45, up); p.lookY = lerp(-0.7, 0.1, up);
    return { pos: [LEAN_AT.x, 0, LEAN_AT.z], yaw: LEAN_AT.yaw, lean: -0.1, pose: p, visible: true, ik: null, sleeve: false };
  }
  // 8) "मुस्कुरा": the smile he can't stop
  if (t < 16.8) {
    pockets(p);
    const k = seg(t, 15.5, 15.95);
    p.headYaw = lerp(-1.0, -0.35, k);
    p.headPitch = lerp(-0.04, 0.12, k);
    p.headRoll = 0.14 * k;
    p.smile = lerp(0.45, 1, k); p.blush = lerp(0.4, 1, k);
    p.brow = 0;
    if (t > 15.95) { p.eyes = 0; p.happyEyes = true; }
    return { pos: [LEAN_AT.x, 0, LEAN_AT.z], yaw: LEAN_AT.yaw, lean: -0.1, pose: p, visible: true, ik: null, sleeve: false };
  }
  // 9) pushes off the car and walks off into the night, hands in pockets, still smiling
  pockets(p);
  const k = clamp((t - 17.1) / 3.6);
  p.walk = t > 17.1 ? 1 : 0;
  p.phase = t * 8;
  p.smile = 0.85;
  p.headPitch = -0.08;
  p.headRoll = 0.08 * Math.sin(t * 4);
  const yaw = lerp(LEAN_AT.yaw, Math.PI, seg(t, 16.85, 17.3));
  return { pos: [lerp(LEAN_AT.x + 0.15, 0.6, seg(t, 17.0, 17.6)), 0, lerp(LEAN_AT.z, -5.2, k)], yaw, lean: 0, pose: p, visible: true, ik: null, sleeve: false };
}

type Girl = { pos: [number, number, number]; yaw: number; pose: Pose; visible: boolean };
// she walks with two friends, laughing, from the far end of the lane past him and away
function herAt(t: number): Girl {
  const p = restPose();
  p.walk = 1;
  p.phase = t * 7.2;
  p.smile = 0.9;
  p.headPitch = 0.05;
  p.blush = 0.3;
  let z = 99;
  if (t >= 6.66 && t < 9.84) z = -15 + 1.3 * (t - 6.66);
  else if (t >= 9.84 && t < 12.3) z = -2.6 + 1.35 * (t - 9.84);
  else if (t >= 13.52 && t < 16.8) z = 5.0 + 1.3 * (t - 13.52);
  const visible = z < 90;
  // laughing with the friend on her right, never looking his way
  p.headYaw = 0.55 + 0.08 * Math.sin(t * 5);
  p.headRoll = 0.06 * Math.sin(t * 9);
  if (t > 10.6 && t < 11.6) { p.eyes = 0; p.happyEyes = true; p.smile = 1; }
  if (t >= 13.52) {   // her friend calls her; she turns toward the voice
    const k = seg(t, 14.0, 14.4);
    p.headYaw = lerp(0.55, -0.2, k);
    p.smile = 0.8;
  }
  return { pos: [1.15, 0, z], yaw: 0, pose: p, visible };
}

// ------------------------------------------------------------------------------------ helpers for the IK arm
const Bone: React.FC<{ a: THREE.Vector3; b: THREE.Vector3; r: number; color: string }> = ({ a, b, r, color }) => {
  const d = b.clone().sub(a);
  const len = d.length();
  const q = new THREE.Quaternion().setFromUnitVectors(V(0, 1, 0), d.clone().normalize());
  const mid = a.clone().add(b).multiplyScalar(0.5);
  return (
    <group position={mid} quaternion={q}>
      <Toon geom={G.capsule} color={color} scale={[r, Math.max(0.01, len / 3 + r * 0.3), r]} />
    </group>
  );
};

function shoulderWorld(h: Him): THREE.Vector3 {
  const hipY = 0.95;
  const local = V(0.25, hipY + 0.6, 0);
  const m = new THREE.Matrix4()
    .makeTranslation(h.pos[0], h.pos[1], h.pos[2])
    .multiply(new THREE.Matrix4().makeRotationY(h.yaw))
    .multiply(new THREE.Matrix4().makeRotationX(h.lean))
    .multiply(new THREE.Matrix4().makeScale(0.85, 0.85, 0.85));
  return local.applyMatrix4(m);
}

const IKArm: React.FC<{ h: Him; look: Look }> = ({ h, look }) => {
  if (!h.ik) return null;
  const S = shoulderWorld(h);
  const T = h.ik.clone();
  const a = 0.32 * 0.85, b = 0.36 * 0.85;
  const d = Math.min(T.clone().sub(S).length(), (a + b) * 0.995);
  const dir = T.clone().sub(S).normalize();
  const Tc = S.clone().addScaledVector(dir, d);   // reachable target
  const x = (a * a - b * b + d * d) / (2 * d);
  const hgt = Math.sqrt(Math.max(0, a * a - x * x));
  const pole = V(0.2, -1, 0.7).normalize();
  const perp = pole.sub(dir.clone().multiplyScalar(pole.dot(dir))).normalize();
  const E = S.clone().addScaledVector(dir, x).addScaledVector(perp, hgt);
  const handDir = Tc.clone().sub(E).normalize();
  const hand = Tc.clone().addScaledVector(handDir, -0.035);
  return (
    <group>
      <Bone a={S} b={E} r={0.06 * 0.85} color={look.shirt} />
      <Bone a={E} b={hand.clone().addScaledVector(handDir, -0.02)} r={(h.sleeve ? 0.06 : 0.052) * 0.85} color={look.shirt} />
      <Toon geom={G.sphere} color={look.skin} position={hand.toArray() as [number, number, number]} scale={[0.038, 0.04, 0.034]} outline={0.008} />
      {!h.sleeve ? <Bone a={hand} b={Tc} r={0.011} color={look.skin} /> : null}
    </group>
  );
};

// ------------------------------------------------------------------------------------ signs and fx
const heartGeo = (() => {
  const s = new THREE.Shape();
  s.moveTo(0, -0.3);
  s.bezierCurveTo(-0.6, 0.1, -0.35, 0.55, 0, 0.25);
  s.bezierCurveTo(0.35, 0.55, 0.6, 0.1, 0, -0.3);
  return new THREE.ExtrudeGeometry(s, { depth: 0.1, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.03, bevelSegments: 3 });
})();

// dust motes hanging in the lamp light ("धूल"), and a puff when he wipes
const Dust: React.FC<{ t: number }> = ({ t }) => {
  const motes = useMemo(() => {
    const r = rng(23);
    return Array.from({ length: 70 }, () => ({ x: CX - 0.8 + r() * 1.6, y: 1.0 + r() * 0.9, z: 0.2 + r() * 1.1, ph: r() * 6, sp: 0.2 + r() * 0.4 }));
  }, []);
  const puff = useMemo(() => {
    const r = rng(31);
    return Array.from({ length: 50 }, () => ({ dx: (r() - 0.5) * 2, dy: r() * 1.2, dz: 0.3 + r() * 0.9, d: r() * 0.5, s: 0.006 + r() * 0.01 }));
  }, []);
  const pk = clamp((t - WIPE_A) / 1.3);
  return (
    <group>
      {t > 1.5 && t < 6.7
        ? motes.map((m, i) => (
            <mesh key={i} position={[m.x + Math.sin(t * m.sp + m.ph) * 0.05, m.y + Math.sin(t * 0.7 + m.ph) * 0.04, m.z]} scale={0.006}>
              <sphereGeometry args={[1, 6, 4]} />
              <meshBasicMaterial color="#ffe6b8" transparent opacity={0.65} />
            </mesh>
          ))
        : null}
      {pk > 0 && pk < 1
        ? puff.map((p, i) => {
            const k = clamp((pk - p.d * 0.5) / 0.6);
            if (k <= 0) return null;
            const o = glassPoint(lerp(980, 430, clamp((WIPE_A + p.d * 0.6 - WIPE_A) / (WIPE_B - WIPE_A))), HEART.cy, 0.05);
            return (
              <mesh key={"p" + i} position={[o.x + p.dx * 0.25 * k, o.y + p.dy * 0.3 * k, o.z + p.dz * 0.35 * k]} scale={p.s * (1 + k)}>
                <sphereGeometry args={[1, 6, 4]} />
                <meshBasicMaterial color="#f2e6cc" transparent opacity={0.7 * (1 - k)} depthWrite={false} fog={false} />
              </mesh>
            );
          })
        : null}
    </group>
  );
};

// voice rings from the friend's mouth: her name being called
const CallRings: React.FC<{ t: number; from: THREE.Vector3 }> = ({ t, from }) => {
  if (t < 13.9 || t > 15.4) return null;
  return (
    <group position={from} rotation={[0, Math.PI, 0]}>
      {[0, 0.28, 0.56].map((d, i) => {
        const k = ((t - 13.9 - d) % 0.84) / 0.84;
        if (t - 13.9 - d < 0) return null;
        return (
          <mesh key={i} position={[0, 0, k * 0.9]} scale={0.12 + k * 0.5}>
            <torusGeometry args={[1, 0.035, 6, 32, Math.PI * 0.7]} />
            <meshBasicMaterial color="#ffe08a" transparent opacity={(1 - k) * 0.9} />
          </mesh>
        );
      })}
    </group>
  );
};

const FloatHearts: React.FC<{ t: number; at: THREE.Vector3; t0: number; t1: number }> = ({ t, at, t0, t1 }) => {
  if (t < t0 || t > t1) return null;
  const r = rng(77);
  return (
    <group position={at}>
      {Array.from({ length: 6 }).map((_, i) => {
        const d = r() * 0.7, sx = (r() - 0.5) * 0.5, sz = (r() - 0.5) * 0.2;
        const k = clamp((t - t0 - d) / 1.1);
        if (k <= 0 || k >= 1) return null;
        const pop = Math.min(1, k * 6) * (1 - smooth((k - 0.75) / 0.25));
        return (
          <group key={i} position={[sx + Math.sin(k * 8 + i) * 0.04, k * 0.55, sz]} rotation={[0, 0, Math.PI]} scale={0.07 * pop}>
            <mesh geometry={heartGeo}>
              <meshBasicMaterial color="#ff4f73" />
            </mesh>
          </group>
        );
      })}
    </group>
  );
};

// ------------------------------------------------------------------------------------ camera
type Cam = { pos: [number, number, number]; target: [number, number, number]; fov: number; roll?: number };
function camAt(t: number): Cam {
  if (t < 1.55) {   // low dolly along the lane to the dusty car under the lamp; he walks in
    const k = Easing.inOut(Easing.quad)(clamp(t / 1.55));
    return { pos: lerp3([2.4, 0.75, 6.2], [1.35, 1.2, 3.7], k), target: lerp3([-0.6, 1.0, 0.2], [-0.9, 1.1, 0.45], k), fov: lerp(46, 40, k) };
  }
  if (t < 3.08) {   // insert, straight down on the glass: his finger draws a heart in the dust
    const k = Easing.out(Easing.quad)((t - 1.55) / 1.53);
    const c = glassPoint(HEART.cx - 40, HEART.cy + 150, 0);
    const n = V(0, -Math.sin(WS_ANG), Math.cos(WS_ANG));
    const d = lerp(1.4, 1.2, k);
    return { pos: [c.x - 0.12, c.y + n.y * d, c.z + n.z * d], target: [c.x - 0.03, c.y, c.z], fov: 44, roll: -0.04 };
  }
  if (t < 4.9) {    // over the shoulder: the names get written
    const k = (t - 3.08) / 1.82;
    return { pos: lerp3([-2.25, 1.42, 2.15], [-2.05, 1.4, 1.95], k), target: [-0.98, 1.27, 0.55], fov: 34 };
  }
  if (t < 6.66) {   // from the bonnet, low: his dreamy face
    const k = (t - 4.9) / 1.76;
    return { pos: [lerp(-1.45, -1.35, k), 1.02, lerp(1.8, 1.7, k)], target: [-0.2, 1.42, 0.62], fov: lerp(42, 38, k) };
  }
  if (t < 7.5) {    // dutch-tilt medium: he startles
    return { pos: [0.45, 1.42, -0.95], target: [-0.2, 1.45, 0.6], fov: 40, roll: -0.18 };
  }
  if (t < 8.44) {   // his point of view: the girls coming down the lane
    const k = (t - 7.5) / 0.94;
    return { pos: [0.05, 1.5, lerp(0.2, 0.0, k)], target: [1.0, 1.25, -8], fov: lerp(34, 28, k) };
  }
  if (t < 9.84) {   // close on the glass: the sleeve wipes it all away
    const k = (t - 8.44) / 1.4;
    return { pos: [lerp(-2.15, -2.05, k), 1.45, lerp(1.95, 2.05, k)], target: [-0.98, 1.27, 0.55], fov: 34, roll: 0.05 };
  }
  if (t < 12.3) {   // low wide: she passes, laughing with friends; he leans on the car
    const k = (t - 9.84) / 2.46;
    return { pos: lerp3([2.9, 0.55, 4.2], [2.7, 0.6, 3.8], k), target: lerp3([0.2, 1.25, -1.6], [0.1, 1.3, 0.2], Easing.inOut(Easing.quad)(k)), fov: 40 };
  }
  if (t < 13.52) {  // close-up: he knows
    const k = (t - 12.3) / 1.22;
    return { pos: [lerp(0.75, 0.65, k), 1.45, lerp(-0.45, -0.38, k)], target: [-0.3, 1.5, -0.05], fov: 34 };
  }
  if (t < 15.46) {  // behind him: up the lane a friend calls her name
    const k = (t - 13.52) / 1.94;
    return { pos: lerp3([0.65, 1.8, -2.7], [0.6, 1.76, -2.4], k), target: [-0.45, 1.3, 6], fov: lerp(52, 50, k) };
  }
  if (t < 16.8) {   // close-up: the smile
    const k = (t - 15.46) / 1.34;
    return { pos: [lerp(0.7, 0.58, k), 1.5, lerp(0.45, 0.38, k)], target: [-0.3, 1.52, 0.0], fov: 32 };
  }
  // crane up and back: he walks off; the street light catches the faint heart on the glass
  const k = Easing.inOut(Easing.cubic)(clamp((t - 16.8) / 3.6));
  return { pos: lerp3([0.2, 1.35, 3.1], [1.8, 4.6, 5.6], k), target: lerp3([-1.0, 1.2, 0.5], [-0.4, 0.9, -1.5], k), fov: lerp(36, 44, k) };
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
  const sky = useMemo(() => skyMat(), []);
  const h = himAt(t);
  const her = herAt(t);
  const friendCall = t >= 13.52 && t < 16.8;
  // friends: A walks ahead on her right, B just behind on her left
  const fA = { x: her.pos[0] + 0.6, z: her.pos[2] + (friendCall ? 1.1 : 0.35) };
  const fB = { x: her.pos[0] - 0.6, z: her.pos[2] - 0.3 };
  const poseA = restPose(); poseA.walk = 1; poseA.phase = t * 7.2 + 1.3; poseA.smile = 0.85; poseA.headYaw = -0.5;
  const poseB = restPose(); poseB.walk = 1; poseB.phase = t * 7.2 + 2.6; poseB.smile = 0.95; poseB.headYaw = 0.4; poseB.eyes = t % 1.6 < 0.5 ? 0 : 1; poseB.happyEyes = true;
  let aYaw = 0;
  if (friendCall) {   // friend A turns back and calls out her name
    const k = seg(t, 13.75, 14.0);
    aYaw = lerp(0, Math.PI, k);
    poseA.walk = 1 - k * 0.8;
    poseA.headYaw = 0;
    poseA.mouthO = t > 13.95 && t < 15.2 ? 0.9 : 0;
    poseA.armR = [-2.2 * k, -0.3]; poseA.elbowR = -0.3;
  }
  const trace = t > 16.8 ? seg(t, 17.6, 18.8) * 0.85 : 0;
  const headWorld = V(h.pos[0], 1.56, h.pos[2]);
  return (
    <>
      <CameraRig t={t} />
      <mesh material={sky} scale={90}>
        <sphereGeometry args={[1, 32, 16]} />
      </mesh>
      <mesh position={[-14, 26, -60]}>
        <sphereGeometry args={[2.2, 24, 16]} />
        <meshBasicMaterial color="#f4ecd2" />
      </mesh>
      <fog attach="fog" args={["#2a2e52", 12, 48]} />
      <ambientLight intensity={0.62} />
      <hemisphereLight args={["#6a78b8", "#2a2228", 0.55]} />
      <directionalLight position={[-6, 9, -10]} intensity={0.55} color="#9fb4ff" castShadow
        shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-8} shadow-camera-right={8}
        shadow-camera-top={8} shadow-camera-bottom={-8} shadow-bias={-0.0008} shadow-normalBias={0.03} />
      {/* fill on the faces */}
      <pointLight position={[1.2, 2.2, 2.0]} intensity={1.1} distance={6} color="#ffd6a8" />
      <Street />
      <Buildings />
      <Lamp base={[-2.5, 0.16, 1.6]} dir={1} target={[-1.0, 0.8, 0.6]} intensity={16} shadow />
      <Lamp base={[2.5, 0.16, -9]} dir={-1} target={[1.6, 0, -9]} intensity={14} />
      <Lamp base={[-2.5, 0.16, -19]} dir={1} target={[-1.6, 0, -19]} intensity={14} />
      <Lamp base={[2.5, 0.16, 9]} dir={-1} target={[1.6, 0, 9]} intensity={14} />
      {[[-3.4, 0.16, -5], [3.4, 0.16, 3], [3.4, 0.16, -14], [-3.4, 0.16, 7]].map((p, i) => (
        <Tree key={i} pos={p as [number, number, number]} s={0.9 + (i % 2) * 0.15} />
      ))}
      <Car pos={[CX, 0, 0]} color="#bcb2a0" t={t} dusty />
      <Car pos={[CX, 0, -6.2]} color="#7a2e2e" />
      <Car pos={[CX, 0, 6.4]} color="#2f4a6a" />
      <Car pos={[-CX + 0.1, 0, -16]} color="#d8d4ca" rotY={Math.PI} />
      <HeartTrace glow={trace} />
      {/* him */}
      {h.visible ? (
        <group position={h.pos} rotation={[0, h.yaw, 0]}>
          <group rotation={[h.lean, 0, 0]} scale={0.85}>
            <Person look={HIM} pose={h.pose} />
          </group>
        </group>
      ) : null}
      <IKArm h={h} look={HIM} />
      {/* her and friends */}
      {her.visible ? (
        <>
          <group position={her.pos} rotation={[0, her.yaw, 0]} scale={0.8}>
            <Person look={HER} pose={her.pose} />
          </group>
          <group position={[fA.x, 0, fA.z]} rotation={[0, aYaw, 0]} scale={0.78}>
            <Person look={FRIEND_A} pose={poseA} />
          </group>
          <group position={[fB.x, 0, fB.z]} scale={0.79}>
            <Person look={FRIEND_B} pose={poseB} />
          </group>
        </>
      ) : null}
      <CallRings t={t} from={V(fA.x, 1.45, fA.z - 0.1)} />
      <FloatHearts t={t} at={V(headWorld.x + 0.05, 1.82, headWorld.z)} t0={14.75} t1={16.8} />
      <FloatHearts t={t} at={V(-0.95, 1.35, 0.6)} t0={4.6} t1={6.0} />
      <Dust t={t} />
    </>
  );
};

export const Sheesha3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const line = LINES.find(([a, b]) => t >= a && t < b);
  let dip = 0;
  for (const c of CUTS) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.1);
  const flash = Math.max(0, 1 - Math.abs(t - 8.44) / 0.12);   // the panic cut
  const fade = Math.min(clamp(t / 0.35), clamp((END - t) / 0.9));
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
        <Scene t={t} />
      </ThreeCanvas>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.5) 100%)" }} />
      {line ? (
        <div style={{ position: "absolute", top: 1290, left: 60, right: 60, textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 64, lineHeight: 1.35, color: "#faf8f4", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill",
          textShadow: "0 4px 14px rgba(0,0,0,0.7)" }}>
          {line[2]}
        </div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash * 0.6 }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.45) }} />
    </AbsoluteFill>
  );
};
