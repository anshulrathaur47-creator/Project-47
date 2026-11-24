import { Composition } from "remotion";
import { Chehre3D, DURATION } from "./Chehre3D";

export const RemotionRoot: React.FC = () => (
  <Composition id="Chehre3D" component={Chehre3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
