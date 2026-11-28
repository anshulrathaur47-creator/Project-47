import { Composition } from "remotion";
import { Kabootar3D, DURATION } from "./Kabootar3D";

export const RemotionRoot: React.FC = () => (
  <Composition id="Kabootar3D" component={Kabootar3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
