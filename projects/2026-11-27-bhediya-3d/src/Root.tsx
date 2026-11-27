import { Composition } from "remotion";
import { Bhediya3D, DURATION } from "./Bhediya3D";
export const RemotionRoot: React.FC = () => (
  <Composition id="Bhediya3D" component={Bhediya3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
