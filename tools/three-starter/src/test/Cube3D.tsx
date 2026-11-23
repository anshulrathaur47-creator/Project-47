import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// A quick 3D check: a lit, spinning cube and a torus in a vertical reel frame.
export const Cube3D: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const rot = interpolate(frame, [0, 90], [0, Math.PI * 2]);
  return (
    <AbsoluteFill style={{ backgroundColor: "#101828" }}>
      <ThreeCanvas width={width} height={height} camera={{ fov: 40, position: [0, 0, 7] }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[3, 4, 5]} intensity={2} />
        <mesh rotation={[rot * 0.6, rot, 0]} position={[0, 1, 0]}>
          <boxGeometry args={[1.6, 1.6, 1.6]} />
          <meshStandardMaterial color="#e8b020" />
        </mesh>
        <mesh rotation={[rot, 0, rot * 0.3]} position={[0, -1.6, 0]}>
          <torusGeometry args={[0.9, 0.3, 32, 64]} />
          <meshStandardMaterial color="#ff7a7a" metalness={0.3} roughness={0.4} />
        </mesh>
      </ThreeCanvas>
    </AbsoluteFill>
  );
};
