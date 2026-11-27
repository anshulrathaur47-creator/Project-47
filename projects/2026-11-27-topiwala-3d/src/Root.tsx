import { Composition } from "remotion";
import { Topiwala3D, DURATION } from "./Topiwala3D";
export const RemotionRoot: React.FC = () => (
  <Composition id="Topiwala3D" component={Topiwala3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
