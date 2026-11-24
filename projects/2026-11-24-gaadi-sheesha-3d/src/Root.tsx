import { Composition } from "remotion";
import { Sheesha3D, DURATION } from "./Sheesha3D";

export const RemotionRoot: React.FC = () => (
  <Composition id="Sheesha3D" component={Sheesha3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
