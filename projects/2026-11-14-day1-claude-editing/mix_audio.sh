#!/usr/bin/env bash
# Mix the Day 1 reel: music bed (120bpm, ours/CC0) + library SFX on the 0.5s beat
# grid, loudness-normalized to -14 LUFS. Output: day1_final.mp4
set -euo pipefail
cd "$(dirname "$0")"
ROOT=../..
G=$ROOT/assets/sfx/generated
MUSIC=$ROOT/assets/music/generated/masti-upbeat-120bpm.mp3

# file  time(s)  volume
SFX=(
  "$G/boom-hit.wav        0.00 0.90"
  "$G/pop.wav             0.50 0.70"
  "$G/whoosh-soft.wav     1.25 0.45"
  "$G/whoosh-fast.wav     2.50 0.65"
  "$G/typing.wav          3.00 0.45"
  "$G/pop.wav             4.25 0.65"
  "$G/pop.wav             5.25 0.55"
  "$G/ding.wav            5.50 0.45"
  "$G/whip-pan.wav        7.00 0.65"
  "$G/click.wav           7.80 0.80"
  "$G/click.wav           8.55 0.80"
  "$G/punch-hit.wav       8.57 0.50"
  "$G/whoosh-soft.wav     9.00 0.45"
  "$G/pop.wav             9.55 0.55"
  "$G/pop.wav             9.80 0.55"
  "$G/pop.wav            10.05 0.60"
  "$G/whoosh-soft.wav    11.00 0.45"
  "$G/sparkle.wav        13.20 0.50"
  "$G/whip-pan.wav       13.00 0.65"
  "$G/pop.wav            13.50 0.55"
  "$G/pop.wav            14.00 0.55"
  "$G/pop.wav            14.50 0.55"
  "$G/pop.wav            15.00 0.55"
  "$G/ding.wav           15.50 0.50"
  "$G/boom-hit.wav       16.50 0.95"
  "$G/sparkle.wav        17.25 0.55"
)

inputs=(-i _day1_silent.mp4 -i "$MUSIC")
fc="[1:a]atrim=0:20,afade=t=in:d=0.2,afade=t=out:st=18.5:d=1.5,volume=0.9[m];"
labels="[m]"
n=2
for row in "${SFX[@]}"; do
  read -r f t v <<<"$row"
  inputs+=(-i "$f")
  ms=$(python3 -c "print(int(round($t*1000)))")
  fc+="[$n:a]adelay=${ms}:all=1,volume=$v[s$n];"
  labels+="[s$n]"
  n=$((n+1))
done
cnt=$((n-1))
fc+="${labels}amix=inputs=$cnt:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.70:level=disabled[out]"

ffmpeg -y -loglevel error "${inputs[@]}" -filter_complex "$fc" \
  -map 0:v -map "[out]" -c:v copy -c:a aac -b:a 192k -ar 44100 -shortest \
  -movflags +faststart day1_final.mp4
echo "wrote day1_final.mp4"
