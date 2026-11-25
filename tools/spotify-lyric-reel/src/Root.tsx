import { Composition } from "remotion";
import { LyricCard } from "./LyricCard";
import { Tutorial, TUTORIAL_SEC } from "./Tutorial";
import { Props, SpotifyLyric } from "./SpotifyLyric";
import sample from "../public/props.json";

const meta = ({ props }: { props: Props }) => ({ durationInFrames: Math.ceil(props.durationSec * 30) });

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="SpotifyLyric" component={SpotifyLyric} fps={30} width={1080} height={1920} durationInFrames={300}
      defaultProps={sample as unknown as Props} calculateMetadata={meta} />
    <Composition id="LyricCard" component={LyricCard} fps={30} width={1080} height={1920} durationInFrames={300}
      defaultProps={sample as unknown as Props} calculateMetadata={meta} />
    <Composition id="Tutorial" component={Tutorial} fps={30} width={1080} height={1920} durationInFrames={Math.round(TUTORIAL_SEC * 30)} />
  </>
);
