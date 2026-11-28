import { Composition } from "remotion";
import { Kauwa3D, DURATION } from "./Kauwa3D";

export const RemotionRoot: React.FC = () => (
  <Composition id="Kauwa3D" component={Kauwa3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
