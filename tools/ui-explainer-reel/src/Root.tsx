import { Composition } from "remotion";
import { UIExplainer, Spec, DEMO } from "./UIExplainer";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="UIExplainer"
    component={UIExplainer}
    durationInFrames={300}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={DEMO}
    calculateMetadata={({ props }: { props: Spec }) => ({ durationInFrames: Math.ceil(props.duration * 30) })}
  />
);
