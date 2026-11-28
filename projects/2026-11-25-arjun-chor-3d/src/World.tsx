import * as THREE from "three";
import { useMemo } from "react";
import { G, Toon } from "./Character";

export function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// ------------------------------------------------------------------------------------ the lane at night
export const skyMat = (top = "#060a1c", bottom = "#33365e", stars = 1) =>
  new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: { top: { value: new THREE.Color(top) }, bottom: { value: new THREE.Color(bottom) }, stars: { value: stars } },
    vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ",
    fragmentShader:
      "uniform vec3 top; uniform vec3 bottom; uniform float stars; varying vec3 vP; float h1(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,45.164)))*43758.5453);} " +
      "void main(){ float h = clamp(vP.y*1.5+0.1,0.0,1.0); vec3 c = mix(bottom, top, h); " +
      "vec3 q = floor(vP*260.0); float s = step(0.9965, h1(q)) * smoothstep(0.1,0.4,vP.y); c += vec3(s*0.8*stars); gl_FragColor = vec4(c,1.0);} ",
  });

export const Buildings: React.FC = () => {
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

export const Lamp: React.FC<{ base: [number, number, number]; dir: 1 | -1; target: [number, number, number]; intensity?: number; shadow?: boolean }> = ({
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

export const Tree: React.FC<{ pos: [number, number, number]; s?: number }> = ({ pos, s = 1 }) => (
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

export const Street: React.FC = () => (
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

