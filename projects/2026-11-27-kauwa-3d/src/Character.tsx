import * as THREE from "three";
import { useMemo } from "react";

// Toon mesh with an inverted-hull outline: the cartoon 3D look.
export const Toon: React.FC<{
  geom: THREE.BufferGeometry;
  color: string;
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number] | number;
  outline?: number;
  emissive?: string;
  emissiveIntensity?: number;
  map?: THREE.Texture;
  castShadow?: boolean;
}> = ({ geom, color, position, rotation, scale, outline = 0.012, emissive, emissiveIntensity = 0, map, castShadow = true }) => {
  const s = typeof scale === "number" ? [scale, scale, scale] : scale ?? [1, 1, 1];
  return (
    <group position={position} rotation={rotation} scale={s as [number, number, number]}>
      <mesh geometry={geom} castShadow={castShadow} receiveShadow>
        <meshToonMaterial color={color} emissive={emissive ?? "#000000"} emissiveIntensity={emissiveIntensity} map={map ?? null} />
      </mesh>
      {outline > 0 ? (
        <mesh geometry={geom} scale={[1 + outline * 4, 1 + outline * 4, 1 + outline * 4]}>
          <meshBasicMaterial color="#0e0e16" side={THREE.BackSide} />
        </mesh>
      ) : null}
    </group>
  );
};

export const G = {
  sphere: new THREE.SphereGeometry(1, 32, 24),
  capsule: new THREE.CapsuleGeometry(1, 1, 8, 16),
  box: new THREE.BoxGeometry(1, 1, 1),
  cyl: new THREE.CylinderGeometry(1, 1, 1, 24),
  torusArc: new THREE.TorusGeometry(1, 0.18, 8, 24, Math.PI),
};

export function plaidTexture(base: string, line: string): THREE.Texture {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const x = c.getContext("2d")!;
  x.fillStyle = base;
  x.fillRect(0, 0, 128, 128);
  x.globalAlpha = 0.45;
  x.fillStyle = line;
  for (let i = 0; i < 128; i += 32) {
    x.fillRect(i, 0, 10, 128);
    x.fillRect(0, i, 128, 10);
  }
  x.globalAlpha = 0.25;
  x.fillStyle = "#000000";
  for (let i = 16; i < 128; i += 32) {
    x.fillRect(i, 0, 3, 128);
    x.fillRect(0, i, 128, 3);
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(2, 2);
  return t;
}

export type Pose = {
  walk: number;          // 0..1 walk amount
  phase: number;         // walk phase (radians)
  armL: [number, number]; // [forward swing x-rotation, outward z-rotation] for the upper arm
  armR: [number, number];
  elbowL: number;        // forearm bend
  elbowR: number;
  headYaw: number;
  headPitch: number;
  headRoll: number;
  sit: number;           // 0..1 (sitting on a step)
  smile: number;         // -1 frown .. 1 smile
  brow: number;          // 0 neutral .. 1 sad (inner ends up)
  eyes: number;          // 1 open .. 0 closed
  lookX: number;
  lookY: number;
  tear: number;          // 0..1 tear progress, <0 none
  tearAlpha: number;
  armSwing?: number;     // how much the arms swing while walking (0 = hands in pockets)
  hideArmR?: boolean;    // the right arm is drawn separately (world-space IK)
  mouthO?: number;       // 0..1 surprised "o" mouth
  blush?: number;        // blush strength
  happyEyes?: boolean;   // closed eyes drawn as happy arcs
  mask?: number;         // 0 = smiley mask lowered/away, 1 = held over the face
  smirk?: number;        // 0..1 lopsided, mean smirk
};

export const restPose = (): Pose => ({
  walk: 0, phase: 0, armL: [0, 0.12], armR: [0, -0.12], elbowL: 0.15, elbowR: 0.15, headYaw: 0, headPitch: 0, headRoll: 0,
  sit: 0, smile: 0.3, brow: 0, eyes: 1, lookX: 0, lookY: 0, tear: -1, tearAlpha: 0,
});

export type Look = {
  skin: string; hair: string; hairStyle: "curly" | "ponytail" | "short" | "long" | "bun" | "receding" | "hood" | "monkey" | "turban"; shirt: string; shirtMap?: THREE.Texture; inner: string;
  pants: string; shoes: string; face: boolean;
  beard?: string;      // beard + moustache colour
  eyeMask?: boolean;   // a thief's black cloth mask over the lower face
  pantsMap?: THREE.Texture;
  tail?: string;       // monkey tail colour
  moustache?: string;  // moustache only
  muzzle?: string;     // monkey muzzle colour
};

const Limb: React.FC<{ len: number; r: number; color: string; map?: THREE.Texture }> = ({ len, r, color, map }) => (
  <Toon geom={G.capsule} color={color} map={map} position={[0, -len / 2, 0]} scale={[r, len / 2 - r * 0.2, r]} />
);

// A stylised anime-like person built from primitives, rigged by a Pose. Origin at the feet, facing +z.
export const Person: React.FC<{ look: Look; pose: Pose; children?: React.ReactNode; handR?: React.ReactNode; handL?: React.ReactNode }> = ({
  look, pose, handR, handL,
}) => {
  const p = pose;
  const legSwing = Math.sin(p.phase) * 0.55 * p.walk;
  const bob = Math.abs(Math.sin(p.phase)) * 0.04 * p.walk;
  const hipY = 0.95 - p.sit * 0.47;
  const hairBits = useMemo(() => {
    const out: [number, number, number, number][] = [];
    for (let i = 0; i < 26; i++) {
      const a = (i / 26) * Math.PI * 2;
      const ring = i % 3;
      const y = 0.06 + ring * 0.07;
      const r = 0.2 - ring * 0.035;
      const front = Math.sin(a) > 0.45;   // the part of the ring over the face
      if (front && ring < 2) continue;
      out.push([Math.cos(a) * r, front ? y + 0.06 : y, Math.sin(a) * r * 0.95 - 0.02, 0.075 - ring * 0.008]);
    }
    out.push([0, 0.26, -0.02, 0.09], [0.06, 0.22, 0.1, 0.065], [-0.07, 0.21, 0.09, 0.065], [0.0, 0.2, 0.13, 0.055]);
    return out;
  }, []);
  return (
    <group position={[0, bob, 0]}>
      {/* legs */}
      {[-1, 1].map((s) => {
        const swing = s * legSwing;
        const thigh = p.sit > 0.5 ? -1.45 : swing;
        const knee = p.sit > 0.5 ? 1.45 : Math.max(0, -Math.sin(p.phase + (s > 0 ? 0 : Math.PI))) * 0.7 * p.walk;
        return (
          <group key={s} position={[s * 0.1, hipY, 0]} rotation={[thigh, 0, 0]}>
            <Limb len={0.46} r={0.075} color={look.pants} map={look.pantsMap} />
            <group position={[0, -0.46, 0]} rotation={[knee, 0, 0]}>
              <Limb len={0.44} r={0.065} color={look.pants} map={look.pantsMap} />
              <Toon geom={G.box} color={look.shoes} position={[0, -0.46, 0.05]} scale={[0.12, 0.08, 0.24]} />
            </group>
          </group>
        );
      })}
      {/* torso */}
      <group position={[0, hipY, 0]}>
        <Toon geom={G.capsule} color={look.shirt} map={look.shirtMap} position={[0, 0.3, 0]} scale={[0.2, 0.2, 0.13]} />
        <Toon geom={G.box} color={look.inner} position={[0, 0.33, 0.1]} scale={[0.1, 0.42, 0.06]} outline={0} />
        {look.tail ? (
          <group position={[0, 0.05, -0.12]}>
            {Array.from({ length: 7 }).map((_, k) => {
              const a = k * 0.32 + 0.25 * Math.sin(p.phase * 0.5 + k * 0.6);
              return <Toon key={k} geom={G.sphere} color={look.tail!} position={[0.03 * Math.sin(k), 0.08 * k - 0.04 * k * k * 0.12, -0.06 * k - 0.02 * Math.sin(a)]} scale={0.035} outline={0.01} />;
            })}
          </group>
        ) : null}
        {/* arms */}
        {[-1, 1].map((s) => {
          const arm = s < 0 ? p.armL : p.armR;
          const elbow = s < 0 ? p.elbowL : p.elbowR;
          const swing = -s * legSwing * 0.6 * (p.armSwing ?? 1);
          if (s > 0 && p.hideArmR) return null;
          return (
            <group key={s} position={[s * 0.25, 0.6, 0]} rotation={[arm[0] + swing, 0, arm[1]]}>
              <Limb len={0.32} r={0.06} color={look.shirt} map={look.shirtMap} />
              <group position={[0, -0.32, 0]} rotation={[elbow, 0, 0]}>
                <Limb len={0.3} r={0.052} color={look.shirt} map={look.shirtMap} />
                <Toon geom={G.sphere} color={look.skin} position={[0, -0.33, 0]} scale={[0.042, 0.05, 0.035]} outline={0.008} />
                <group position={[0, -0.36, 0.02]}>{s < 0 ? handL : handR}</group>
              </group>
            </group>
          );
        })}
        {/* neck + head */}
        <Toon geom={G.cyl} color={look.skin} position={[0, 0.68, 0]} scale={[0.055, 0.1, 0.055]} outline={0} />
        <group position={[0, 0.88, 0]} rotation={[p.headPitch, p.headYaw, p.headRoll]}>
          <Toon geom={G.sphere} color={look.skin} scale={[0.19, 0.21, 0.19]} />
          {look.face ? <Face pose={p} /> : null}
          {(p.mask ?? 0) > 0.01 ? <Mask k={p.mask ?? 0} /> : null}
          <Hair look={look} bits={hairBits} />
          {look.beard ? <Beard color={look.beard} /> : null}
          {look.eyeMask ? <ClothMask /> : null}
          {look.moustache ? <Toon geom={G.capsule} color={look.moustache} position={[0, -0.06, 0.178]} rotation={[0, 0, Math.PI / 2]} scale={[0.02, 0.05, 0.02]} outline={0.006} /> : null}
        </group>
      </group>
    </group>
  );
};

const Hair: React.FC<{ look: Look; bits: [number, number, number, number][] }> = ({ look, bits }) => {
  const c = look.hair;
  if (look.hairStyle === "curly")
    return <>{bits.map(([x, y, z, r], i) => <Toon key={i} geom={G.sphere} color={c} position={[x, y, z]} scale={r} outline={0.02} />)}</>;
  if (look.hairStyle === "turban")   // a wrapped pagdi with a tail of cloth
    return (
      <>
        <Toon geom={G.sphere} color="#1a1410" position={[0, -0.02, -0.06]} scale={[0.19, 0.16, 0.16]} />
        <Toon geom={G.sphere} color={c} position={[0, 0.1, -0.01]} scale={[0.225, 0.17, 0.215]} />
        {[0, 1, 2].map((k) => <mesh key={k} position={[0, 0.06 + k * 0.05, 0]} rotation={[0.25 - k * 0.12, 0, 0]} scale={[0.228 - k * 0.02, 0.2 - k * 0.02, 0.22 - k * 0.02]}><torusGeometry args={[1, 0.06, 6, 24]} /><meshToonMaterial color={k % 2 ? "#ffffff" : c} /></mesh>)}
        <Toon geom={G.box} color={c} position={[0.05, -0.12, -0.2]} rotation={[0.3, 0, 0.1]} scale={[0.06, 0.2, 0.02]} outline={0.006} />
      </>
    );
  if (look.hairStyle === "monkey")   // fur cap, big round ears
    return (
      <>
        <Toon geom={G.sphere} color={c} position={[0, 0.05, -0.03]} scale={[0.205, 0.2, 0.2]} />
        {[-1, 1].map((s) => (
          <group key={s} position={[s * 0.2, 0.0, -0.02]}>
            <Toon geom={G.sphere} color={c} scale={[0.04, 0.085, 0.085]} />
            <Toon geom={G.sphere} color={look.muzzle ?? "#e0b088"} position={[s * 0.012, 0, 0.01]} scale={[0.03, 0.06, 0.06]} outline={0} />
          </group>
        ))}
      </>
    );
  if (look.hairStyle === "receding")   // grey hair at the back and sides, bald on top
    return (
      <>
        <Toon geom={G.sphere} color={c} position={[0, 0.0, -0.06]} scale={[0.2, 0.17, 0.17]} />
        {[-1, 1].map((s) => <Toon key={s} geom={G.sphere} color={c} position={[s * 0.16, 0.0, 0.0]} scale={[0.05, 0.1, 0.09]} />)}
      </>
    );
  if (look.hairStyle === "hood")   // a dark cloth hood wrapped round the head
    return (
      <>
        <Toon geom={G.sphere} color={c} position={[0, 0.05, -0.03]} scale={[0.22, 0.23, 0.215]} />
        <Toon geom={G.capsule} color={c} position={[0, -0.18, -0.05]} scale={[0.2, 0.08, 0.17]} />
      </>
    );
  if (look.hairStyle === "bun")   // a high messy bun with two loose strands
    return (
      <>
        <Toon geom={G.sphere} color={c} position={[0, 0.04, -0.02]} scale={[0.205, 0.215, 0.2]} />
        <Toon geom={G.sphere} color={c} position={[0, 0.25, -0.07]} scale={[0.1, 0.09, 0.1]} />
        <Toon geom={G.sphere} color={c} position={[0.04, 0.15, 0.11]} rotation={[0.6, 0, -0.3]} scale={[0.12, 0.05, 0.09]} />
        {[-1, 1].map((s) => (
          <Toon key={s} geom={G.capsule} color={c} position={[s * 0.15, -0.08, 0.1]} rotation={[0, 0, s * 0.1]} scale={[0.018, 0.07, 0.018]} outline={0.01} />
        ))}
      </>
    );
  if (look.hairStyle === "ponytail")
    return (
      <>
        <Toon geom={G.sphere} color={c} position={[0, 0.04, -0.02]} scale={[0.205, 0.215, 0.2]} />
        <Toon geom={G.sphere} color={c} position={[0, 0.06, -0.24]} scale={[0.07, 0.07, 0.07]} />
        <Toon geom={G.capsule} color={c} position={[0, -0.12, -0.27]} rotation={[0.25, 0, 0]} scale={[0.055, 0.14, 0.055]} />
      </>
    );
  if (look.hairStyle === "short")   // short undercut with a swept, spiky fringe
    return (
      <>
        <Toon geom={G.sphere} color={c} position={[0, 0.05, -0.025]} scale={[0.2, 0.2, 0.2]} />
        <Toon geom={G.sphere} color={c} position={[0.03, 0.17, 0.06]} rotation={[0.5, 0, -0.5]} scale={[0.15, 0.07, 0.12]} />
        <Toon geom={G.sphere} color={c} position={[-0.09, 0.15, 0.1]} rotation={[0.9, 0, 0.6]} scale={[0.09, 0.05, 0.08]} />
        {[[-0.08, 0.2, -0.02, 0.4], [0.02, 0.23, -0.06, 0.1], [0.1, 0.19, -0.04, -0.4], [0.0, 0.18, -0.14, 0]].map(([x, y, z, r], i) => (
          <Toon key={i} geom={G.sphere} color={c} position={[x, y, z]} rotation={[0, 0, r]} scale={[0.05, 0.08, 0.05]} />
        ))}
      </>
    );
  // long open hair: a cap, side locks framing the face and a fall down the back
  return (
    <>
      <Toon geom={G.sphere} color={c} position={[0, 0.045, -0.02]} scale={[0.212, 0.22, 0.205]} />
      <Toon geom={G.sphere} color={c} position={[0.06, 0.15, 0.1]} rotation={[0.6, 0, -0.4]} scale={[0.13, 0.06, 0.1]} />
      {[-1, 1].map((s) => (
        <Toon key={s} geom={G.capsule} color={c} position={[s * 0.17, -0.12, 0.03]} rotation={[0.1, 0, s * 0.08]} scale={[0.045, 0.13, 0.05]} />
      ))}
      <Toon geom={G.capsule} color={c} position={[0, -0.2, -0.1]} rotation={[0.12, 0, 0]} scale={[0.18, 0.18, 0.07]} />
    </>
  );
};

const Face: React.FC<{ pose: Pose }> = ({ pose: p }) => {
  const eyeH = 0.045 * Math.max(0.08, p.eyes);
  const brow = p.brow;
  return (
    <group>
      {[-1, 1].map((s) => (
        <group key={s} position={[s * 0.07, 0.01, 0.168]}>
          {p.eyes > 0.15 ? (
            <>
              <mesh position={[p.lookX * 0.012, p.lookY * 0.01, 0]} scale={[0.034, eyeH, 0.02]}>
                <sphereGeometry args={[1, 16, 12]} />
                <meshBasicMaterial color="#1a1010" />
              </mesh>
              <mesh position={[p.lookX * 0.012 - 0.01, p.lookY * 0.01 + 0.015, 0.016]} scale={0.009}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#ffffff" />
              </mesh>
            </>
          ) : (
            <mesh rotation={[0, 0, p.happyEyes ? 0 : Math.PI]} scale={[0.03, 0.02, 0.02]}>
              <torusGeometry args={[1, 0.25, 6, 16, Math.PI]} />
              <meshBasicMaterial color="#1a1010" />
            </mesh>
          )}
          {/* brow: inner end rises when sad */}
          <mesh position={[0, 0.075 + brow * 0.01, 0.005]} rotation={[0, 0, -s * (0.1 + brow * 0.45)]} scale={[0.04, 0.008, 0.01]}>
            <boxGeometry args={[1, 1, 1]} />
            <meshBasicMaterial color="#20140f" />
          </mesh>
        </group>
      ))}
      {/* mouth: arc flips between smile and frown; an "o" when surprised */}
      {(p.mouthO ?? 0) > 0.3 ? (
        <mesh position={[0, -0.095, 0.17]} scale={[0.018, 0.026 * (p.mouthO ?? 0), 0.01]}>
          <sphereGeometry args={[1, 12, 10]} />
          <meshBasicMaterial color="#4a161c" />
        </mesh>
      ) : <mesh position={[0.012 * (p.smirk ?? 0), -0.09, 0.172]} rotation={[0, 0, (p.smile >= 0 ? Math.PI : 0) + 0.35 * (p.smirk ?? 0)]} scale={[0.04, 0.02 * Math.max(0.3, Math.abs(p.smile)), 0.02]}>
        <torusGeometry args={[1, 0.22, 6, 16, Math.PI]} />
        <meshBasicMaterial color="#5a1e24" />
      </mesh>}
      {/* blush */}
      {[-1, 1].map((s) => (
        <mesh key={s} position={[s * 0.1, -0.045, 0.155]} scale={[0.03, 0.014, 0.01]}>
          <sphereGeometry args={[1, 10, 8]} />
          <meshBasicMaterial color="#e87a80" transparent opacity={p.blush ?? 0.45} />
        </mesh>
      ))}
      {p.tear >= 0 ? (
        <mesh position={[-0.075, -0.02 - p.tear * 0.12, 0.17]} scale={0.013}>
          <sphereGeometry args={[1, 10, 8]} />
          <meshBasicMaterial color="#9fd0ff" transparent opacity={p.tearAlpha} />
        </mesh>
      ) : null}
    </group>
  );
};

// the "चेहरे पे चेहरा": a smiley mask on a stick, held over the face (k=1) or lowered (k=0)
let maskTex: THREE.Texture | null = null;
function getMaskTex(): THREE.Texture {
  if (maskTex) return maskTex;
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const x = c.getContext("2d")!;
  x.fillStyle = "#ffe9c8";
  x.beginPath(); x.arc(128, 128, 124, 0, Math.PI * 2); x.fill();
  x.fillStyle = "#1a1010";
  x.beginPath(); x.ellipse(84, 104, 16, 24, 0, 0, Math.PI * 2); x.fill();
  x.beginPath(); x.ellipse(172, 104, 16, 24, 0, 0, Math.PI * 2); x.fill();
  x.strokeStyle = "#c2263a"; x.lineWidth = 14; x.lineCap = "round";
  x.beginPath(); x.arc(128, 140, 62, 0.15 * Math.PI, 0.85 * Math.PI); x.stroke();
  x.fillStyle = "rgba(240,110,120,0.55)";
  x.beginPath(); x.ellipse(60, 160, 22, 12, 0, 0, Math.PI * 2); x.fill();
  x.beginPath(); x.ellipse(196, 160, 22, 12, 0, 0, Math.PI * 2); x.fill();
  maskTex = new THREE.CanvasTexture(c);
  maskTex.colorSpace = THREE.SRGBColorSpace;
  return maskTex;
}
const Mask: React.FC<{ k: number }> = ({ k }) => (
  <group position={[0.05, -0.32, 0.26]} rotation={[(1 - k) * 1.5, 0, 0]}>
    <mesh position={[0, 0.32, 0]}>
      <circleGeometry args={[0.2, 32]} />
      <meshBasicMaterial map={getMaskTex()} side={THREE.DoubleSide} />
    </mesh>
    <mesh position={[0, 0.32, -0.004]}>
      <circleGeometry args={[0.212, 32]} />
      <meshBasicMaterial color="#0e0e16" side={THREE.DoubleSide} />
    </mesh>
    <mesh position={[0, 0.06, -0.01]}>
      <cylinderGeometry args={[0.008, 0.008, 0.32, 6]} />
      <meshToonMaterial color="#8a6a3a" />
    </mesh>
  </group>
);

// short beard and moustache
const Beard: React.FC<{ color: string }> = ({ color }) => (
  <group>
    <Toon geom={G.sphere} color={color} position={[0, -0.13, 0.1]} scale={[0.13, 0.09, 0.1]} outline={0.01} />
    {[-1, 1].map((s) => <Toon key={s} geom={G.sphere} color={color} position={[s * 0.12, -0.06, 0.08]} scale={[0.05, 0.09, 0.07]} outline={0.01} />)}
    <Toon geom={G.capsule} color={color} position={[0, -0.065, 0.175]} rotation={[0, 0, Math.PI / 2]} scale={[0.016, 0.035, 0.016]} outline={0.006} />
  </group>
);
// black cloth over nose and mouth, eyes left free
const ClothMask: React.FC = () => (
  <group>
    <Toon geom={G.sphere} color="#121216" position={[0, -0.09, 0.03]} scale={[0.196, 0.13, 0.18]} outline={0.01} />
    <Toon geom={G.box} color="#121216" position={[0.1, -0.12, -0.18]} rotation={[0.3, 0, 0.4]} scale={[0.04, 0.12, 0.02]} outline={0.006} />
  </group>
);
