import { Composition } from "remotion";
import { Chor3D, DURATION } from "./Chor3D";

export const RemotionRoot: React.FC = () => (
  <Composition id="Chor3D" component={Chor3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
