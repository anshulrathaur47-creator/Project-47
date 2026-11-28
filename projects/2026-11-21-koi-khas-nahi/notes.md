# "कोई खास नहीं": Peeli Chhatri (पीली छतरी)

**Input:** `assets/music/ReelAudio-84356.mp3` (20.1 s, ~136 bpm). Lyrics are in `references/ReelAudio-84356_hin.txt`.
The user asked for "ekdum professional", then for a **male version**. The male version is the deliverable.

**How it was made (ultracode):**
1. **Design workflow.** Three designers proposed a story and shot list from three angles: friendzone, memory,
   and minimal-cinematic. A judge scored them and merged the best into the final "Peeli Chhatri" design.
2. **Renderer.** `make_khas.py` builds 14 bespoke shots on the 19 Nov rig. Shared parts: the character head and
   body, faceless silhouettes, an umbrella prop, a night street, a rooftop, the bus shelter and a puddle reflection.
3. **Review round 1.** Story/acting, polish and continuity reviewers looked at 28 frames, and a lead merged a
   fix list. It covered:
   - gaze clipped inside the eye, visible sad brows, drooping lids
   - pinky-promise geometry, the high-five layout and the umbrella hand-off
   - the glass reflection, lyric outlines, night-time shelter light
   - the receding umbrella at the end, and screen direction on the reverse angle
4. **Male switch.** `make_khas_male.py` sets `STYLE="male"` and remaps the silhouettes.
5. **Review round 2** (on the male frames). Fixes included:
   - crossed fingers drawn as a clear X
   - a real silhouette taking the umbrella
   - the shot 2 canopy polygon, an upward point and a visible shrug
   - a readable long-haired girl silhouette
   - umbrella shafts behind the head
   - a feathered reflection smear and irregular rivulets
   - redrawn closed umbrella and puddle
   - the shot 8 coat and legs in proportion

**Male version.**
- **Aarav:** soft dark-brown hair with a side fringe, an olive bomber over a white tee, black jeans and a
  red-white friendship thread.
- **His best friend:** a girl, shown as a long-haired silhouette.
- **Her new boyfriend:** a silhouette in a cap with a coral rim. He asks who Aarav is, and she says "nobody special".

| Time | Lyric | Shot |
|---|---|---|
| 0 to 1.1 | कोई पूछे तुमसे… | Wide rainy street: Aarav at the bus shelter, the yellow umbrella snaps open; the couple under an awning across the road |
| 1.1 to 2.1 | …कौन हूँ मैं | Over his shoulder: the boyfriend points at him with a "?", she shrugs |
| 2.1 to 4.2 | तुम कह देना कोई ख़ास नहीं | Close-up under the umbrella: a polite smile, eyes drop, a tear; a gold heart on his chest cracks and drips |
| 4.2 to 5.3 | (music) | Feet at the curb: his tear falls into the puddle, ripples turn the frame golden |
| 5.3 to 6.2 | एक दोस्त था… | Golden flashback: walking under the umbrella he tilts over her, laughing, a high-five, shadows merging |
| 6.2 to 7.3 | …पक्का कच्चा सा | Macro: pinky promise; a strand of his thread frays |
| 7.3 to 9.1 | एक झूठ था आधा सच्चा सा | Rooftop at dusk: she shows a heart on her phone; "no one", he lies with a bright smile, fingers crossed; split warm/cool light |
| 9.1 to 10.6 | (music) | Feet walking together; hers veer away, his stop; drains to teal |
| 10.6 to 12.2 | जीवन का एक साथी था | Inside the shelter through rainy glass: a fond look; a golden memory on the glass washes away |
| 12.2 to 14.3 | जो पास होकर भी पास नहीं | Two-shot split by a steel bar: she is lost in her coral phone; his hand stops short; fog swallows her side; she leaves |
| 14.3 to 15.2 | कोई पूछे तुमसे… | Reverse angle from behind the couple: he is small across the road; the boyfriend points, he waves awkwardly |
| 15.2 to 16.1 | …कौन हूँ मैं | Close-up: rain smears his reflection's face; eyes close, a tear |
| 16.1 to 17.0 | (music) | He hands her the umbrella; she takes it; rain hits him; a brave closed-eye smile |
| 17.0 to end | तुम कह देना कोई ख़ास नहीं | Heavy rain: he walks alone towards us, crying-smiling, the friendship thread in his fist; far away the yellow umbrella over the couple fades; he walks into the lens; black |

**Look:**
- Cold, desaturated night for the present; warm golden memories that pale shot by shot; the coldest grade at the end.
- Mustard is his love (the umbrella), coral is the new partner, red is the thread.
- Static serif Devanagari lyrics with a dark outline and shadow, in the lower third; the last line sits at the top.

**Render:** `python3 make_khas_male.py --workers 4`. For the female version (Ira), run `python3 make_khas.py`.
