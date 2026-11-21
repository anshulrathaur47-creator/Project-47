""""Peeli Chhatri", male version (user: "Male version m banana hai").

Same story and shots as make_khas.py with the roles swapped. The one who loves silently is Aarav, a boy with
soft dark-brown hair and a side-swept fringe, an olive bomber jacket over a white tee, black jeans and the
red-and-white friendship thread. His best friend is a girl (long-haired silhouette), and her new boyfriend
(silhouette in a cap, coral rim) is the one who asks "who is he?".

Usage: python3 make_khas_male.py [--frames 30,150,...] [--workers 4]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_khas as kh  # noqa: E402

kh.STYLE = "male"
kh.SKIN, kh.SKIN_SH = (214, 164, 124), (190, 140, 104)
kh.HAIR = (36, 27, 24)
kh.DENIM, kh.DENIM_SH, kh.DENIM_L = (86, 98, 62), (62, 72, 44), (120, 134, 90)   # olive bomber
kh.CUFF = (62, 72, 44)
kh.CREAM = (238, 238, 234)          # white tee
kh.JEANS = (34, 34, 40)
kh.KIND_MAP = {"kabir": "girl", "gf": "boy"}
kh.KIND_H = {"girl": 0.9, "boy": 1.06}
kh.ARM_W = (46, 40)
kh.OUT = os.path.join(HERE, "khas_male.mp4")
kh.SILENT = os.path.join(HERE, "_khas_male_silent.mp4")

if __name__ == "__main__":
    kh.main()
