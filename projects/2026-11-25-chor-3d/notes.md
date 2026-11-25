# "रात आया मेरे घर एक चोर": 3D emotional reel

**Inputs:** `assets/music/ReelAudio-33727.mp3` (48.1 s) and `references/ReelAudio-33727_hin.txt`.
- Timing is from chunked Whisper with a transcript prompt.
- Each "… भी ले जा" line is 2.0 s, exactly on the beat.

**Story:**
- A rainy night. Ramesh, a tired man of about 50 with a white beard, a cream kurta and a checked lungi, sits awake on his cot.
- A thief in a navy hood and a black cloth mask climbs in through the window: "दे दे मुझे जो भी तेरा है".
- Ramesh does not resist. With a tear and a small smile he puts everything into the thief's jute sack, one thing per line.
- Each thing is shown as a sign, flying into the sack:

  | Word | Sign |
  |---|---|
  | जीत | trophy |
  | हार | failed result paper |
  | डर | shivering dark smoke |
  | घर | house keys |
  | ख़्वाब | dream bubble with a heart |
  | राज़ | locked diary |
  | ग़म | his late wife's garlanded photo (he hugs it first) |
  | ज़ख़्म | cracked glowing heart |
  | जात | worn ID card |
  | औक़ात | empty wallet and two coins |
  | बात | unsent letter to his son |
  | हालात | a swirl of what is left; the camera cranes up over the leaking, cracked room |

- The thief's eyes soften from the photo onwards, and he cries.
- At the end he drops the sack (the things spill, glowing) and sits beside Ramesh with a hand on his shoulder.

**Build:** Remotion + three.js.
- `Character.tsx` adds a beard, a cloth mask, and "receding" and "hood" hair.
- `Chor3D.tsx` has the room, the props, the cameras, lightning and rain.
- Lyrics are static (Noto Serif Devanagari at top 1300).
