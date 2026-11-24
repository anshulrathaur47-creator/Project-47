import * as THREE from "three";
import { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { G, Look, Person, Pose, Toon, plaidTexture, restPose } from "./Character";

export const DURATION = 393; // 13.1 s at 30 fps
const FPS = 30;

// ------------------------------------------------------------------------------------ helpers
const clamp = (x: number, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = (x: number) => {
  const t = clamp(x);
  return t * t * (3 - 2 * t);
};
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: number[], b: number[], t: number) => a.map((v, i) => lerp(v, b[i], t)) as [number, number, number];
const seg = (t: number, a: number, b: number) => smooth((t - a) / (b - a));
const mixCol = (a: string, b: string, t: number) => new THREE.Color(a).lerp(new THREE.Color(b), clamp(t));

const LINES: [number, number, string][] = [
  [0.1, 2.7, "उसको फ़ुर्सत नहीं मिलती"],
  [2.72, 4.0, "कि पलट कर देखे"],
  [5.38, 7.55, "उसको फ़ुर्सत नहीं मिलती"],
  [7.58, 8.95, "कि पलट कर देखे"],
  [9.04, 10.22, "हम ही दीवाने हैं"],
  [10.25, 11.34, "दीवाने बने रहते हैं"],
];
const CUTS = [2.72, 3.3, 4.0, 5.38, 9.04, 11.36];

// ------------------------------------------------------------------------------------ time of day
type Tod = { top: string; bottom: string; sun: number; sunCol: string; amb: number; lamps: number; windows: number };
const DUSK: Tod = { top: "#3a2c58", bottom: "#ffb070", sun: 2.0, sunCol: "#ffb070", amb: 0.9, lamps: 0.35, windows: 0.5 };
const MORNING: Tod = { top: "#5b9ee8", bottom: "#fff1d6", sun: 2.6, sunCol: "#fff4dc", amb: 1.5, lamps: 0, windows: 0.1 };
const NIGHT: Tod = { top: "#050914", bottom: "#1b2440", sun: 0.35, sunCol: "#8aa0d0", amb: 0.45, lamps: 1, windows: 1 };
const mixTod = (a: Tod, b: Tod, k: number): Tod => ({
  top: "#" + mixCol(a.top, b.top, k).getHexString(), bottom: "#" + mixCol(a.bottom, b.bottom, k).getHexString(),
  sun: lerp(a.sun, b.sun, k), sunCol: "#" + mixCol(a.sunCol, b.sunCol, k).getHexString(), amb: lerp(a.amb, b.amb, k),
  lamps: lerp(a.lamps, b.lamps, k), windows: lerp(a.windows, b.windows, k),
});
function todAt(t: number): Tod {
  if (t < 5.38) return mixTod(DUSK, NIGHT, seg(t, 4.2, 5.3) * 0.35);
  if (t < 6.6) return mixTod(MORNING, MORNING, 0);
  if (t < 7.8) return mixTod(MORNING, DUSK, seg(t, 6.4, 6.9));
  if (t < 9.04) return mixTod(DUSK, NIGHT, seg(t, 7.6, 8.1));
  return NIGHT;
}

// ------------------------------------------------------------------------------------ camera
type Cam = { pos: [number, number, number]; target: [number, number, number]; fov: number; up?: [number, number, number] };
function camAt(t: number): Cam {
  if (t < 2.72) {   // crane down from the rooftops into an over-the-shoulder shot
    const k = Easing.inOut(Easing.cubic)(clamp(t / 2.6));
    return { pos: lerp3([4.6, 9.5, 7.5], [1.05, 1.85, 1.3], k), target: lerp3([0, 0.6, -3], [-0.1, 1.4, -6], k), fov: lerp(46, 38, k) };
  }
  if (t < 3.3) {    // low-angle close-up of his hopeful face, slow orbit
    const k = (t - 2.72) / 0.58;
    return { pos: [lerp(0.25, 0.05, k), 1.45, lerp(-1.3, -1.25, k)], target: [0.5, 1.72, 0], fov: 36 };
  }
  if (t < 4.0) {    // her: she nearly turns back... then the phone buzzes
    return { pos: [-0.9, 1.6, -8.0], target: [0.25, 1.5, -5.3], fov: 36 };
  }
  if (t < 5.38) {   // high angle: he is left alone, petals fall
    const k = (t - 4.0) / 1.38;
    return { pos: lerp3([3.2, 6.5, 2.8], [2.6, 7.5, 2.2], k), target: [0.5, 0.6, -0.8], fov: 42 };
  }
  if (t < 9.04) {   // one long 360-degree orbit round the lamp post while the days go by
    const k = (t - 5.38) / 3.66;
    const a = -0.5 + k * Math.PI * 2;
    const r = 3.6;
    return { pos: [0.6 + r * Math.sin(a), lerp(1.5, 2.1, k), -r * Math.cos(a)], target: [0.6, 1.3, 0], fov: 40 };
  }
  if (t < 11.36) {  // dolly in to his face on the steps in the rain
    const k = Easing.inOut(Easing.quad)((t - 9.04) / 2.32);
    return { pos: lerp3([0.6, 1.5, -4.2], [0.5, 1.3, -0.95], k), target: lerp3([0.5, 1.0, 0.3], [0.5, 1.38, 0.3], k), fov: lerp(42, 34, k) };
  }
  const k = Easing.inOut(Easing.cubic)((t - 11.36) / 1.74);   // crane up: every dried rose around him
  return { pos: lerp3([0.5, 1.5, -1.8], [2.8, 7.8, -5.6], k), target: lerp3([0.5, 0.9, 0.3], [0.5, 0.4, 0.3], k), fov: 40 };
}

const CameraRig: React.FC<{ t: number }> = ({ t }) => {
  const { camera } = useThree();
  const c = camAt(t);
  const cam = camera as THREE.PerspectiveCamera;
  cam.position.set(...c.pos);
  cam.up.set(...(c.up ?? [0, 1, 0]));
  cam.fov = c.fov;
  cam.near = 0.05;
  cam.far = 200;
  cam.lookAt(new THREE.Vector3(...c.target));
  cam.updateProjectionMatrix();
  return null;
};

// ------------------------------------------------------------------------------------ world
const skyMat = (top: string, bottom: string) =>
  new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: { top: { value: new THREE.Color(top) }, bottom: { value: new THREE.Color(bottom) } },
    vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ",
    fragmentShader: "uniform vec3 top; uniform vec3 bottom; varying vec3 vP; void main(){ float h = clamp(vP.y*1.6+0.15,0.0,1.0); gl_FragColor = vec4(mix(bottom, top, h),1.0);} ",
  });

function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

const Buildings: React.FC<{ windows: number }> = ({ windows }) => {
  const data = useMemo(() => {
    const r = rng(7);
    const b: { x: number; z: number; w: number; h: number; d: number; col: string }[] = [];
    const win: { x: number; y: number; z: number; side: number; on: boolean }[] = [];
    for (const side of [-1, 1]) {
      let z = 8;
      while (z > -46) {
        const d = 3 + r() * 3, h = 4 + r() * 8, w = 3;
        const x = side * (4.2 + w / 2);
        b.push({ x, z: z - d / 2, w, h, d: d - 0.2, col: ["#6b4f4a", "#58606e", "#7a6a58", "#4f5868"][Math.floor(r() * 4)] });
        for (let yy = 1.6; yy < h - 0.6; yy += 1.3)
          for (let zz = z - 0.7; zz > z - d + 0.4; zz -= 1.1) win.push({ x: side * 4.19, y: yy, z: zz, side, on: r() < 0.55 });
        z -= d;
      }
    }
    return { b, win };
  }, []);
  return (
    <group>
      {data.b.map((o, i) => (
        <mesh key={i} position={[o.x, o.h / 2, o.z]} receiveShadow castShadow>
          <boxGeometry args={[o.w, o.h, o.d]} />
          <meshToonMaterial color={o.col} />
        </mesh>
      ))}
      {data.win.map((w, i) => (
        <mesh key={"w" + i} position={[w.x, w.y, w.z]} rotation={[0, (w.side * -Math.PI) / 2, 0]}>
          <planeGeometry args={[0.55, 0.7]} />
          <meshBasicMaterial color={w.on ? new THREE.Color("#ffd28a").multiplyScalar(0.25 + 0.75 * windows) : new THREE.Color("#2a3040")} />
        </mesh>
      ))}
    </group>
  );
};

const LampPost: React.FC<{ pos: [number, number, number]; on: number; shadow?: boolean }> = ({ pos, on, shadow }) => (
  <group position={pos}>
    <mesh position={[0, 1.7, 0]} castShadow>
      <cylinderGeometry args={[0.045, 0.06, 3.4, 12]} />
      <meshToonMaterial color="#3a404c" />
    </mesh>
    <mesh position={[-0.28, 3.38, 0]} rotation={[0, 0, Math.PI / 2]}>
      <cylinderGeometry args={[0.03, 0.03, 0.6, 8]} />
      <meshToonMaterial color="#3a404c" />
    </mesh>
    <mesh position={[-0.55, 3.3, 0]}>
      <sphereGeometry args={[0.11, 16, 12]} />
      <meshBasicMaterial color={new THREE.Color("#fff0c8").multiplyScalar(0.35 + 0.65 * on)} />
    </mesh>
    {on > 0.05 ? (
      <>
        <spotLight position={[-0.55, 3.25, 0]} target-position={[-0.55, 0, 0]} angle={0.75} penumbra={0.6} intensity={18 * on}
          distance={9} decay={1.6} color="#ffcf8a" castShadow={shadow} shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-bias={-0.0008} shadow-normalBias={0.03} />
        <mesh position={[-0.55, 1.65, 0]}>
          <coneGeometry args={[1.25, 3.2, 32, 1, true]} />
          <meshBasicMaterial color="#ffd9a0" transparent opacity={0.07 * on} depthWrite={false} side={THREE.DoubleSide} />
        </mesh>
      </>
    ) : null}
  </group>
);

const Street: React.FC<{ tod: Tod; wet: number }> = ({ tod, wet }) => (
  <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -15]} receiveShadow>
      <planeGeometry args={[8.4, 70]} />
      <meshStandardMaterial color={mixCol("#3b3a40", "#1d222c", wet)} roughness={lerp(0.9, 0.35, wet)} metalness={lerp(0, 0.4, wet)} />
    </mesh>
    {[-1, 1].map((s) => (
      <mesh key={s} position={[s * 3.2, 0.08, -15]} receiveShadow>
        <boxGeometry args={[2, 0.16, 70]} />
        <meshToonMaterial color="#8a8680" />
      </mesh>
    ))}
    {Array.from({ length: 12 }).map((_, i) => (
      <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 6 - i * 5]}>
        <planeGeometry args={[0.12, 2]} />
        <meshBasicMaterial color={mixCol("#d8d2c0", "#6a6a60", tod.lamps)} />
      </mesh>
    ))}
    {[-12, -24, -36].map((z) => (
      <LampPost key={z} pos={[1.9, 0.16, z]} on={tod.lamps} />
    ))}
    <LampPost pos={[1.9, 0.16, -0.2]} on={tod.lamps} shadow />
    {/* the steps he ends up sitting on */}
    <mesh position={[0.55, 0.24, 0.5]} receiveShadow castShadow>
      <boxGeometry args={[2.4, 0.48, 0.7]} />
      <meshToonMaterial color="#9a8f84" />
    </mesh>
    <mesh position={[0.55, 0.12, 0.05]} receiveShadow castShadow>
      <boxGeometry args={[2.4, 0.24, 0.3]} />
      <meshToonMaterial color="#a69a8e" />
    </mesh>
  </group>
);

// ------------------------------------------------------------------------------------ props
const Rose: React.FC<{ wilt?: number; scale?: number; rotation?: [number, number, number] }> = ({ wilt = 0, scale = 1, rotation }) => (
  <group scale={scale} rotation={rotation}>
    <mesh position={[0, 0.14, 0]}>
      <cylinderGeometry args={[0.008, 0.008, 0.3, 6]} />
      <meshToonMaterial color="#2f7a3a" />
    </mesh>
    <Toon geom={G.sphere} color={"#" + mixCol("#d11c3c", "#6e2e34", wilt).getHexString()} position={[0, 0.3 - wilt * 0.03, 0]}
      scale={[0.05, 0.06 * (1 - wilt * 0.3), 0.05]} outline={0.01} />
    <mesh position={[0.03, 0.12, 0]} rotation={[0, 0, -0.8]} scale={[0.03, 0.012, 0.015]}>
      <sphereGeometry args={[1, 8, 6]} />
      <meshToonMaterial color="#3d8a46" />
    </mesh>
  </group>
);

const GiftBox: React.FC = () => (
  <group>
    <Toon geom={G.box} color="#c0284a" scale={[0.2, 0.15, 0.14]} outline={0.006} />
    <mesh scale={[0.04, 0.152, 0.142]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshToonMaterial color="#f0c860" />
    </mesh>
  </group>
);

const Card: React.FC = () => (
  <group rotation={[0.2, 0, 0]}>
    <Toon geom={G.box} color="#f6ead8" scale={[0.14, 0.18, 0.01]} outline={0.01} />
    <mesh position={[0, 0.01, 0.007]} scale={0.035}>
      <sphereGeometry args={[1, 12, 8]} />
      <meshBasicMaterial color="#e03a5a" />
    </mesh>
  </group>
);

const Phone: React.FC<{ glow: number }> = ({ glow }) => (
  <group>
    <mesh scale={[0.07, 0.13, 0.012]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshBasicMaterial color="#1a1a20" />
    </mesh>
    <mesh position={[0, 0, 0.007]} scale={[0.06, 0.115, 1]}>
      <planeGeometry args={[1, 1]} />
      <meshBasicMaterial color={new THREE.Color("#9fd0ff").multiplyScalar(0.6 + glow)} />
    </mesh>
    <pointLight position={[0, 0, 0.15]} intensity={0.15 + glow * 0.6} distance={0.8} color="#9fd0ff" />
  </group>
);

const heartShape = (() => {
  const s = new THREE.Shape();
  s.moveTo(0, -0.3);
  s.bezierCurveTo(-0.6, 0.1, -0.35, 0.55, 0, 0.25);
  s.bezierCurveTo(0.35, 0.55, 0.6, 0.1, 0, -0.3);
  return new THREE.ExtrudeGeometry(s, { depth: 0.12, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.04, bevelSegments: 3 });
})();

// ------------------------------------------------------------------------------------ the people
const HIM: Look = { skin: "#d9a07a", hair: "#151216", hairStyle: "curly", shirt: "#8c2430", inner: "#1d1d22", pants: "#2c3a5a",
  shoes: "#f2f2f2", face: true };
const HER: Look = { skin: "#c98f6c", hair: "#2a1a14", hairStyle: "ponytail", shirt: "#e6a92a", inner: "#f4e4c0", pants: "#f2ece0",
  shoes: "#d04a5a", face: true };
const FRIEND_A: Look = { ...HER, hair: "#3a2418", shirt: "#4a8fd8", pants: "#2a2a34", face: false };
const FRIEND_B: Look = { ...HER, hair: "#18120e", shirt: "#d85a8a", pants: "#e8e2d8", face: false };

function hisPose(t: number): Pose {
  const p = restPose();
  p.headYaw = 0;
  // holding: the rose at the chest
  const chest = (pp: Pose, side: "R" | "L" | "both") => {
    if (side !== "L") { pp.armR = [-0.55, -0.12]; pp.elbowR = -1.35; }
    if (side !== "R") { pp.armL = [-0.55, 0.12]; pp.elbowL = -1.35; }
  };
  if (t < 4.0) {
    chest(p, "R");
    p.smile = lerp(0.7, -0.25, seg(t, 3.35, 3.7));
    p.brow = lerp(-0.1, 0.75, seg(t, 3.35, 3.7));
    p.eyes = lerp(1, 0.7, seg(t, 3.35, 3.7));
    p.headPitch = lerp(-0.05, 0.12, seg(t, 3.35, 3.8));
  } else if (t < 5.38) {   // the rose sinks to his side
    const k = seg(t, 4.1, 4.7);
    p.armR = [lerp(-0.55, 0, k), -0.12];
    p.elbowR = lerp(-1.35, 0.1, k);
    p.smile = -0.3; p.brow = 0.85; p.eyes = 0.6; p.headPitch = 0.3;
  } else if (t < 9.04) {   // waiting at the lamp post, a new gift each day; he turns to watch her pass
    const segs: [number, number, "both" | "R"][] = [[5.38, 6.6, "both"], [6.6, 7.8, "R"], [7.8, 9.04, "R"]];
    for (const [a, b, side] of segs) {
      if (t >= a && t < b) {
        chest(p, side);
        const u = (t - a) / (b - a);
        const her = herCross(t);
        p.headYaw = clamp(Math.atan2(her.x - 0.5, -(her.z - 0)) * -1 * 0.8, -1.0, 1.0);
        p.smile = u < 0.55 ? 0.7 : lerp(0.7, -0.2, seg(u, 0.55, 0.85));
        p.brow = u < 0.55 ? -0.1 : lerp(-0.1, 0.7, seg(u, 0.55, 0.85));
        p.eyes = u < 0.55 ? 1 : 0.75;
      }
    }
  } else {                 // on the steps in the rain, smiling at his rose with wet eyes
    p.sit = 1;
    chest(p, "both");
    p.armL = [-0.75, 0.25]; p.armR = [-0.75, -0.25]; p.elbowL = -1.1; p.elbowR = -1.1;
    const up = seg(t, 10.2, 10.6);
    p.headPitch = lerp(0.3, -0.12, up);
    p.smile = lerp(0.45, 0.85, up);
    p.brow = 0.6;
    p.eyes = t > 11.9 ? lerp(0.85, 0.1, seg(t, 11.9, 12.4)) : lerp(0.65, 0.85, up);
    p.tear = clamp((t - 10.3) / 1.0);
    p.tearAlpha = t > 10.3 ? 0.95 : 0;
    p.lookY = lerp(-0.6, 0.5, up);
  }
  return p;
}

// her crossings during the orbit (morning with friends, dusk on the phone, night in a hurry)
function herCross(t: number): { x: number; z: number; yaw: number; visible: boolean; speed: number } {
  if (t >= 5.45 && t < 6.6) return { x: lerp(-5.5, 6.5, (t - 5.45) / 1.15), z: -3.0, yaw: Math.PI / 2, visible: true, speed: 1 };
  if (t >= 6.65 && t < 7.8) return { x: lerp(6.5, -5.5, (t - 6.65) / 1.15), z: -3.4, yaw: -Math.PI / 2, visible: true, speed: 1 };
  if (t >= 7.85 && t < 9.0) return { x: lerp(-5.5, 6.5, (t - 7.85) / 1.15), z: -3.0, yaw: Math.PI / 2, visible: true, speed: 1.4 };
  return { x: 99, z: 0, yaw: 0, visible: false, speed: 0 };
}

function herState(t: number): { pos: [number, number, number]; yaw: number; pose: Pose; phone: number; visible: boolean } {
  const p = restPose();
  p.armR = [-0.6, -0.15]; p.elbowR = -1.3;   // phone in hand
  if (t < 5.38) {
    // walks away, pauses on "देखे" and almost turns back, then the phone buzzes and she walks on
    const pauseA = 3.3, pauseB = 3.78;
    let z: number;
    if (t < pauseA) z = lerp(-1.9, -5.3, t / pauseA);
    else if (t < pauseB) z = -5.3;
    else z = lerp(-5.3, -9.5, (t - pauseB) / (5.38 - pauseB));
    const walking = t < pauseA || t >= pauseB;
    p.walk = walking ? 1 : 0;
    p.phase = t * 7;
    p.headYaw = t >= pauseA && t < pauseB ? 0.75 * Math.sin(Math.PI * clamp((t - pauseA) / (pauseB - pauseA))) : 0;
    p.headPitch = 0.2;
    p.smile = 0.2;
    const buzz = t >= 3.62 && t < 3.85 ? 1 : 0;
    return { pos: [0.25, 0, z], yaw: Math.PI, pose: p, phone: buzz, visible: true };
  }
  const c = herCross(t);
  p.walk = 1;
  p.phase = t * 7 * c.speed;
  p.headPitch = 0.2;
  if (t >= 8.0 && t < 8.4) p.headYaw = -0.6 * Math.sin(Math.PI * (t - 8.0) / 0.4);   // night: she almost looks
  if (t >= 5.38 && t < 6.6) { p.armR = [0, -0.12]; p.elbowR = 0.2; p.smile = 0.9; }  // morning: laughing with friends
  return { pos: [c.x, 0, c.z], yaw: c.yaw, pose: p, phone: 0, visible: c.visible };
}

// ------------------------------------------------------------------------------------ fx
const Rain: React.FC<{ t: number; amount: number }> = ({ t, amount }) => {
  const drops = useMemo(() => {
    const r = rng(3);
    return Array.from({ length: 260 }, () => ({ x: (r() - 0.5) * 9, z: -6 + r() * 9, y0: r() * 8, sp: 7 + r() * 4 }));
  }, []);
  if (amount <= 0.01) return null;
  return (
    <group>
      {drops.slice(0, Math.floor(260 * amount)).map((d, i) => {
        const y = 8 - ((d.y0 + t * d.sp) % 8);
        return (
          <mesh key={i} position={[d.x, y, d.z]} rotation={[0, 0, 0.12]}>
            <boxGeometry args={[0.008, 0.28, 0.008]} />
            <meshBasicMaterial color="#b8c8e8" transparent opacity={0.5} />
          </mesh>
        );
      })}
    </group>
  );
};

const Petals: React.FC<{ t: number }> = ({ t }) => {
  if (t < 4.1 || t > 5.4) return null;
  const r = rng(11);
  return (
    <group>
      {Array.from({ length: 10 }).map((_, i) => {
        const d = r() * 0.5, sx = (r() - 0.5) * 0.5, sz = (r() - 0.5) * 0.5;
        const k = clamp((t - 4.1 - d) / 1.0);
        if (k <= 0) return null;
        return (
          <mesh key={i} position={[0.75 + sx * k, lerp(1.0, 0.03, k), -0.2 + sz * k]} rotation={[k * 6, k * 4, 0]} scale={[0.03, 0.006, 0.02]}>
            <sphereGeometry args={[1, 8, 6]} />
            <meshToonMaterial color="#c81c3a" />
          </mesh>
        );
      })}
    </group>
  );
};

const DriedRoses: React.FC<{ show: number }> = ({ show }) => {
  const spots = useMemo(() => {
    const r = rng(5);
    return Array.from({ length: 22 }, (_, i) => ({ x: -0.55 + r() * 2.2, z: 0.25 + r() * 0.5, rot: r() * 6, onTop: i % 3 !== 0 }));
  }, []);
  if (show <= 0) return null;
  return (
    <group>
      {spots.map((s, i) => (
        <group key={i} position={[s.x, s.onTop ? 0.49 : 0.25, s.z - (s.onTop ? 0 : 0.45)]} rotation={[0, s.rot, Math.PI / 2 - 0.15]}>
          <Rose wilt={0.85} scale={0.8} />
        </group>
      ))}
    </group>
  );
};

// ------------------------------------------------------------------------------------ scene
const Scene: React.FC<{ t: number }> = ({ t }) => {
  const tod = todAt(t);
  const sky = useMemo(() => skyMat(tod.top, tod.bottom), [tod.top, tod.bottom]);
  const shirtMap = useMemo(() => plaidTexture("#8c2430", "#1d1d22"), []);
  const him = hisPose(t);
  const her = herState(t);
  const wet = t > 8.9 ? smooth((t - 8.9) / 0.6) : 0;
  const lookHim = { ...HIM, shirtMap };
  // what he holds
  let handR: React.ReactNode = null;
  let handL: React.ReactNode = null;
  if (t < 5.38) handR = <Rose rotation={[-0.4, 0, t > 4.1 ? lerp(0, 2.2, seg(t, 4.1, 4.7)) : 0.1]} wilt={0} />;
  else if (t < 6.6) handR = <group position={[-0.08, 0.02, 0.06]}><GiftBox /></group>;
  else if (t < 7.8) handR = <Card />;
  else if (t < 9.04) handR = <Rose rotation={[-0.4, 0, 0.1]} />;
  else handR = <group position={[-0.08, 0.02, 0.04]}><Rose rotation={[-0.2, 0, 0.3]} /></group>;
  const heartK = (t0: number) => (t >= t0 && t < t0 + 0.9 ? 1 - smooth((t - t0 - 0.55) / 0.35) : 0);
  const hk = Math.max(heartK(9.44), heartK(10.28));
  const beat = 1 + 0.15 * Math.max(Math.exp(-(((t - 9.56) / 0.08) ** 2)), Math.exp(-(((t - 10.4) / 0.08) ** 2)));
  return (
    <>
      <CameraRig t={t} />
      <mesh material={sky} scale={80}>
        <sphereGeometry args={[1, 32, 16]} />
      </mesh>
      <fog attach="fog" args={[tod.bottom, 14, 55]} />
      <ambientLight intensity={tod.amb} />
      <hemisphereLight args={[tod.top, "#2a2420", 0.4]} />
      <directionalLight position={[5, 10, 8]} intensity={tod.sun} color={tod.sunCol} castShadow
        shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-8} shadow-camera-right={8}
        shadow-camera-top={8} shadow-camera-bottom={-8} shadow-bias={-0.0008} shadow-normalBias={0.03} />
      <Street tod={tod} wet={wet} />
      <Buildings windows={tod.windows} />
      {/* him: facing down the street (-z) */}
      <group position={[0.5, him.sit > 0.5 ? 0.07 : 0.16, him.sit > 0.5 ? 0.35 : 0]} rotation={[0, Math.PI, 0]} scale={0.85}>
        <Person look={lookHim} pose={him} handR={handR} handL={handL} />
      </group>
      {/* her */}
      {her.visible ? (
        <group position={[her.pos[0], 0.0, her.pos[2]]} rotation={[0, her.yaw, 0]} scale={0.8}>
          <Person look={HER} pose={her.pose} handR={t < 5.38 || t >= 6.6 ? <Phone glow={her.phone} /> : null} />
        </group>
      ) : null}
      {t >= 5.45 && t < 6.6 ? (
        [-1, 1].map((s) => {
          const c = herCross(t);
          const pp = restPose();
          pp.walk = 1;
          pp.phase = t * 7 + s;
          return (
            <group key={s} position={[c.x - 0.8 * (s > 0 ? 1 : 0.5), 0, c.z + s * 0.6]} rotation={[0, c.yaw, 0]} scale={0.8}>
              <Person look={s > 0 ? FRIEND_A : FRIEND_B} pose={pp} />
            </group>
          );
        })
      ) : null}
      <Petals t={t} />
      <DriedRoses show={t >= 9.04 ? 1 : 0} />
      <Rain t={t} amount={t > 8.85 ? clamp((t - 8.85) / 0.4) : 0} />
      {hk > 0.01 ? (
        <group position={[1.25, 1.95, 0.1]} rotation={[0, Math.PI, Math.PI]} scale={0.28 * beat}>
          <mesh geometry={heartShape}>
            <meshBasicMaterial color={new THREE.Color("#ff3a5a").multiplyScalar(0.8 + 0.4 * hk)} transparent opacity={hk} />
          </mesh>
          <pointLight intensity={0.5 * hk} distance={1.2} color="#ff4a6a" />
        </group>
      ) : null}
    </>
  );
};

export const Fursat3D: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const line = LINES.find(([a, b]) => t >= a && t < b);
  let dip = 0;
  for (const c of CUTS) dip = Math.max(dip, 1 - Math.abs(t - c) / 0.1);
  const fade = Math.min(clamp(t / 0.35), clamp((13.1 - t) / 0.9));
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <ThreeCanvas width={1080} height={1920} shadows camera={{ fov: 40, position: [0, 2, 6] }}>
        <Scene t={t} />
      </ThreeCanvas>
      {/* vignette */}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)" }} />
      {line ? (
        <div style={{ position: "absolute", top: 1290, width: "100%", textAlign: "center", fontFamily: "'Noto Serif Devanagari', serif",
          fontWeight: 700, fontSize: 66, color: "#faf8f4", WebkitTextStroke: "3px #0c0e18", paintOrder: "stroke fill",
          textShadow: "0 4px 14px rgba(0,0,0,0.7)" }}>
          {line[2]}
        </div>
      ) : null}
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: Math.max(1 - fade, dip * 0.45) }} />
    </AbsoluteFill>
  );
};
