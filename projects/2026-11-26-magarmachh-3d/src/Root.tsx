import { Composition } from "remotion";
import { Magarmachh3D, DURATION } from "./Magarmachh3D";

export const RemotionRoot: React.FC = () => (
  <Composition id="Magarmachh3D" component={Magarmachh3D} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
