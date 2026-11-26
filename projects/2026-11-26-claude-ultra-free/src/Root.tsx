import { Composition } from "remotion";
import { DURATION, UltraFree } from "./UltraFree";

export const RemotionRoot: React.FC = () => (
  <Composition id="UltraFree" component={UltraFree} durationInFrames={DURATION} fps={30} width={1080} height={1920} />
);
