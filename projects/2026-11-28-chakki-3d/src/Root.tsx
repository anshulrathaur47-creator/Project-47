import { Composition } from "remotion";
import { Chakki3D, DURATION } from "./Chakki3D";
export const RemotionRoot: React.FC = () => (
  <Composition id="Chakki3D" component={Chakki3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
