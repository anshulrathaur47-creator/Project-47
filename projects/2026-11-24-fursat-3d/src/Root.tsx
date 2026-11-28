import { Composition } from "remotion";
import { Fursat3D, DURATION } from "./Fursat3D";

export const RemotionRoot: React.FC = () => (
  <Composition id="Fursat3D" component={Fursat3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
