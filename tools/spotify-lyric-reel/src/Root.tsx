import { Composition } from "remotion";
import { Props, SpotifyLyric } from "./SpotifyLyric";
import sample from "../public/props.json";

export const RemotionRoot: React.FC = () => (
  <Composition id="SpotifyLyric" component={SpotifyLyric} fps={30} width={1080} height={1920} durationInFrames={300}
    defaultProps={sample as unknown as Props}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.ceil(props.durationSec * 30) })} />
);
