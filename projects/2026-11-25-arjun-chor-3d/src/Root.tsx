import { Composition } from "remotion";
import { Arjun3D, DURATION } from "./Arjun3D";

export const RemotionRoot: React.FC = () => (
  <Composition id="Arjun3D" component={Arjun3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
