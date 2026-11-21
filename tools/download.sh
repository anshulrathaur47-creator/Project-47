#!/usr/bin/env bash
# Download a video (YouTube, Shorts, Instagram Reels, TikTok, ...) with yt-dlp.
#   bash tools/download.sh <url> [folder]      # default folder: inspirations/
#
# YouTube and Instagram often refuse downloads from cloud servers ("Sign in to confirm
# you're not a bot", login required). The fix yt-dlp recommends is a cookies file from a
# browser where you're logged in. Save it (Netscape cookies.txt format) as:
#   tools/secrets/youtube-cookies.txt     (used for youtube.com / youtu.be links)
#   tools/secrets/instagram-cookies.txt   (used for instagram.com links)
# tools/secrets/ is git-ignored. Cookies give access to that account, so prefer a
# spare account and delete the file when you no longer need it.
set -euo pipefail
cd "$(dirname "$0")/.."
url=${1:?usage: bash tools/download.sh <url> [folder]}
out=${2:-inspirations}
mkdir -p "$out"

cookies=()
case "$url" in
  *youtube.com*|*youtu.be*) f=tools/secrets/youtube-cookies.txt ;;
  *instagram.com*)          f=tools/secrets/instagram-cookies.txt ;;
  *)                        f= ;;
esac
if [ -n "$f" ] && [ -f "$f" ]; then cookies=(--cookies "$f"); fi

yt-dlp "${cookies[@]}" \
  -f "bv*[height<=1920]+ba/b" --merge-output-format mp4 --no-playlist \
  -o "$out/%(extractor)s_%(id)s_%(title).60B.%(ext)s" "$url" && exit 0

status=$?
if [ -n "$f" ] && [ ! -f "$f" ]; then
  echo
  echo "Download failed. This site usually needs a logged-in cookies file from this server."
  echo "Export cookies.txt from your browser (e.g. the 'Get cookies.txt LOCALLY' extension)"
  echo "and upload it so it can be saved as $f, then run this again."
fi
exit $status
