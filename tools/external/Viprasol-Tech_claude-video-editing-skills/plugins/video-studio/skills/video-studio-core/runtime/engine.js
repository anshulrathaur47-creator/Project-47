/* Video Studio runtime — deterministic, seekable overlay engine.
 * window.__PLAN  : the plan object (see references/plan-schema.md and references/motion.md)
 * window.__render(t, layer) -> Promise<boolean>  (true if anything visible on that layer)
 * Every element is a pure function of time t: no CSS animations, no timers, no Math.random,
 * so any frame can be rendered in any order. All "randomness" comes from seeded hashes.
 *
 * Sections:
 *   1. math: easings, cubic-bezier, closed-form spring, seeded hash / value noise
 *   2. plan-level data: beats, face track, asset urls
 *   3. in/out animations, keyframes, idle motion (windowState)
 *   4. DOM helpers
 *   5. components: captions, text (+ fx), and the original set
 *   6. components added in the motion upgrade (timer ... transition)
 *   7. build + window.__render
 */
(function () {
  "use strict";
  const P = window.__PLAN;
  const W = P.output.width, H = P.output.height, FPS = P.output.fps || 30;
  const PORTRAIT = H > W;
  const warned = new Set();
  const warnOnce = m => { if (!warned.has(m)) { warned.add(m); console.warn(m); } };

  // =====================================================================
  // 1. math / easing / spring / noise
  // =====================================================================
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const lerp = (a, b, k) => a + (b - a) * k;
  const C1 = 1.70158, C2 = C1 * 1.525, C3 = C1 + 1;
  function bounceOut(k) {
    const n1 = 7.5625, d1 = 2.75;
    if (k < 1 / d1) return n1 * k * k;
    if (k < 2 / d1) return n1 * (k -= 1.5 / d1) * k + 0.75;
    if (k < 2.5 / d1) return n1 * (k -= 2.25 / d1) * k + 0.9375;
    return n1 * (k -= 2.625 / d1) * k + 0.984375;
  }
  // k in [0,1] -> eased value. Original names first (kept for old plans), then the full set.
  const E = {
    linear: k => k,
    out: k => 1 - Math.pow(1 - k, 3),
    in: k => k * k * k,
    inOut: k => (k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    back: k => 1 + C3 * Math.pow(k - 1, 3) + C1 * Math.pow(k - 1, 2),
    elastic: k => k === 0 || k === 1 ? k : Math.pow(2, -10 * k) * Math.sin((k * 10 - .75) * (2 * Math.PI / 3)) + 1,
    quadIn: k => k * k, quadOut: k => 1 - (1 - k) * (1 - k), quadInOut: k => k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2,
    cubicIn: k => k * k * k, cubicOut: k => 1 - Math.pow(1 - k, 3), cubicInOut: k => (k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    quintIn: k => Math.pow(k, 5), quintOut: k => 1 - Math.pow(1 - k, 5), quintInOut: k => k < .5 ? 16 * Math.pow(k, 5) : 1 - Math.pow(-2 * k + 2, 5) / 2,
    expoIn: k => k === 0 ? 0 : Math.pow(2, 10 * k - 10),
    expoOut: k => k === 1 ? 1 : 1 - Math.pow(2, -10 * k),
    expoInOut: k => k === 0 ? 0 : k === 1 ? 1 : k < .5 ? Math.pow(2, 20 * k - 10) / 2 : (2 - Math.pow(2, -20 * k + 10)) / 2,
    circIn: k => 1 - Math.sqrt(1 - k * k), circOut: k => Math.sqrt(1 - Math.pow(k - 1, 2)),
    circInOut: k => k < .5 ? (1 - Math.sqrt(1 - Math.pow(2 * k, 2))) / 2 : (Math.sqrt(1 - Math.pow(-2 * k + 2, 2)) + 1) / 2,
    sineIn: k => 1 - Math.cos(k * Math.PI / 2), sineOut: k => Math.sin(k * Math.PI / 2), sineInOut: k => -(Math.cos(Math.PI * k) - 1) / 2,
    backIn: k => C3 * k * k * k - C1 * k * k,
    backOut: k => 1 + C3 * Math.pow(k - 1, 3) + C1 * Math.pow(k - 1, 2),
    backInOut: k => k < .5 ? (Math.pow(2 * k, 2) * ((C2 + 1) * 2 * k - C2)) / 2 : (Math.pow(2 * k - 2, 2) * ((C2 + 1) * (k * 2 - 2) + C2) + 2) / 2,
    elasticOut: k => k === 0 || k === 1 ? k : Math.pow(2, -10 * k) * Math.sin((k * 10 - .75) * (2 * Math.PI / 3)) + 1,
    bounce: bounceOut, bounceOut, bounceIn: k => 1 - bounceOut(1 - k),
    bounceInOut: k => k < .5 ? (1 - bounceOut(1 - 2 * k)) / 2 : (1 + bounceOut(2 * k - 1)) / 2,
  };

  // CSS cubic-bezier(x1,y1,x2,y2): Newton iterations with a bisection fallback (deterministic).
  function cubicBezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = u => ((ax * u + bx) * u + cx) * u, sy = u => ((ay * u + by) * u + cy) * u, dx = u => (3 * ax * u + 2 * bx) * u + cx;
    return k => {
      if (k <= 0) return 0; if (k >= 1) return 1;
      let u = k;
      for (let i = 0; i < 8; i++) { const x = sx(u) - k, d = dx(u); if (Math.abs(x) < 1e-6 || Math.abs(d) < 1e-6) break; u -= x / d; }
      if (!(u >= 0 && u <= 1) || Math.abs(sx(u) - k) > 1e-4) {
        let lo = 0, hi = 1; u = k;
        for (let i = 0; i < 40; i++) { const x = sx(u); if (Math.abs(x - k) < 1e-6) break; if (x < k) lo = u; else hi = u; u = (lo + hi) / 2; }
      }
      return sy(u);
    };
  }

  // Closed-form damped spring (mass/stiffness/damping), evaluable at any local time lt (seconds).
  // Returns from -> to (default 0 -> 1); may overshoot when under-damped.
  function spring(lt, o) {
    o = o || {};
    const m = o.mass || 1, k = o.stiffness || 170, c = o.damping != null ? o.damping : 26;
    const from = o.from || 0, to = o.to != null ? o.to : 1;
    if (lt <= 0) return from;
    const w0 = Math.sqrt(k / m), z = c / (2 * Math.sqrt(k * m));
    let x;
    if (z < 1) {
      const wd = w0 * Math.sqrt(1 - z * z);
      x = 1 - Math.exp(-z * w0 * lt) * (Math.cos(wd * lt) + (z * w0 / wd) * Math.sin(wd * lt));
    } else if (z === 1) {
      x = 1 - Math.exp(-w0 * lt) * (1 + w0 * lt);
    } else {
      const s = Math.sqrt(z * z - 1), r1 = -w0 * (z - s), r2 = -w0 * (z + s);
      x = 1 - (r2 * Math.exp(r1 * lt) - r1 * Math.exp(r2 * lt)) / (r2 - r1);
    }
    return from + (to - from) * x;
  }
  const SPRING_EASE = { stiffness: 180, damping: 20 };

  // Resolve an ease spec into k->value. spec: name | "cubic-bezier(a,b,c,d)" | [a,b,c,d] | "spring" |
  // {spring:{stiffness,damping,mass}} | {stiffness,...}. dur (s) is used to map k onto spring time.
  function easeFn(spec, dur) {
    if (spec == null || spec === "") return null;
    if (typeof spec === "function") return spec;
    if (Array.isArray(spec) && spec.length === 4) return cubicBezier(spec[0], spec[1], spec[2], spec[3]);
    if (spec === "spring") { const d = dur || 0.6; return k => k >= 1 ? 1 : spring(k * d, SPRING_EASE); }
    if (typeof spec === "object") { const so = spec.spring || spec, d = spec.dur || dur || 0.6; return k => k >= 1 ? 1 : spring(k * d, so); }
    if (typeof spec === "string") {
      if (E[spec]) return E[spec];
      const m = spec.match(/^cubic-bezier\(([^)]+)\)$/);
      if (m) { const v = m[1].split(",").map(Number); if (v.length === 4 && v.every(isFinite)) return cubicBezier(v[0], v[1], v[2], v[3]); }
    }
    warnOnce("unknown ease " + JSON.stringify(spec));
    return null;
  }

  // Legacy seeded random (kept: old components use it) + integer hash, 2D value noise, PRNG.
  const rand = s => { const x = Math.sin(s * 9301.13 + 49297.7) * 233280; return x - Math.floor(x); };
  const hashInt = a => { a |= 0; a = Math.imul(a ^ (a >>> 16), 0x45d9f3b); a = Math.imul(a ^ (a >>> 16), 0x45d9f3b); return (a ^ (a >>> 16)) >>> 0; };
  const hash2 = (x, y, seed) => hashInt(x * 374761393 + y * 668265263 + seed * 1442695041) / 4294967295;
  // smooth value noise in [-1, 1]
  function noise2(x, y, seed = 0) {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    const a = hash2(xi, yi, seed), b = hash2(xi + 1, yi, seed), c = hash2(xi, yi + 1, seed), d = hash2(xi + 1, yi + 1, seed);
    return lerp(lerp(a, b, u), lerp(c, d, u), v) * 2 - 1;
  }
  // mulberry32: fast seeded PRNG for per-frame textures (grain)
  const prng = seed => () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  // largest index i with arr[i] <= t, or -1 (arr sorted ascending)
  function lastBefore(arr, t) { let lo = 0, hi = arr.length - 1, r = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m] <= t) { r = m; lo = m + 1; } else hi = m - 1; } return r; }
  const tri = p => 1 - Math.abs(2 * p - 1);

  // =====================================================================
  // 2. plan-level data: beats, face track, assets
  // =====================================================================
  // P.beats = {bpm, beats:[t...], downbeats:[t...], offset, beatsPerBar}. beats can be derived from bpm.
  const BEATS = (() => {
    const b = P.beats; if (!b) return null;
    let beats = Array.isArray(b.beats) ? b.beats.slice().sort((x, y) => x - y) : null;
    if (!beats && b.bpm) { beats = []; const step = 60 / b.bpm; for (let x = b.offset || 0; x < P.output.duration + step; x += step) beats.push(x); }
    let down = Array.isArray(b.downbeats) ? b.downbeats.slice().sort((x, y) => x - y) : null;
    if (!down && beats) down = beats.filter((_, i) => i % (b.beatsPerBar || 4) === 0);
    return { beats: beats || [], downbeats: down || [] };
  })();
  // times: an array of seconds, or "beats" / "downbeats"
  function timesOf(v) { if (Array.isArray(v)) return v; if (typeof v === "string") { if (BEATS) return BEATS[v] || []; warnOnce("'" + v + "' used but plan has no beats"); } return []; }
  function beatPulse(times, t, amp, decay) { const i = lastBefore(times, t); return i < 0 ? 0 : amp * Math.exp(-(t - times[i]) * decay); }

  // P.track = [{t, x, y, w, h}] normalized face boxes (x,y = top-left, 0..1). Linear interpolation.
  const TRACK = Array.isArray(P.track) && P.track.length ? P.track.slice().sort((a, b) => a.t - b.t) : null;
  const TRACK_T = TRACK ? TRACK.map(f => f.t) : null;
  function faceAt(t) {
    if (!TRACK) return null;
    const i = lastBefore(TRACK_T, t);
    if (i < 0) return TRACK[0];
    if (i >= TRACK.length - 1) return TRACK[TRACK.length - 1];
    const a = TRACK[i], b = TRACK[i + 1], k = clamp((t - a.t) / ((b.t - a.t) || 1));
    return { x: lerp(a.x, b.x, k), y: lerp(a.y, b.y, k), w: lerp(a.w, b.w, k), h: lerp(a.h, b.h, k) };
  }
  // offset [dx,dy]: |v| <= 3 means a fraction of the face size, otherwise pixels
  function faceCentre(t, off) {
    const f = faceAt(t); if (!f) return null;
    off = off || [0, 0];
    const dx = Math.abs(off[0]) <= 3 ? off[0] * f.w * W : off[0], dy = Math.abs(off[1]) <= 3 ? off[1] * f.h * H : off[1];
    return [(f.x + f.w / 2) * W + dx, (f.y + f.h / 2) * H + dy];
  }
  // nested asset paths (panes, avatars) are not resolved by render.py: resolve against workDir
  function assetUrl(p) {
    if (!p) return p;
    if (/^(https?:|data:|file:|blob:)/i.test(p)) return p;
    if (/^[A-Za-z]:[\\/]/.test(p) || p.startsWith("/")) return "file:///" + p.replace(/\\/g, "/").replace(/^\/+/, "");
    return new URL("../" + p.replace(/\\/g, "/"), location.href).href;
  }

  // =====================================================================
  // 3. in/out animations: return {tx,ty,s,sx,sy,r,o,blur,clip,txP,tyP,ry,flip,origin}
  // =====================================================================
  // default durations for the new named animations (old names keep the old 0.35/0.25 defaults)
  const NEW_ANIM_DUR = { maskUp: .5, maskDown: .5, maskLeft: .5, maskRight: .5, iris: .5, clockWipe: .6, slideUpFull: .5, push: .5, zoomOut: .45, whip: .3, elastic: .7, springPop: .6, rotateIn: .5, swing3d: .6, unfold: .45, blurIn: .45, typewriter: .6 };
  const IDLE = () => ({ tx: 0, ty: 0, s: 1, sx: 1, sy: 1, r: 0, o: 1, blur: 0, clip: null, txP: 0, tyP: 0, ry: 0, flip: 0, origin: null });

  // normalise "name" or {name, dur, ease, dir, dist, spring} into a spec with a resolved ease fn
  function animSpec(spec, durField, def, elEase) {
    const o = spec && typeof spec === "object" ? spec : { name: spec };
    const name = o.name || "fade";
    const dur = o.dur != null ? o.dur : durField != null ? durField : NEW_ANIM_DUR[name] != null ? NEW_ANIM_DUR[name] : def;
    return { name, dur, dir: o.dir, dist: o.dist, spring: o.spring, ease: easeFn(o.ease != null ? o.ease : elEase, dur) };
  }
  // direction helpers for push / whip: dir = direction of travel ("left" = enters from the right)
  function dirOffset(st, dir, v) { if (dir === "right") st.tx = -v; else if (dir === "up") st.ty = v; else if (dir === "down") st.ty = -v; else st.tx = v; }

  function animState(name, k, dir, o) {
    // k: 0 -> hidden, 1 -> fully shown. dir: "in" | "out" (out plays the in-animation backwards)
    o = o || {};
    const st = IDLE();
    if (!name || name === "none" || k >= 1) return st;
    const ez = o.ease;
    const e = ez ? ez(k) : E.out(k);           // default for the original names
    const eb = ez ? ez(k) : E.back(k);
    const ex = ez ? ez(k) : E.expoOut(k);      // default for masks / pushes
    switch (name) {
      // ----- original set (unchanged behaviour) -----
      case "fade": st.o = e; break;
      case "pop": st.s = lerp(0.4, 1, dir === "in" ? eb : e); st.o = clamp(k * 3); break;
      case "bounce": st.s = lerp(0.2, 1, ez ? ez(k) : E.elastic(k)); st.o = clamp(k * 4); break;
      case "rise": case "slideUp": st.ty = lerp(60, 0, e); st.o = e; break;
      case "drop": case "slideDown": st.ty = lerp(-60, 0, e); st.o = e; break;
      case "slideLeft": st.tx = lerp(120, 0, e); st.o = e; break;
      case "slideRight": st.tx = lerp(-120, 0, e); st.o = e; break;
      case "scale": st.s = lerp(1.25, 1, e); st.o = e; break;
      case "zoomIn": st.s = lerp(0.6, 1, e); st.o = e; break;
      case "blur": st.blur = lerp(24, 0, e); st.o = e; st.s = lerp(1.08, 1, e); break;
      case "spin": st.r = lerp(-25, 0, eb); st.s = lerp(.5, 1, eb); st.o = clamp(k * 3); break;
      case "wipe": st.clip = `inset(0 ${(1 - e) * 100}% 0 0)`; break;
      case "wipeUp": st.clip = `inset(${(1 - e) * 100}% 0 0 0)`; break;
      case "stamp": st.s = lerp(2.2, 1, ez ? ez(k) : E.out(k)); st.o = clamp(k * 2); st.r = lerp(-8, 0, e); break;
      case "flip": st.o = e; st.flip = lerp(90, 0, e); break;
      case "glitch": st.tx = (rand(Math.floor(k * 20)) - .5) * 40 * (1 - k); st.o = k > .15 ? 1 : 0; break;
      // ----- clip reveals: content slides inside a fixed mask (clip moves opposite to translate) -----
      case "maskUp": { const v = (1 - ex) * 100; st.tyP = v; st.clip = `inset(0 0 ${v}% 0)`; break; }
      case "maskDown": { const v = (1 - ex) * 100; st.tyP = -v; st.clip = `inset(${v}% 0 0 0)`; break; }
      case "maskLeft": { const v = (1 - ex) * 100; st.txP = v; st.clip = `inset(0 ${v}% 0 0)`; break; }
      case "maskRight": { const v = (1 - ex) * 100; st.txP = -v; st.clip = `inset(0 0 0 ${v}%)`; break; }
      case "iris": st.clip = `circle(${(ex * 75).toFixed(3)}% at 50% 50%)`; break;
      case "clockWipe": {
        const a = (ez ? ez(k) : E.sineInOut(k)) * 360, n = Math.max(2, Math.ceil(a / 8)), pts = ["50% 50%"];
        for (let i = 0; i <= n; i++) { const r = (-90 + a * i / n) * Math.PI / 180; pts.push(`${(50 + Math.cos(r) * 150).toFixed(2)}% ${(50 + Math.sin(r) * 150).toFixed(2)}%`); }
        st.clip = `polygon(${pts.join(",")})`; break;
      }
      // ----- moves -----
      case "slideUpFull": st.ty = (1 - ex) * H; break;
      case "push": dirOffset(st, o.dir, (1 - ex) * (o.dist || (o.dir === "up" || o.dir === "down" ? H * 0.6 : W))); break;
      case "zoomOut": st.s = lerp(1.6, 1, ex); st.o = clamp(k * 2.5); st.blur = (1 - ex) * 10; break;
      case "whip": {
        const d = o.dir || "left", v = (1 - ex) * (o.dist || W * 0.7);
        dirOffset(st, d, v); st.blur = (1 - k) * 26; st.o = clamp(k * 4);
        if (d === "up" || d === "down") st.sy = 1 + (1 - ex) * 0.8; else st.sx = 1 + (1 - ex) * 0.8;
        break;
      }
      case "elastic": st.s = ez ? ez(k) : E.elastic(k); st.o = clamp(k * 4); break;
      case "springPop": st.s = lerp(0.3, 1, spring(k * (o.dur || 0.6), o.spring || { stiffness: 240, damping: 14 })); st.o = clamp(k * 5); break;
      case "rotateIn": st.r = lerp(-90, 0, eb); st.s = lerp(0.6, 1, e); st.o = clamp(k * 3); break;
      case "swing3d": st.ry = lerp(-80, 0, eb); st.origin = "0% 50%"; st.o = clamp(k * 3); break;
      case "unfold": st.sy = Math.max(0.001, e); st.origin = "50% 0%"; st.o = clamp(k * 4); break;
      case "blurIn": st.blur = (1 - e) * 30; st.o = e; break;
      case "typewriter": { const q = Math.floor(k * 14) / 14; st.clip = `inset(0 ${(1 - q) * 100}% 0 0)`; break; } // non-text fallback
      default: st.o = e;
    }
    return st;
  }
  function combine(a, b) {
    return { tx: a.tx + b.tx, ty: a.ty + b.ty, s: a.s * b.s, sx: a.sx * b.sx, sy: a.sy * b.sy, r: a.r + b.r, o: a.o * b.o,
      blur: a.blur + b.blur, clip: a.clip || b.clip, txP: a.txP + b.txP, tyP: a.tyP + b.tyP, ry: a.ry + b.ry,
      flip: a.flip + b.flip, origin: a.origin || b.origin };
  }
  function applyAnim(node, st, extra) {
    const sx = (st.sx == null ? 1 : st.sx) * st.s, sy = (st.sy == null ? 1 : st.sy) * st.s;
    let tf = `translate(${st.tx}px,${st.ty}px)`;
    if (st.txP || st.tyP) tf += ` translate(${st.txP || 0}%,${st.tyP || 0}%)`;
    tf += ` scale(${sx === sy ? sx : sx + "," + sy}) rotate(${st.r}deg)`;
    if (st.flip) tf = `perspective(800px) rotateX(${st.flip}deg) ` + tf;
    if (st.ry) tf = `perspective(1200px) rotateY(${st.ry}deg) ` + tf;
    if (extra) tf += " " + extra;
    node.style.transform = tf;
    node.style.opacity = st.o;
    node.style.filter = st.blur > 0.05 ? `blur(${st.blur}px)` : "";
    node.style.clipPath = st.clip || "";
    node.style.transformOrigin = st.origin || "";
  }

  // keyframes: keys = {prop: [[t, value, ease?], ...]}, t relative to element start; the ease on
  // a key shapes the segment arriving at it (default inOut).
  function compileKeys(keys, elEase) {
    const out = {};
    for (const p in keys) {
      const arr = (keys[p] || []).slice().sort((a, b) => a[0] - b[0]);
      out[p] = arr.map((k, i) => ({ t: k[0], v: k[1], f: i ? (easeFn(k[2] != null ? k[2] : elEase || "inOut", k[0] - arr[i - 1][0]) || E.inOut) : null }));
    }
    return out;
  }
  function sampleKeys(arr, lt) {
    if (!arr.length) return null;
    if (lt <= arr[0].t) return arr[0].v;
    for (let i = 1; i < arr.length; i++) {
      const b = arr[i];
      if (lt < b.t) { const a = arr[i - 1]; return lerp(a.v, b.v, b.f(clamp((lt - a.t) / ((b.t - a.t) || 1)))); }
    }
    return arr[arr.length - 1].v;
  }

  // Visible window + combined motion for an element at time t (null when hidden).
  // Also moves el._outer when keys.x/y or anchorTo:"face" drive the position.
  function windowState(el, t) {
    const s = el.start != null ? el.start : 0, e = el.end != null ? el.end : P.output.duration + 1;
    if (t < s || t >= e) return null;
    const lt = t - s;
    const A = el._ws || (el._ws = {
      i: animSpec(el.in || "fade", el.inDur, 0.35, el.ease),
      o: animSpec(el.out || "fade", el.outDur, 0.25, el.outEase != null ? el.outEase : el.ease),
    });
    const kin = A.i.dur > 0 ? clamp(lt / A.i.dur) : 1;
    const kout = A.o.dur > 0 ? clamp((e - t) / A.o.dur) : 1;
    const st = combine(animState(A.i.name, kin, "in", A.i), animState(A.o.name, kout, "out", A.o));
    // idle motion
    if (el.float) { st.ty += Math.sin(lt * 2 * Math.PI * (el.floatSpeed || 0.35)) * el.float; }
    if (el.drift) { st.s *= 1 + el.drift * lt; }
    if (el.wobble) { st.r += Math.sin(lt * 6) * el.wobble; }
    if (el.shake) {
      const sh = el.shake, f = sh.freq || 8, amp = sh.amp != null ? sh.amp : 12, seed = (sh.seed || 0) + (el._i || 0) * 17;
      const env = sh.decay ? Math.exp(-lt * sh.decay) : 1;
      st.tx += noise2(lt * f, 0.5, seed) * amp * env; st.ty += noise2(lt * f, 9.5, seed) * amp * env;
      if (sh.rot) st.r += noise2(lt * f, 19.5, seed) * sh.rot * env;
    }
    let posX = null, posY = null;
    if (el.keys) {
      const kc = el._kc || (el._kc = compileKeys(el.keys, el.ease));
      for (const p in kc) {
        const v = sampleKeys(kc[p], lt); if (v == null) continue;
        if (p === "s") st.s *= v; else if (p === "o") st.o *= v; else if (p === "r") st.r += v; else if (p === "blur") st.blur += v;
        else if (p === "tx") st.tx += v; else if (p === "ty") st.ty += v; else if (p === "x") posX = v; else if (p === "y") posY = v;
      }
    }
    if (typeof el.pulseOn === "string") st.s *= 1 + beatPulse(timesOf(el.pulseOn), t, el.pulseAmp != null ? el.pulseAmp : 0.06, el.pulseDecay || 9);
    if (el.anchorTo === "face") { const c = faceCentre(t, el.offset); if (c) { posX = c[0]; posY = c[1]; } }
    if (el._outer) { if (posX != null) el._outer.style.left = posX + "px"; if (posY != null) el._outer.style.top = posY + "px"; }
    return { st, lt, kin, kout, dur: e - s };
  }

  // =====================================================================
  // 4. DOM helpers
  // =====================================================================
  const h = (tag, cls, parent, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    if (parent) parent.appendChild(n);
    return n;
  };
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const escBr = s => esc(s).replace(/\n/g, "<br>");
  // Grapheme clusters, not code points: a Devanagari matra / virama conjunct or an emoji sequence never splits.
  const GSEG = new Intl.Segmenter(undefined, { granularity: "grapheme" });
  const graphemes = s => Array.from(GSEG.segment(String(s)), g => g.segment);
  const glen = s => graphemes(s).length;
  const SENT_END = /[.!?।॥]$/, PHRASE_END = /[.!?,;:।॥]$/;   // incl. Devanagari danda / double danda (mirrors vs_common.SENT_END)
  const styleObj = (n, o) => { if (o) for (const k in o) n.style.setProperty(k.startsWith("--") ? k : k.replace(/[A-Z]/g, m => "-" + m.toLowerCase()), o[k]); };
  const px = v => (typeof v === "number" ? v + "px" : v);
  const anchorShift = a => { a = a || "center"; return [a.includes("left") ? 0 : a.includes("right") ? -100 : -50, a.includes("top") ? 0 : a.includes("bottom") ? -100 : -50]; };
  const fmtNum = (v, dec, compact) => compact && Math.abs(v) >= 10000
    ? new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)
    : Number(v).toLocaleString("en-US", { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  const PALETTE = ["var(--c-accent)", "var(--c-accent2)", "#7C8CFF", "#3EE08F", "#FF8A3D", "#C86BFF", "#4FC3F7", "#FF6B9A"];

  function position(node, el) {
    // x,y are the anchor point in output pixels (default centre of frame)
    const x = el.x != null ? el.x : W / 2, y = el.y != null ? el.y : H / 2;
    const [ax, ay] = anchorShift(el.anchor);
    node.style.left = px(x); node.style.top = px(y);
    node.style.transform = `translate(${ax}%,${ay}%) rotate(${el.rotate || 0}deg)`;
    if (el.w) node.style.width = px(el.w);
    if (el.h) node.style.height = px(el.h);
    if (el.z != null) node.style.zIndex = el.z;
  }

  // Base wrapper shared by all components
  function base(el, root) {
    const outer = h("div", "el el-" + el.type + (el.className ? " " + el.className : ""), root);
    position(outer, el);
    const inner = h("div", "anim", outer);
    styleObj(inner, el.style);
    el._outer = outer;
    return { outer, inner };
  }
  // Standard update loop: window -> show/hide -> in/out anim on inner -> optional per-frame tick
  function windowed(e2, outer, inner, tick) {
    return {
      layer: e2.layer || "front",
      async update(t) {
        const ws = windowState(e2, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        applyAnim(inner, ws.st);
        if (tick) await tick(t, ws);
        return true;
      }
    };
  }
  // full-frame element (overlays, callouts, pointers)
  const fullFrame = (el, extra) => Object.assign({}, el, { x: 0, y: 0, w: W, h: H, anchor: "top-left", anchorTo: null, keys: null }, extra || {});
  const POP = { name: "springPop", dur: 0.45, spring: { stiffness: 260, damping: 18 } };
  const SVGNS = "http://www.w3.org/2000/svg";

  // ---------- components ----------
  const C = {};

  // =====================================================================
  // 5a. captions (transcript words)
  // =====================================================================
  const CAP_PRESETS = {
    hormozi: { uppercase: true, maxWords: 3, maxChars: 18, mode: "karaoke", activeScale: 1.16, activePop: true, groupIn: "pop", groupInDur: 0.12, y: H * 0.66 },
    beast: { uppercase: true, maxWords: 2, maxChars: 14, mode: "reveal", wordIn: { name: "springPop", dur: 0.35 }, groupIn: "none", tilt: 3, y: H * 0.64 },
    clean: { maxWords: 16, maxChars: PORTRAIT ? 64 : 84, mode: "static", hold: 0.6, groupIn: "fade", groupInDur: 0.15, stripPunct: false, breakOnPunct: "sentence", breakGap: 0.7, y: H * 0.78 },
    karaoke: { maxWords: 6, maxChars: 30, mode: "fill", groupIn: "fade", groupInDur: 0.15, stripPunct: false, breakOnPunct: "sentence", y: H * 0.74 },
    boxed: { uppercase: true, maxWords: 3, maxChars: 18, mode: "karaoke", activeScale: 1.06, activePop: true, groupIn: "pop", groupInDur: 0.12, y: H * 0.68 },
    "minimal-lower": { maxWords: 5, maxChars: 30, mode: "reveal", wordIn: "fade", wordInDur: 0.2, groupIn: "none", y: H * 0.81 },
  };
  const EMOJI_IN = { name: "springPop", dur: 0.45, spring: { stiffness: 260, damping: 13 } };

  C.captions = function (elIn, root) {
    const pre = elIn.preset ? CAP_PRESETS[elIn.preset] : null;
    if (elIn.preset && !pre) warnOnce("unknown caption preset " + elIn.preset);
    const el = pre ? Object.assign({}, pre, elIn, { className: ["cap-preset-" + elIn.preset, elIn.className].filter(Boolean).join(" ") }) : elIn;
    const words = (el.words || P.words || []).filter(w => w.w && w.w.trim());
    const maxWords = el.maxWords || 3, maxChars = el.maxChars || 22, gap = el.breakGap || 0.45;
    const punctRe = el.breakOnPunct === "sentence" ? SENT_END : PHRASE_END;
    let groups = []; let cur = [];
    const flush = () => { if (cur.length) groups.push(cur); cur = []; };
    words.forEach((w, i) => {
      const prev = words[i - 1];
      const chars = cur.reduce((a, b) => a + glen(b.w) + 1, 0) + glen(w.w);
      if (cur.length && (cur.length >= maxWords || chars > maxChars || (prev && w.start - prev.end > gap))) flush();
      cur.push(w);
      if (punctRe.test(w.w.trim()) && el.breakOnPunct !== false) flush();
    });
    flush();
    const hold = el.hold != null ? el.hold : 0.5;
    const timeGroups = gs => gs.forEach((g, i) => {
      g.s = g[0].start; const next = gs[i + 1];
      g.e = Math.min(g[g.length - 1].end + hold, next ? next[0].start : 1e9);
    });
    timeGroups(groups);
    // reading speed: split groups above cpsMax chars/sec unless a half would be shorter than minDur
    const cpsMax = el.cpsMax != null ? el.cpsMax : 20, minDur = el.minDur != null ? el.minDur : 0.3;
    for (let pass = 0; cpsMax > 0 && pass < 4; pass++) {
      let changed = false; const out = [];
      groups.forEach(g => {
        const chars = g.reduce((a, w) => a + glen(w.w.trim()), 0) + g.length - 1;
        const d = Math.max(0.05, g.e - g.s), m = Math.ceil(g.length / 2);
        if (g.length > 1 && chars / d > cpsMax && g[m].start - g.s >= minDur && g.e - g[m].start >= minDur) { out.push(g.slice(0, m), g.slice(m)); changed = true; }
        else out.push(g);
      });
      groups = out; timeGroups(groups);
      if (!changed) break;
    }
    const clean = s => s.toLowerCase().replace(/[^\p{L}\p{M}\p{N}']/gu, "");
    const kw = new Set((el.keywords || []).map(clean));
    const emoji = {}; if (el.emoji) for (const k in el.emoji) emoji[clean(k)] = el.emoji[k];
    const outer = h("div", "el el-captions " + (el.className || ""), root);
    const baseX = el.x != null ? el.x : W / 2, baseY = el.y != null ? el.y : H * 0.68;
    outer.style.left = el.x != null ? px(el.x) : "50%"; outer.style.top = px(baseY);
    outer.style.transform = "translate(-50%,-50%)";
    outer.style.width = px(el.w || W * 0.86);
    const line = h("div", "cap-line", outer);
    styleObj(line, el.style);
    // An active word scaled up (activeScale) grows into its neighbours and the gap visually closes
    // ("MISTAKESTHAT"). Widen the word gap by the growth of a typical ~4-em word on each side.
    if (el.activeScale > 1 && !(el.style && (el.style.gap || el.style.columnGap))) {
      line.style.columnGap = `calc(${getComputedStyle(line).columnGap || "0.26em"} + ${((el.activeScale - 1) * 2.2).toFixed(3)}em)`;
    }
    let built = -1, spans = [], fills = [], emos = [];
    const fmt = s => {
      let x = s.trim();
      if (el.stripPunct !== false) x = x.replace(/[.,;:!?"।॥]+$/g, "").replace(/^["]+/, "");
      if (el.uppercase) x = x.toUpperCase();
      if (el.lowercase) x = x.toLowerCase();
      return x;
    };
    // ---- placement: safe area, right rail (9:16), dodge windows, face dodge ----
    let capX = baseX, capW = 0, capH = 0;
    function measure() {
      // one layout read per caption group (not per frame)
      capH = outer.offsetHeight;
      const ow = outer.offsetWidth;
      let minL = 1e9, maxR = -1e9;
      line.querySelectorAll(".cap-word").forEach(s => { minL = Math.min(minL, s.offsetLeft); maxR = Math.max(maxR, s.offsetLeft + s.offsetWidth); });
      if (maxR < minL) { minL = 0; maxR = ow; }
      capW = maxR - minL; capX = baseX;
      if (el.safe !== false && PORTRAIT) {
        const right = baseX - ow / 2 + maxR, left = baseX - ow / 2 + minL, limit = W * 0.88;
        if (right > limit) capX = baseX - Math.max(0, Math.min(right - limit, left - W * 0.04));
      }
    }
    function faceDodgeY(t, y) {
      const f = faceAt(t); if (!f) return y;
      const top = f.y * H, bot = (f.y + f.h) * H, m = el.dodgeMargin != null ? el.dodgeMargin : 30;
      if (f.x * W > capX + capW / 2 || (f.x + f.w) * W < capX - capW / 2) return y;
      if (y + capH / 2 + m < top || y - capH / 2 - m > bot) return y;
      const below = bot + m + capH / 2, above = top - m - capH / 2;
      const okB = below <= H * 0.85 - capH / 2, okA = above >= H * 0.10 + capH / 2;
      if (okB && (!okA || Math.abs(below - y) <= Math.abs(above - y))) return below;
      return okA ? above : y;
    }
    function place(t) {
      let y = baseY;
      if (el.dodge) for (const d of el.dodge) if (t >= d.start && t < d.end) { y = d.y <= 1 ? d.y * H : d.y; break; }
      if (el.dodgeFace && TRACK) { let acc = 0; for (let k = 0; k < 5; k++) acc += faceDodgeY(t - k * 0.04, y); y = acc / 5; }
      if (el.safe !== false) y = clamp(y, H * 0.10 + capH / 2, Math.max(H * 0.10 + capH / 2, H * 0.85 - capH / 2));
      outer.style.top = y + "px";
      if (capX !== baseX || el.x == null) outer.style.left = capX + "px";
    }
    if (el.lines) {
      // pre-written lines (e.g. translations): [{text, start, end}]
      let lastLi = -1;
      return {
        layer: el.layer || "front",
        update(t) {
          const li = el.lines.findIndex(l => t >= l.start && t < l.end);
          if (li < 0) { outer.style.display = "none"; return false; }
          outer.style.display = "";
          if (li !== lastLi) { line.innerHTML = ""; h("span", "cap-word is-line", line, esc(fmt(el.lines[li].text))); lastLi = li; measure(); }
          place(t);
          applyAnim(line, animState(el.groupIn || "fade", clamp((t - el.lines[li].start) / 0.15), "in"));
          return true;
        }
      };
    }
    const mode = el.mode || "karaoke";
    const wordSpec = animSpec(el.wordIn || "pop", el.wordInDur || null, 0.18, el.wordEase);
    const groupSpec = animSpec(el.groupIn || "fade", el.groupInDur || null, 0.12, null);
    return {
      layer: el.layer || "front",
      update(t) {
        const gi = groups.findIndex(g => t >= g.s && t < g.e);
        if (gi < 0) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        const g = groups[gi];
        if (built !== gi) {
          line.innerHTML = ""; fills = []; emos = [];
          spans = g.map((w, j) => {
            const c = clean(w.w);
            const sp = h("span", "cap-word" + (kw.has(c) ? " is-key" : ""), line, esc(fmt(w.w)));
            if (mode === "fill") fills[j] = h("span", "cap-fill", sp, esc(fmt(w.w)));
            if (emoji[c]) { const eo = h("span", "cap-emoji", sp); emos[j] = h("span", "cap-emoji-i", eo, esc(emoji[c])); }
            return sp;
          });
          built = gi;
          applyAnim(line, IDLE());
          measure();
        }
        place(t);
        g.forEach((w, j) => {
          const sp = spans[j];
          const spoken = t >= w.start, active = t >= w.start && (t < w.end + 0.05 || j === g.length - 1 && t < g.e) && !(g[j + 1] && t >= g[j + 1].start);
          let st = IDLE();
          if (mode === "reveal" || mode === "single") {
            if (!spoken) st.o = 0; else st = animState(wordSpec.name, clamp((t - w.start) / (wordSpec.dur || 0.18)), "in", wordSpec);
            if (mode === "single") sp.style.display = active ? "" : "none";
          }
          if (mode !== "static") { sp.classList.toggle("is-active", active); sp.classList.toggle("is-spoken", spoken); }
          if (active && el.activeScale && mode !== "static") st.s *= el.activePop ? 1 + (el.activeScale - 1) * spring(t - w.start, { stiffness: 320, damping: 16 }) : el.activeScale;
          applyAnim(sp, st);
          if (fills[j]) { const p = clamp((t - w.start) / Math.max(0.05, w.end - w.start)); fills[j].style.clipPath = `inset(-10% ${((1 - p) * 100).toFixed(2)}% -10% 0)`; }
          if (emos[j]) applyAnim(emos[j], animState("springPop", clamp((t - w.start + 0.05) / 0.45), "in", EMOJI_IN));
        });
        // group in/out
        const kin = clamp((t - g.s) / (groupSpec.dur || 0.12));
        applyAnim(line, animState(groupSpec.name, kin, "in", groupSpec), el.tilt ? `rotate(${(gi % 2 ? 1 : -1) * el.tilt}deg)` : "");
        return true;
      }
    };
  };

  // =====================================================================
  // 5b. text (+ fx effects)
  // =====================================================================
  const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+=<>/?";
  const FLAP = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  // split text into nowrap word groups of per-char cells; spaceCells: spaces become cells too
  function charCells(inner, txt, make, spaceCells) {
    inner.innerHTML = ""; const cells = [];
    txt.split(/(\s+)/).forEach(tok => {
      if (!tok) return;
      if (/^\s+$/.test(tok)) {
        if (/\n/.test(tok)) { inner.appendChild(document.createElement("br")); return; }
        if (spaceCells) cells.push(make(inner, " ", cells.length)); else inner.appendChild(document.createTextNode(" "));
        return;
      }
      const wg = h("span", "word-group", inner);
      graphemes(tok).forEach(ch => cells.push(make(wg, ch, cells.length)));
    });
    return cells;
  }
  // Each fx builder: (el, inner, txt, fx) -> {init?(), update(lt)}. init runs once after fit.
  const FX = {};
  FX.typewriter = (el, inner, txt, fx) => {
    inner.innerHTML = "";
    const on = h("span", "tw-on", inner), car = h("span", "tw-caret", inner, `<i>${esc(fx.caret || "|")}</i>`), off = h("span", "tw-off", inner);
    const chars = graphemes(txt), N = chars.length, cps = fx.cps || 18, delay = fx.delay || 0;
    if (fx.caret === false) car.style.display = "none";
    off.textContent = txt; let last = 0;
    return {
      update(lt) {
        const n = clamp(Math.floor((lt - delay) * cps), 0, N);
        if (n !== last) { on.textContent = chars.slice(0, n).join(""); off.textContent = chars.slice(n).join(""); last = n; }
        car.style.opacity = n < N && lt >= delay ? 1 : (Math.floor(lt / 0.53) % 2 ? 0 : 1);
      }
    };
  };
  FX.scramble = (el, inner, txt, fx) => {
    const cells = charCells(inner, txt, (p, ch) => { const s = h("span", "fx-ch", p); return { real: h("span", "fx-real", s, esc(ch)), ov: h("span", "fx-ov", s), st: -1 }; });
    const dur = fx.dur || 0.9, delay = fx.delay || 0, N = cells.length || 1, seed = fx.seed || 0;
    return {
      update(lt) {
        const frame = Math.floor(lt * FPS / (fx.every || 2));
        cells.forEach((c, j) => {
          if (lt >= delay + dur * ((j + 1) / N)) { if (c.st !== 1) { c.real.style.visibility = ""; c.ov.textContent = ""; c.st = 1; } }
          else { c.real.style.visibility = "hidden"; c.ov.textContent = GLYPHS[hashInt(j * 7919 + frame * 104729 + seed) % GLYPHS.length]; c.st = 0; }
        });
      }
    };
  };
  FX.splitflap = (el, inner, txt, fx) => {
    inner.classList.add("fx-flapboard");
    const cells = charCells(inner, txt.toUpperCase(), (p, ch) => { const s = h("span", "flap" + (ch === " " ? " is-space" : ""), p); return { b: h("b", "", s, "&nbsp;"), ch, g: null }; }, true);
    const stg = fx.stagger != null ? fx.stagger : 0.045, fd = fx.flipDur || 0.05, flips = fx.flips || 8, delay = fx.delay || 0, L = FLAP.length;
    return {
      update(lt) {
        cells.forEach((c, j) => {
          const step = (lt - delay - j * stg) / fd;
          let g, tf = "";
          if (step < 0) g = " ";
          else if (step >= flips) g = c.ch;
          else {
            const idx = FLAP.indexOf(c.ch) < 0 ? hashInt(j) % L : FLAP.indexOf(c.ch);
            g = FLAP[(idx - (flips - Math.floor(step)) + L * 8) % L];
            tf = `scaleY(${(0.35 + 0.65 * Math.abs(Math.cos((step % 1) * Math.PI))).toFixed(3)})`;
          }
          if (g !== c.g) { c.b.textContent = g === " " ? " " : g; c.g = g; }
          c.b.style.transform = tf;
        });
      }
    };
  };
  // marker-style effects: highlight / underline / strike sweep left->right (CSS var --k drives size)
  const markFx = (cls, defDelay, defDur) => (el, inner, txt, fx) => {
    const tgt = fx.target || fx.word ? String(fx.target || fx.word) : null;
    const i = tgt ? txt.toLowerCase().indexOf(tgt.toLowerCase()) : -1;
    const open = `<span class="fx-mark ${cls}">`;
    inner.innerHTML = i >= 0 ? escBr(txt.slice(0, i)) + open + escBr(txt.slice(i, i + tgt.length)) + "</span>" + escBr(txt.slice(i + tgt.length)) : open + escBr(txt) + "</span>";
    const m = inner.querySelector(".fx-mark");
    if (fx.color) m.style.setProperty("--mk", fx.color);
    if (fx.textColor) m.style.color = fx.textColor;
    const delay = fx.delay != null ? fx.delay : defDelay, dur = fx.dur || defDur, ez = easeFn(fx.ease || "cubicOut", dur) || E.out;
    if (cls === "fx-st") {
      // strike must sit over the glyphs: one ::after per word, swept in sequence by character share
      const ws = m.textContent.split(/\s+/).filter(Boolean), total = ws.reduce((a, w) => a + glen(w), 0) || 1;
      m.innerHTML = ws.map(w => `<span class="fx-st-w">${esc(w)}</span>`).join(" ");
      let off = 0; const parts = Array.from(m.children).map((n, i) => { const o = { n, a: off / total, b: (off + glen(ws[i])) / total }; off += glen(ws[i]); return o; });
      return { update(lt) { const K = ez(clamp((lt - delay) / dur)); parts.forEach(q => q.n.style.setProperty("--k", clamp((K - q.a) / ((q.b - q.a) || 1)).toFixed(4))); } };
    }
    return { update(lt) { m.style.setProperty("--k", ez(clamp((lt - delay) / dur)).toFixed(4)); } };
  };
  FX.highlight = markFx("fx-hl", 0.25, 0.4);
  FX.underline = markFx("fx-ul", 0.3, 0.35);
  FX.strike = markFx("fx-st", 0.35, 0.3);
  FX.gradientSweep = (el, inner, txt, fx) => {
    inner.innerHTML = `<span class="fx-grad">${escBr(txt)}</span>`;
    const g = inner.firstChild; if (fx.color) g.style.setProperty("--gs", fx.color);
    const per = fx.period || 2.2, delay = fx.delay || 0;
    return { update(lt) { const p = (Math.max(0, lt - delay) / per) % 1; g.style.backgroundPosition = `${(100 - p * 100).toFixed(2)}% 50%`; } };
  };
  // countWords: every number inside the text counts up from 0 (final width reserved, no reflow)
  FX.countWords = (el, inner, txt, fx) => {
    const re = /\d[\d,]*(?:\.\d+)?/g; let html = "", last = 0, m; const nums = [];
    while ((m = re.exec(txt))) {
      html += escBr(txt.slice(last, m.index));
      const raw = m[0];
      html += `<span class="fx-num"><span class="fx-num-final">${esc(raw)}</span><span class="fx-num-cur"></span></span>`;
      nums.push({ v: parseFloat(raw.replace(/,/g, "")), dec: (raw.split(".")[1] || "").length, comma: raw.includes(",") });
      last = re.lastIndex;
    }
    inner.innerHTML = html + escBr(txt.slice(last));
    const curs = inner.querySelectorAll(".fx-num-cur"), delay = fx.delay != null ? fx.delay : 0.1, dur = fx.dur || 1.2;
    return {
      update(lt) {
        const k = E.expoOut(clamp((lt - delay) / dur));
        nums.forEach((n, i) => { const v = n.v * k; curs[i].textContent = n.comma ? fmtNum(v, n.dec) : v.toFixed(n.dec); });
      }
    };
  };
  // stroke-draw: SVG text outline drawn with stroke-dashoffset, fill fades in at the end (one line)
  FX["stroke-draw"] = (el, inner, txt, fx) => {
    inner.innerHTML = esc(txt);   // plain text first so fit can measure it
    let tx = null, D = 0;
    const delay = fx.delay || 0, dur = fx.dur || 1.4;
    return {
      init() {
        const fs = parseFloat(getComputedStyle(inner).fontSize);
        inner.innerHTML = "";
        const svg = document.createElementNS(SVGNS, "svg"); svg.setAttribute("class", "fx-stroke"); inner.appendChild(svg);
        tx = document.createElementNS(SVGNS, "text"); tx.textContent = txt.replace(/\n/g, " "); tx.setAttribute("x", 0); tx.setAttribute("y", 0); svg.appendChild(tx);
        const bb = tx.getBBox(), pad = fs * 0.08;
        svg.setAttribute("viewBox", `${bb.x - pad} ${bb.y - pad} ${bb.width + 2 * pad} ${bb.height + 2 * pad}`);
        svg.style.width = (bb.width + 2 * pad) + "px"; svg.style.height = (bb.height + 2 * pad) + "px";
        D = fx.dash || fs * 6;
        tx.style.strokeDasharray = `${D} ${D}`; tx.style.stroke = fx.color || "var(--c-accent)"; tx.style.strokeWidth = fx.width || Math.max(2, fs * 0.022);
      },
      update(lt) {
        const k = clamp((lt - delay) / dur);
        tx.style.strokeDashoffset = D * (1 - E.inOut(k));
        tx.style.fillOpacity = fx.fill === false ? 0 : E.out(clamp((k - 0.6) / 0.4));
      }
    };
  };
  // karaoke-fill: accent copy clipped left->right over [from, to] (absolute) or [delay, delay+dur]
  FX["karaoke-fill"] = (el, inner, txt, fx) => {
    const t = escBr(txt);
    inner.innerHTML = `<span class="kf"><span class="kf-base">${t}</span><span class="kf-top" aria-hidden="true">${t}</span></span>`;
    const top = inner.querySelector(".kf-top"); if (fx.color) top.style.color = fx.color;
    const s0 = el.start || 0, from = fx.from != null ? fx.from - s0 : (fx.delay || 0), to = fx.to != null ? fx.to - s0 : from + (fx.dur || 1.6);
    return { update(lt) { const k = clamp((lt - from) / ((to - from) || 1)); top.style.clipPath = `inset(-10% ${((1 - k) * 100).toFixed(2)}% -10% 0)`; } };
  };

  // Generic text: headline, chip, tile, sticker, poster word ...
  C.text = function (el, root) {
    const { outer, inner } = base(el, root);
    const txt = el.uppercase ? String(el.text).toUpperCase() : String(el.text == null ? "" : el.text);
    let fx = el.fx ? (typeof el.fx === "string" ? { name: el.fx } : el.fx) : null;
    let wsEl = el;
    const inName = el.in && typeof el.in === "object" ? el.in.name : el.in;
    if (!fx && inName === "typewriter") { fx = Object.assign({}, typeof el.in === "object" ? el.in : {}, { name: "typewriter" }); wsEl = Object.assign({}, el, { in: "none" }); }
    if (fx && !FX[fx.name]) { warnOnce("unknown text fx " + fx.name); fx = null; }
    const lineMode = !fx && el.split === "lines";
    let parts = [], fxu = null, linesBuilt = false;
    const buildLines = rows => { inner.innerHTML = ""; parts = rows.map(r => h("span", "unit unit-line", h("span", "line-row", inner), esc(r) || "&nbsp;")); };
    if (fx) fxu = FX[fx.name](el, inner, txt, fx);
    else if (el.split === "words" || el.split === "chars") {
      // words stay unbroken: each word is a nowrap group; chars animate inside it
      txt.split(/(\s+)/).forEach(tok => {
        if (!tok) return;
        if (/^\s+$/.test(tok)) { inner.appendChild(document.createTextNode(" ")); return; }
        if (el.split === "words") { parts.push(h("span", "unit", inner, esc(tok))); return; }
        const wg = h("span", "word-group", inner);
        wg.style.whiteSpace = "nowrap"; wg.style.display = "inline-block";
        graphemes(tok).forEach(ch => parts.push(h("span", "unit", wg, esc(ch))));
      });
    } else if (lineMode) {
      if (txt.includes("\n")) { buildLines(txt.split("\n")); linesBuilt = true; } else inner.innerHTML = esc(txt);
    } else inner.innerHTML = el.html ? el.text : escBr(txt);
    // split:"lines" without \n: measure where the browser wraps (once, after fit)
    const measureLines = () => {
      const ws = txt.split(/\s+/).filter(Boolean);
      inner.innerHTML = ws.map(w => `<span class="lw">${esc(w)}</span>`).join(" ");
      const rows = []; let lastTop = null;
      inner.querySelectorAll(".lw").forEach(s => { const tp = s.offsetTop; if (lastTop === null || Math.abs(tp - lastTop) > 4) { rows.push([]); lastTop = tp; } rows[rows.length - 1].push(s.textContent); });
      buildLines(rows.map(r => r.join(" ")));
    };
    let fitted = !(el.fit || (el.type === "headline" && el.fit !== false));
    const doFit = () => {
      // shrink font until the text fits its box width (and height if h given)
      const maxW = el.w || W * 0.92, maxH = el.h || 1e9;
      inner.style.whiteSpace = el.wrap ? "pre-line" : "nowrap";
      inner.style.width = "auto"; inner.style.display = "inline-block";
      let fs = parseFloat(getComputedStyle(inner).fontSize), guard = 0;
      while ((inner.scrollWidth > maxW || inner.scrollHeight > maxH) && fs > 12 && guard++ < 60) {
        fs *= 0.92; inner.style.fontSize = fs + "px";
      }
      inner.style.width = ""; inner.style.display = "";
      fitted = true;
    };
    let U = null;
    return {
      layer: el.layer || "front",
      update(t) {
        const ws = windowState(wsEl, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        if (!fitted) doFit();
        if (lineMode && !linesBuilt) { measureLines(); linesBuilt = true; }
        if (fxu && !fxu.ready) { if (fxu.init) fxu.init(); fxu.ready = true; }
        applyAnim(inner, ws.st);
        if (parts.length) {
          U = U || animSpec(el.unitIn || (lineMode ? "maskUp" : "rise"), el.unitDur || null, lineMode ? 0.55 : 0.3, el.unitEase);
          const stg = el.stagger != null ? el.stagger : lineMode ? 0.12 : 0.06;
          parts.forEach((p, i) => applyAnim(p, animState(U.name, U.dur > 0 ? clamp((ws.lt - i * stg) / U.dur) : 1, "in", U)));
        }
        if (fxu) fxu.update(ws.lt, ws);
        return true;
      }
    };
  };
  C.headline = C.text; C.chip = C.text; C.sticker = C.text; C.tile = C.text;

  // =====================================================================
  // 5c. original components (unchanged apart from small fixes noted inline)
  // =====================================================================
  // Card: title/body/list/image/clip
  C.card = function (el, root) {
    const { outer, inner } = base(el, root);
    let media = null, clipC = null;
    if (el.image) { media = h("img", "card-media", inner); media.src = el.image; }
    if (el.clip) { clipC = clipPlayer(el.clip, el.clipOffset || 0, inner, "card-media"); }
    if (el.kicker) h("div", "card-kicker", inner, esc(el.kicker));
    if (el.title) h("div", "card-title", inner, esc(el.title));
    if (el.body) h("div", "card-body", inner, esc(el.body));
    const items = (el.items || []).map((it, i) => {
      const li = h("div", "card-item", inner);
      h("span", "card-mark", li, el.marker || (el.numbered ? String(i + 1) : "✓"));
      h("span", "card-item-text", li, esc(typeof it === "string" ? it : it.text));
      return { li, at: typeof it === "object" && it.at != null ? it.at : null, i };
    });
    return {
      layer: el.layer || "front",
      async update(t) {
        const ws = windowState(el, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        applyAnim(inner, ws.st);
        items.forEach(o => {
          const at = o.at != null ? o.at : (el.start || 0) + 0.4 + o.i * (el.itemStagger || 0.5);
          const k = clamp((t - at) / 0.3);
          applyAnim(o.li, animState(el.itemIn || "slideLeft", k, "in"));
          o.li.classList.toggle("is-done", t >= at);
        });
        if (clipC) await clipC.seek(t - (el.start || 0));
        return true;
      }
    };
  };

  // Image sequence player for clips declared in plan.clips (extracted by render.py)
  const CLIPS = {};
  (P.clips || []).forEach(c => { CLIPS[c.id] = c; });
  function clipPlayer(id, offset, parent, cls) {
    const c = CLIPS[id];
    const img = h("img", cls || "clip", parent);
    let lastIdx = -1;
    return {
      img,
      async seek(lt) {
        if (!c) return;
        const n = c.frames || 1;
        let idx = Math.floor((lt + offset) * FPS);
        idx = c.loop ? ((idx % n) + n) % n : clamp(idx, 0, n - 1);
        if (idx !== lastIdx) {
          img.src = `${c.dir}/${String(idx + 1).padStart(5, "0")}.jpg`;
          lastIdx = idx;
          try { await img.decode(); } catch (e) { /* missing frame: keep last image */ }
        }
      }
    };
  }

  // Clip on screen with optional device frame and 3D motion
  C.clip = function (el, root) {
    const { outer, inner } = base(el, root);
    let host = inner;
    if (el.device) {
      host = h("div", "device device-" + el.device, inner);
      if (el.device === "browser") { const bar = h("div", "device-bar", host); h("i", "", bar); h("i", "", bar); h("i", "", bar); }
      host = h("div", "device-screen", host);
    }
    const player = clipPlayer(el.clip, el.clipOffset || 0, host, "clip-media");
    if (el.image) player.img.src = el.image;
    return {
      layer: el.layer || "front",
      async update(t) {
        const ws = windowState(el, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        let extra = "";
        const m = el.motion || "none", lt = ws.lt;
        if (m === "flyIn") {
          const k = E.out(clamp(lt / (el.flyDur || 1.2)));
          extra = `perspective(1600px) translateZ(${lerp(-900, 0, k)}px) rotateY(${lerp(-38, el.tiltY || -12, k)}deg) rotateX(${lerp(22, el.tiltX || 6, k)}deg)`;
        } else if (m === "tilt") {
          extra = `perspective(1600px) rotateY(${Math.sin(lt * .6) * 10 + (el.tiltY || -10)}deg) rotateX(${Math.cos(lt * .5) * 4 + (el.tiltX || 5)}deg)`;
        } else if (m === "float") {
          extra = `translateY(${Math.sin(lt * 1.2) * 14}px) rotate(${Math.sin(lt * .8) * 1.5}deg)`;
        } else if (m === "kenburns") {
          extra = `scale(${1 + lt * 0.02})`;
        } else if (m === "orbit") {
          extra = `perspective(1600px) rotateY(${Math.sin(lt * .4) * 25}deg)`;
        }
        applyAnim(inner, ws.st, extra);
        if (!el.image) await player.seek(lt);
        return true;
      }
    };
  };
  C.image = function (el, root) { return C.clip(Object.assign({}, el, { clip: null }), root); };

  // Animated counter
  C.counter = function (el, root) {
    const { outer, inner } = base(el, root);
    const num = h("div", "counter-num", inner);
    if (el.label) h("div", "counter-label", inner, esc(el.label));
    const dec = el.decimals || 0;
    const fmtN = v => (el.prefix || "") + Number(v).toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + (el.suffix || "");
    const cE = easeFn(el.countEase, el.countDur || 1.2) || E.out;
    return {
      layer: el.layer || "front",
      update(t) {
        const ws = windowState(el, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        applyAnim(inner, ws.st);
        const k = cE(clamp(ws.lt / (el.countDur || 1.2)));
        num.textContent = fmtN(lerp(el.from || 0, el.to, k));
        return true;
      }
    };
  };

  // Bar chart
  C.bars = function (el, root) {
    const { outer, inner } = base(el, root);
    if (el.title) h("div", "bars-title", inner, esc(el.title));
    const max = el.max || Math.max(...el.items.map(i => i.value));
    const rows = el.items.map(it => {
      const r = h("div", "bar-row", inner);
      h("div", "bar-label", r, esc(it.label));
      const track = h("div", "bar-track", r);
      const fill = h("div", "bar-fill" + (it.highlight ? " is-hi" : ""), track);
      const val = h("div", "bar-value", r);
      return { fill, val, it };
    });
    return {
      layer: el.layer || "front",
      update(t) {
        const ws = windowState(el, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        applyAnim(inner, ws.st);
        rows.forEach((o, i) => {
          const k = E.out(clamp((ws.lt - 0.2 - i * 0.15) / 0.9));
          o.fill.style.width = (o.it.value / max * 100 * k) + "%";
          o.val.textContent = (el.prefix || "") + Math.round(o.it.value * k).toLocaleString("en-US") + (el.suffix || "");
        });
        return true;
      }
    };
  };

  // Lower third
  C.lowerthird = function (el, root) {
    const e2 = Object.assign({ x: 70, y: H - 360, anchor: "left", in: "slideRight" }, el);
    const { outer, inner } = base(e2, root);
    h("div", "lt-name", inner, esc(el.name));
    if (el.role) h("div", "lt-role", inner, esc(el.role));
    return { layer: el.layer || "front", update(t) { const ws = windowState(e2, t); if (!ws) { outer.style.display = "none"; return false; } outer.style.display = ""; applyAnim(inner, ws.st); return true; } };
  };

  // Full-frame title card
  C.titlecard = function (el, root) {
    const e2 = Object.assign({ x: W / 2, y: H / 2, w: W, h: H }, el);
    const { outer, inner } = base(e2, root);
    if (el.kicker) h("div", "tc-kicker", inner, esc(el.kicker));
    h("div", "tc-title", inner, esc(el.title));
    if (el.subtitle) h("div", "tc-sub", inner, esc(el.subtitle));
    return { layer: el.layer || "front", update(t) { const ws = windowState(e2, t); if (!ws) { outer.style.display = "none"; return false; } outer.style.display = ""; applyAnim(inner, ws.st); return true; } };
  };

  // Decorative shapes (rings, glows, orbits, ribbons, rays, grids, blobs, sparkles...)
  C.shape = function (el, root) {
    const e2 = Object.assign({ x: W / 2, y: H * 0.4, w: W * 0.8, h: W * 0.8, in: "fade", inDur: 0.6 }, el);
    const { outer, inner } = base(e2, root);
    const kind = el.kind || "ring";
    inner.classList.add("shape", "shape-" + kind);
    const c1 = el.color || "var(--c-accent)", c2 = el.color2 || "var(--c-accent2)";
    inner.style.setProperty("--s1", c1); inner.style.setProperty("--s2", c2);
    let svg = null, parts = [];
    if (kind === "orbit" || kind === "sparkles" || kind === "bubbles" || kind === "confetti") {
      const n = el.count || (kind === "orbit" ? 3 : 18);
      for (let i = 0; i < n; i++) parts.push(h("i", "p", inner));
    }
    if (kind === "ribbon") {
      inner.innerHTML = `<svg viewBox="0 0 1000 1000" preserveAspectRatio="none"><defs><linearGradient id="rg${el._i}" x1="0" x2="1"><stop offset="0" stop-color="${c1}"/><stop offset="1" stop-color="${c2}"/></linearGradient></defs><path class="rib" fill="none" stroke="url(#rg${el._i})" stroke-linecap="round"/></svg>`;
      svg = inner.querySelector("path");
    }
    const pulseTimes = Array.isArray(el.pulseOn) ? el.pulseOn : [];   // string "beats" handled by windowState
    return {
      layer: el.layer || "behind",
      update(t) {
        const ws = windowState(e2, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        const lt = ws.lt, sp = el.speed || 1;
        let extra = "";
        if (kind === "ring" || kind === "glow") extra = `scale(${1 + Math.sin(lt * 2.2 * sp) * 0.03 + pulseTimes.reduce((a, p) => a + Math.max(0, 0.12 - Math.abs(t - p) * 0.4), 0)})`;
        if (kind === "rays" || kind === "burst") extra = `rotate(${lt * 12 * sp}deg)`;
        if (kind === "blob") inner.style.borderRadius = `${50 + Math.sin(lt * sp) * 12}% ${50 + Math.cos(lt * 1.3 * sp) * 12}% ${50 + Math.sin(lt * .7 * sp) * 12}% ${50 + Math.cos(lt * .9 * sp) * 12}%`;
        if (kind === "orbit") parts.forEach((p, i) => {
          const a = lt * 1.4 * sp + i * (Math.PI * 2 / parts.length);
          const rx = (e2.w / 2) * 0.92, ry = (e2.h / 2) * 0.32;
          const x = Math.cos(a) * rx, y = Math.sin(a) * ry;
          p.style.transform = `translate(${x}px,${y}px) scale(${0.7 + 0.5 * (Math.sin(a) + 1) / 2})`;
          p.style.opacity = 0.35 + 0.65 * (Math.sin(a) + 1) / 2;
          p.style.zIndex = Math.sin(a) > 0 ? 2 : 0;
        });
        if (kind === "sparkles" || kind === "bubbles" || kind === "confetti") parts.forEach((p, i) => {
          const r1 = rand(i + 1), r2 = rand(i + 7.3), r3 = rand(i + 3.1);
          const life = 2 + r3 * 2, ph = ((lt * sp + r1 * life) % life) / life;
          const x = (r1 - .5) * e2.w, y = (kind === "bubbles" ? (0.5 - ph) : (r2 - .5)) * e2.h + (kind === "confetti" ? ph * e2.h * .5 : 0);
          p.style.transform = `translate(${x}px,${y}px) rotate(${ph * 360 * (kind === "confetti" ? 2 : 0)}deg) scale(${kind === "sparkles" ? Math.sin(ph * Math.PI) : 1})`;
          p.style.opacity = kind === "sparkles" ? Math.sin(ph * Math.PI) : 1 - ph * .6;
        });
        if (svg) {
          const pts = []; for (let i = 0; i <= 40; i++) { const u = i / 40; pts.push(`${u * 1000},${500 + Math.sin(u * 6.2 + lt * 1.6 * sp) * 210 + Math.sin(u * 2.3 - lt * sp) * 90}`); }
          svg.setAttribute("d", "M" + pts.join(" L")); svg.style.strokeWidth = el.thickness || 90;
        }
        applyAnim(inner, ws.st, extra);
        return true;
      }
    };
  };

  // Hand-drawn marks: circle, underline, arrow, box, cross, check, highlight
  C.scribble = function (el, root) {
    const e2 = Object.assign({ w: 360, h: 160, in: "none", out: "fade" }, el);
    const { outer, inner } = base(e2, root);
    const kind = el.kind || "circle";
    const paths = {
      circle: "M 520 90 C 760 80 960 190 940 330 C 920 470 640 520 430 505 C 200 490 40 420 60 290 C 80 160 300 70 560 95",
      underline: "M 20 520 C 260 470 600 490 980 455",
      arrow: "M 40 900 C 200 700 500 520 900 140 M 900 140 L 700 170 M 900 140 L 860 340",
      box: "M 40 60 L 960 50 L 950 560 L 50 570 Z",
      cross: "M 80 80 L 920 920 M 920 80 L 80 920",
      check: "M 80 520 L 380 860 L 940 120",
      highlight: "M 0 500 L 1000 500",
      zigzag: "M 20 500 L 140 380 L 260 600 L 380 380 L 500 600 L 620 380 L 740 600 L 860 380 L 980 500",
    };
    const vb = kind === "circle" || kind === "box" ? "0 0 1000 600" : "0 0 1000 1000";
    inner.innerHTML = `<svg viewBox="${vb}" preserveAspectRatio="none" width="100%" height="100%"><path d="${paths[kind] || paths.circle}" fill="none" stroke="${el.color || "var(--c-mark)"}" stroke-width="${el.strokeWidth || (kind === "highlight" ? 380 : 18)}" stroke-linecap="round" stroke-linejoin="round" vector-effect="${kind === "highlight" ? "" : "non-scaling-stroke"}" ${kind === "highlight" ? 'opacity="0.45"' : ""}/></svg>`;
    const p = inner.querySelector("path");
    const L = 4000;
    p.style.strokeDasharray = L;
    return {
      layer: el.layer || "front",
      update(t) {
        const ws = windowState(e2, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        const k = E.inOut(clamp(ws.lt / (el.drawDur || 0.5)));
        p.style.strokeDashoffset = L * (1 - k);
        applyAnim(inner, ws.st);
        return true;
      }
    };
  };

  // Progress bar
  C.progress = function (el, root) {
    const outer = h("div", "el el-progress " + (el.className || ""), root);
    const fill = h("div", "progress-fill", outer);
    styleObj(outer, el.style);
    if (el.position === "bottom") { outer.style.bottom = "0"; } else outer.style.top = "0";
    return { layer: el.layer || "front", update(t) { fill.style.width = clamp(t / P.output.duration) * 100 + "%"; return true; } };
  };

  // Background (opaque, for bg layer)
  C.background = function (el, root) {
    const outer = h("div", "el el-background bg-" + (el.kind || "solid") + " " + (el.className || ""), root);
    outer.style.inset = "0";
    styleObj(outer, el.style);
    if (el.image) { outer.style.backgroundImage = `url(${el.image})`; outer.style.backgroundSize = "cover"; outer.style.backgroundPosition = "center"; }
    return {
      layer: el.layer || "bg",
      update(t) {
        if (el.start != null && (t < el.start || t >= (el.end || 1e9))) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        if (el.kind === "mesh" || el.kind === "gradient") outer.style.backgroundPosition = `${50 + Math.sin(t * .3) * 30}% ${50 + Math.cos(t * .25) * 30}%`;
        return true;
      }
    };
  };

  // Emoji burst
  C.burst = function (el, root) {
    const e2 = Object.assign({ w: 10, h: 10, in: "none", out: "none" }, el);
    const { outer, inner } = base(e2, root);
    const chars = graphemes(el.chars || "✨");
    const n = el.count || 8;
    const ps = []; for (let i = 0; i < n; i++) ps.push(h("span", "burst-p", inner, esc(chars[i % chars.length])));
    return {
      layer: el.layer || "front",
      update(t) {
        const ws = windowState(e2, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        const k = clamp(ws.lt / (el.burstDur || 0.9));
        ps.forEach((p, i) => {
          const a = (i / n) * Math.PI * 2 + rand(i) * 0.6, d = (el.radius || 260) * E.out(k) * (0.7 + rand(i + 2) * 0.5);
          p.style.transform = `translate(${Math.cos(a) * d}px,${Math.sin(a) * d + k * k * 120}px) scale(${lerp(0.3, 1.2, E.back(clamp(k * 2)))}) rotate(${(rand(i + 5) - .5) * 90 * k}deg)`;
          p.style.opacity = 1 - clamp((k - 0.6) / 0.4);
        });
        return true;
      }
    };
  };

  // News ticker
  C.ticker = function (el, root) {
    const outer = h("div", "el el-ticker " + (el.className || ""), root);
    outer.style.top = px(el.y != null ? el.y : H - 140);
    if (el.label) h("div", "ticker-label", outer, esc(el.label));
    const track = h("div", "ticker-track", outer);
    const txt = h("div", "ticker-text", track, esc((el.text + "  •  ").repeat(6)));
    return {
      layer: el.layer || "front",
      update(t) {
        if (el.start != null && (t < el.start || t >= (el.end || 1e9))) { outer.style.display = "none"; return false; }
        outer.style.display = ""; txt.style.transform = `translateX(${-(t * (el.speed || 140)) % 2000}px)`; return true;
      }
    };
  };

  // REC / timecode overlay (VHS, camcorder)
  C.rec = function (el, root) {
    const outer = h("div", "el el-rec " + (el.className || ""), root);
    const dot = h("span", "rec-dot", outer); h("span", "rec-label", outer, esc(el.label || "REC"));
    const tc = h("div", "rec-tc", outer);
    const d0 = el.date || "JAN 01 1997";
    return {
      layer: el.layer || "front",
      update(t) {
        dot.style.opacity = Math.floor(t * 1.5) % 2 ? 0.2 : 1;
        const s = Math.floor(t + (el.offset || 0)); tc.textContent = `${d0}  ${String(Math.floor(s / 3600)).padStart(2, "0")}:${String(Math.floor(s / 60) % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
        return true;
      }
    };
  };

  // Full-screen flash / colour hit. times: [t...] | "beats" | "downbeats"
  C.flash = function (el, root) {
    const outer = h("div", "el el-flash", root); outer.style.inset = "0"; outer.style.background = el.color || "#fff";
    const times = timesOf(el.times);
    const d = el.dur || 0.18;
    return {
      layer: el.layer || "front",
      update(t) {
        let o = 0; times.forEach(x => { if (t >= x && t < x + d) o = Math.max(o, 1 - (t - x) / d); });
        if (el.start != null && (t < el.start || t >= (el.end || 1e9))) o = 0;
        outer.style.opacity = o * (el.opacity || 0.8); outer.style.display = o > 0 ? "" : "none"; return o > 0;
      }
    };
  };

  // Before / after wipe compare (two images or clips)
  C.compare = function (el, root) {
    const e2 = Object.assign({ w: W * 0.9, h: H * 0.5 }, el);
    const { outer, inner } = base(e2, root);
    inner.classList.add("compare");
    const a = h("div", "cmp-a", inner), b = h("div", "cmp-b", inner);
    const ia = h("img", "", a), ib = h("img", "", b);
    if (el.before) ia.src = el.before; if (el.after) ib.src = el.after;
    h("div", "cmp-tag cmp-tag-a", inner, esc(el.beforeLabel || "BEFORE"));
    h("div", "cmp-tag cmp-tag-b", inner, esc(el.afterLabel || "AFTER"));
    const handle = h("div", "cmp-handle", inner);
    return {
      layer: el.layer || "front",
      update(t) {
        const ws = windowState(e2, t);
        if (!ws) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        applyAnim(inner, ws.st);
        const k = E.inOut(clamp((ws.lt - (el.wipeDelay || 0.8)) / (el.wipeDur || 1.4)));
        const pos = lerp(100, el.wipeTo != null ? el.wipeTo : 0, k);
        b.style.clipPath = `inset(0 0 0 ${pos}%)`; handle.style.left = pos + "%";
        return true;
      }
    };
  };

  // Audio-reactive-looking bars (deterministic pseudo spectrum)
  const fakeLevel = (t, i, speaking) => 0.15 + speaking * 0.85 * Math.abs(Math.sin(t * (5 + rand(i) * 9) + i)) * (0.5 + rand(i + 9) * .5);
  const isSpeaking = t => (P.words || []).some(w => t >= w.start && t <= w.end) ? 1 : 0.25;
  C.equalizer = function (el, root) {
    const e2 = Object.assign({ w: W * 0.8, h: 180 }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("eq");
    const n = el.count || 32; const bars = []; for (let i = 0; i < n; i++) bars.push(h("i", "", inner));
    return {
      layer: el.layer || "front",
      update(t) {
        const ws = windowState(e2, t); if (!ws) { outer.style.display = "none"; return false; } outer.style.display = "";
        const speaking = isSpeaking(t);
        bars.forEach((b, i) => { b.style.transform = `scaleY(${fakeLevel(t, i, speaking)})`; });
        applyAnim(inner, ws.st); return true;
      }
    };
  };

  // Rating stars (only for real reviews supplied by the user)
  C.stars = function (el, root) {
    const { outer, inner } = base(el, root); inner.classList.add("stars");
    const n = el.count || 5, ss = []; for (let i = 0; i < n; i++) ss.push(h("span", "star", inner, "★"));
    return {
      layer: el.layer || "front",
      update(t) {
        const ws = windowState(el, t); if (!ws) { outer.style.display = "none"; return false; } outer.style.display = "";
        applyAnim(inner, ws.st); ss.forEach((s, i) => applyAnim(s, animState("pop", clamp((ws.lt - i * 0.12) / 0.3), "in"))); return true;
      }
    };
  };

  // =====================================================================
  // 6. motion-upgrade components
  // =====================================================================

  // Countdown ring + number. from (s), label, warnAt, delay
  C.timer = function (el, root) {
    const e2 = Object.assign({ w: 380, h: 380, in: "springPop" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("timer");
    const CIRC = 2 * Math.PI * 45;
    inner.innerHTML = `<svg viewBox="0 0 100 100"><circle class="timer-track" cx="50" cy="50" r="45"/><circle class="timer-ring" cx="50" cy="50" r="45" transform="rotate(-90 50 50)" stroke-dasharray="${CIRC}"/></svg><div class="timer-num"></div>` + (el.label ? `<div class="timer-label">${esc(el.label)}</div>` : "");
    const ring = inner.querySelector(".timer-ring"), num = inner.querySelector(".timer-num");
    const total = el.from != null ? el.from : 10, delay = el.delay || 0, warnAt = el.warnAt != null ? el.warnAt : 3;
    let last = "";
    return windowed(e2, outer, inner, (t, ws) => {
      const gone = clamp(ws.lt - delay, 0, total), remain = total - gone;
      ring.style.strokeDashoffset = CIRC * (gone / total);
      const sec = Math.ceil(remain - 1e-6);
      const txt = total >= 60 ? `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}` : String(sec);
      if (txt !== last) { num.textContent = txt; last = txt; }
      const pulse = gone > 0 && remain > 0 ? 0.12 * Math.exp(-(gone % 1) * 7) : 0;
      num.style.transform = `scale(${1 + pulse})`;
      inner.classList.toggle("is-warn", remain <= warnAt);
    });
  };

  // Poll: question + 2-3 options whose bars fill to pct at revealAt (s after start)
  C.poll = function (el, root) {
    const e2 = Object.assign({ w: W * 0.84, in: "springPop" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("poll");
    if (el.question) h("div", "poll-q", inner, esc(el.question));
    const opts = el.options || [], best = Math.max(0, ...opts.map(o => o.pct || 0));
    const rows = opts.map((o, i) => {
      const r = h("div", "poll-opt" + ((o.pct || 0) === best ? " is-win" : ""), inner);
      const fill = h("div", "poll-fill", r);
      h("div", "poll-label", r, esc(o.label));
      return { r, fill, pct: h("div", "poll-pct", r), o, i };
    });
    if (el.footer) h("div", "poll-foot", inner, esc(el.footer));
    const at = el.revealAt != null ? el.revealAt : 0.7;
    return windowed(e2, outer, inner, (t, ws) => rows.forEach(R => {
      applyAnim(R.r, animState("rise", clamp((ws.lt - 0.15 - R.i * 0.1) / 0.35), "in"));
      const k = E.expoOut(clamp((ws.lt - at - R.i * 0.08) / 0.9)), v = (R.o.pct || 0) * k;
      R.fill.style.transform = `scaleX(${(v / 100).toFixed(4)})`;
      R.pct.textContent = Math.round(v) + "%";
      R.r.classList.toggle("is-done", k > 0.97);
    }));
  };

  // Chat thread: messages [{text, side:"left"|"right", at, name}], typing dots before incoming messages
  C.chat = function (el, root) {
    const e2 = Object.assign({ w: W * 0.86, h: H * 0.46, in: "rise" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("chat");
    if (el.title) { const hd = h("div", "chat-head", inner); h("div", "chat-avatar", hd, esc(el.avatar || el.title[0])); h("div", "chat-title", hd, esc(el.title) + (el.status ? `<span>${esc(el.status)}</span>` : "")); }
    const list = h("div", "chat-list", inner);
    const s0 = el.start || 0;
    const msgs = (el.messages || []).map((m, i) => ({ m, at: m.at != null ? m.at : s0 + 0.5 + i * 1.1, side: m.side === "right" || m.side === "me" ? "right" : "left" })).sort((a, b) => a.at - b.at);
    msgs.forEach(M => {
      M.node = h("div", "chat-msg chat-" + M.side, list);
      if (M.m.name) h("div", "chat-name", M.node, esc(M.m.name));
      h("div", "chat-bubble", M.node, esc(M.m.text));
      M.node.style.display = "none";
    });
    const typing = h("div", "chat-msg chat-left chat-typing", list, '<div class="chat-bubble"><i></i><i></i><i></i></div>');
    typing.style.display = "none";
    const dots = typing.querySelectorAll("i"), TY = el.typing != null ? el.typing : 0.8;
    return windowed(e2, outer, inner, t => {
      msgs.forEach(M => {
        const vis = t >= M.at;
        M.node.style.display = vis ? "" : "none";
        if (vis) applyAnim(M.node, animState(POP.name, clamp((t - M.at) / POP.dur), "in", POP));
      });
      const nx = msgs.find(M => t < M.at);
      const show = nx && nx.side === "left" && TY > 0 && t >= nx.at - TY;
      typing.style.display = show ? "" : "none";
      if (show) dots.forEach((d, i) => { const v = (Math.sin(t * 9 - i * 0.9) + 1) / 2; d.style.transform = `translateY(${-v * 9}px)`; d.style.opacity = 0.35 + 0.65 * v; });
    });
  };

  // Phone notification banner: app, title, body, icon, time
  C.notification = function (el, root) {
    const e2 = Object.assign({ y: 130, anchor: "top", w: W * 0.92, in: { name: "push", dir: "down" }, out: { name: "push", dir: "down" }, inDur: 0.6, outDur: 0.45 }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("notif");
    const top = h("div", "notif-top", inner);
    h("div", "notif-icon", top, esc(el.icon || (el.app || "A")[0]));
    h("div", "notif-app", top, esc(el.app || "Messages"));
    h("div", "notif-time", top, esc(el.time || "now"));
    if (el.title) h("div", "notif-title", inner, esc(el.title));
    if (el.body) h("div", "notif-body", inner, esc(el.body));
    return windowed(e2, outer, inner);
  };

  // Search bar: query typed at cps with cursor, then results drop in
  const SEARCH_ICON = '<svg viewBox="0 0 24 24" class="sb-icon"><circle cx="10.5" cy="10.5" r="6.5"/><line x1="15.5" y1="15.5" x2="21" y2="21"/></svg>';
  C.searchbar = function (el, root) {
    const e2 = Object.assign({ y: H * 0.24, anchor: "top", w: W * 0.88, in: "rise" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("search");
    const bar = h("div", "sb-bar", inner, SEARCH_ICON);
    const field = h("div", "sb-field", bar);
    const ph = el.placeholder ? h("span", "sb-ph", field, esc(el.placeholder)) : null;
    const on = h("span", "sb-text", field), cur = h("span", "sb-cursor", field);
    const res = h("div", "sb-results", inner);
    const q = String(el.query || ""), qc = graphemes(q), cps = el.cps || 14, delay = el.delay != null ? el.delay : 0.35;
    const qre = q ? new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i") : null;
    const items = (el.results || []).map(r => {
      const s = String(r), m = qre && s.match(qre);
      const html = m ? esc(s.slice(0, m.index)) + "<b>" + esc(m[0]) + "</b>" + esc(s.slice(m.index + m[0].length)) : esc(s);
      return h("div", "sb-item", res, SEARCH_ICON + `<span>${html}</span>`);
    });
    if (!items.length) res.style.display = "none";
    const typedEnd = delay + qc.length / cps;
    let last = -1;
    return windowed(e2, outer, inner, (t, ws) => {
      const n = clamp(Math.floor((ws.lt - delay) * cps), 0, qc.length);
      if (n !== last) { on.textContent = qc.slice(0, n).join(""); if (ph) ph.style.display = n ? "none" : ""; last = n; }
      cur.style.opacity = n < qc.length && ws.lt >= delay ? 1 : (Math.floor(ws.lt / 0.53) % 2 ? 0 : 1);
      if (items.length) {
        applyAnim(res, animState("unfold", clamp((ws.lt - typedEnd - 0.2) / 0.3), "in"));
        items.forEach((it, i) => applyAnim(it, animState("drop", clamp((ws.lt - typedEnd - 0.3 - i * 0.1) / 0.3), "in")));
      }
    });
  };

  // Code block typed line by line: code, title, cps, linePause, lineNumbers, diff (+/- lines)
  const KW = "const|let|var|function|return|if|else|for|while|class|import|from|export|default|def|async|await|new|try|catch|throw|in|of|and|or|not|elif|lambda|with|as|pass|yield|public|private|static|void|int|string|bool|true|false|null|undefined|None|True|False|self|this|fn|pub|struct|impl|match|use|mut";
  const TOKEN_RE = new RegExp(`(\\/\\/.*$|#.*$)|("(?:[^"\\\\]|\\\\.)*"|'(?:[^'\\\\]|\\\\.)*'|\`[^\`]*\`)|\\b(\\d+(?:\\.\\d+)?)\\b|\\b(${KW})\\b|([A-Za-z_]\\w*)(?=\\s*\\()`, "g");
  function highlightCode(line) {
    let out = "", last = 0, m; TOKEN_RE.lastIndex = 0;
    while ((m = TOKEN_RE.exec(line))) {
      out += esc(line.slice(last, m.index));
      const cls = m[1] ? "c" : m[2] ? "s" : m[3] ? "n" : m[4] ? "k" : "f";
      out += `<span class="tk-${cls}">${esc(m[0])}</span>`;
      last = TOKEN_RE.lastIndex;
    }
    return out + esc(line.slice(last));
  }
  C.codeblock = function (el, root) {
    const e2 = Object.assign({ w: W * 0.9, in: "rise" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("code");
    const head = h("div", "code-head", inner, "<i></i><i></i><i></i>");
    if (el.title) h("span", "code-title", head, esc(el.title));
    const body = h("div", "code-body", inner);
    const src = String(el.code || "").replace(/\t/g, "  ").replace(/\n$/, "").split("\n");
    const diff = el.diff === true || el.lang === "diff";
    const cps = el.cps || 38, pause = el.linePause != null ? el.linePause : 0.12;
    let tt = el.delay != null ? el.delay : 0.35;
    const lines = src.map((L, i) => {
      const sign = diff && /^[+-]/.test(L) ? L[0] : "";
      const row = h("div", "code-line" + (sign === "+" ? " is-add" : sign === "-" ? " is-del" : ""), body);
      if (el.lineNumbers !== false) h("span", "code-ln", row, String(i + 1));
      if (diff) h("span", "code-sign", row, sign || "&nbsp;");
      const text = sign ? L.slice(1) : L;
      const wrap = h("span", "code-wrap", row);
      const tx = h("span", "code-text", wrap, highlightCode(text) || "&nbsp;");
      const car = h("span", "code-caret", wrap);
      const len = Array.from(text).length, t0 = tt;
      tt += len / cps + pause;
      return { row, tx, car, len, t0 };
    });
    return windowed(e2, outer, inner, (t, ws) => {
      let active = -1;
      lines.forEach((L, i) => { if (ws.lt >= L.t0) active = i; });
      lines.forEach((L, i) => {
        const n = clamp(Math.floor((ws.lt - L.t0) * cps), 0, L.len);
        L.row.style.visibility = ws.lt >= L.t0 || el.showAll ? "" : "hidden";
        L.tx.style.clipPath = n >= L.len ? "" : `inset(-20% calc(100% - ${n}ch) -20% 0)`;
        L.car.style.left = n + "ch";
        L.car.style.opacity = i !== active ? 0 : (n < L.len ? 1 : (Math.floor(ws.lt / 0.53) % 2 ? 0 : 1));
      });
    });
  };

  // Callout: dot at point [x,y] (or the face), leader line draws to a label box at x,y
  C.callout = function (el, root) {
    const lx = el.x != null ? el.x : W * 0.5, ly = el.y != null ? el.y : H * 0.3, pt = el.point || [W * 0.5, H * 0.5];
    const e2 = fullFrame(el, { in: el.in || "fade", inDur: el.inDur != null ? el.inDur : 0.15 });
    const { outer, inner } = base(e2, root); inner.classList.add("callout");
    inner.innerHTML = `<svg class="co-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}"><line class="co-line"/><circle class="co-ring"/><circle class="co-dot"/></svg>`;
    const line = inner.querySelector(".co-line"), dot = inner.querySelector(".co-dot"), ring = inner.querySelector(".co-ring");
    if (el.color) inner.style.setProperty("--co", el.color);
    const box = h("div", "co-label", inner);
    const [ax, ay] = anchorShift(el.anchor);
    box.style.left = lx + "px"; box.style.top = ly + "px"; box.style.transform = `translate(${ax}%,${ay}%)`;
    const boxIn = h("div", "co-label-in", box, (el.title ? `<div class="co-title">${esc(el.title)}</div>` : "") + (el.text ? `<div class="co-text">${esc(el.text)}</div>` : ""));
    const drawDur = el.drawDur || 0.45, LS = animSpec(el.labelIn || POP, null, 0.4, null);
    return windowed(e2, outer, inner, (t, ws) => {
      let [x0, y0] = pt;
      if (el.anchorTo === "face") { const c = faceCentre(t, el.offset); if (c) { x0 = c[0]; y0 = c[1]; } }
      const L = Math.hypot(lx - x0, ly - y0);
      line.setAttribute("x1", x0); line.setAttribute("y1", y0); line.setAttribute("x2", lx); line.setAttribute("y2", ly);
      line.style.strokeDasharray = L; line.style.strokeDashoffset = L * (1 - E.inOut(clamp((ws.lt - 0.12) / drawDur)));
      const dk = clamp(ws.lt / 0.3), ph = ((ws.lt + 0.6) % 1.4) / 1.4;
      dot.setAttribute("cx", x0); dot.setAttribute("cy", y0); dot.setAttribute("r", (14 * E.backOut(dk)).toFixed(2));
      ring.setAttribute("cx", x0); ring.setAttribute("cy", y0); ring.setAttribute("r", (14 + 34 * ph).toFixed(2)); ring.style.opacity = dk * (1 - ph);
      applyAnim(boxIn, animState(LS.name, clamp((ws.lt - 0.12 - drawDur * 0.75) / LS.dur), "in", LS));
    });
  };

  // Pointer / arrow at target x,y. kind "arrow" (drawn from `from`) | "hand" (tapping emoji + ripple)
  C.pointer = function (el, root) {
    const tx = el.x != null ? el.x : W / 2, ty = el.y != null ? el.y : H / 2;
    const from = el.from || [tx + 220, ty + 280];
    const e2 = fullFrame(el, { in: el.in || "fade", inDur: el.inDur != null ? el.inDur : 0.12 });
    const { outer, inner } = base(e2, root); inner.classList.add("pointer");
    if (el.color) inner.style.setProperty("--pt", el.color);
    const kind = el.kind || "arrow";
    if (kind === "hand") {
      inner.innerHTML = `<svg class="pt-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}"><circle class="pt-ripple" cx="${tx}" cy="${ty}"/></svg>`;
      const rip = inner.querySelector(".pt-ripple");
      const hand = h("div", "pt-hand", inner, `<span>${esc(el.emoji || "👆")}</span>`);
      const hi = hand.firstChild, period = el.period || 0.9;
      return windowed(e2, outer, inner, (t, ws) => {
        const k = E.expoOut(clamp(ws.lt / 0.5)), ph = Math.max(0, ws.lt - 0.5) % period / period;
        const press = ws.lt > 0.5 && ph < 0.18 ? Math.sin(ph / 0.18 * Math.PI) : 0;
        hand.style.left = lerp(from[0], tx, k) + "px"; hand.style.top = lerp(from[1], ty, k) + "px";
        hi.style.transform = `translateY(${press * 14}px) scale(${1 - press * 0.08})`;
        const rp = ws.lt > 0.5 ? clamp(ph / 0.7) : 0;
        rip.setAttribute("r", (10 + rp * 70).toFixed(1)); rip.style.opacity = ws.lt > 0.5 ? (1 - rp) * 0.9 : 0;
      });
    }
    // arrow: quadratic curve from -> target, bowed by `curve`
    const dx = tx - from[0], dy = ty - from[1], len = Math.hypot(dx, dy) || 1, cv = el.curve != null ? el.curve : 0.22;
    const cx = (from[0] + tx) / 2 - dy / len * len * cv, cy = (from[1] + ty) / 2 + dx / len * len * cv;
    const gap = el.gap != null ? el.gap : 18;   // stop short of the target
    const ex = tx - (tx - cx) / Math.hypot(tx - cx, ty - cy) * gap, ey = ty - (ty - cy) / Math.hypot(tx - cx, ty - cy) * gap;
    const ang = Math.atan2(ey - cy, ex - cx), hl = el.headSize || 44;
    const hp = a => `${ex + Math.cos(ang + Math.PI + a) * hl},${ey + Math.sin(ang + Math.PI + a) * hl}`;
    inner.innerHTML = `<svg class="pt-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}"><g class="pt-g"><path class="pt-shaft" d="M${from[0]},${from[1]} Q${cx},${cy} ${ex},${ey}"/><path class="pt-head" d="M${hp(0.45)} L${ex},${ey} L${hp(-0.45)}"/></g></svg>`;
    const shaft = inner.querySelector(".pt-shaft"), head = inner.querySelector(".pt-head"), g = inner.querySelector(".pt-g");
    let SL = 0; const drawDur = el.drawDur || 0.45;
    return windowed(e2, outer, inner, (t, ws) => {
      if (!SL) { SL = shaft.getTotalLength(); shaft.style.strokeDasharray = SL; head.style.strokeDasharray = 200; }
      const k = E.inOut(clamp(ws.lt / drawDur));
      shaft.style.strokeDashoffset = SL * (1 - k);
      head.style.strokeDashoffset = 200 * (1 - E.out(clamp((ws.lt - drawDur * 0.85) / 0.2)));
      const nud = ws.lt > drawDur + 0.2 ? Math.sin((ws.lt - drawDur - 0.2) * 7) * 7 : 0;
      g.setAttribute("transform", `translate(${(Math.cos(ang) * nud).toFixed(2)},${(Math.sin(ang) * nud).toFixed(2)})`);
    });
  };
  C.arrow = C.pointer;

  // Stylised map: seeded dot-grid "land" (no real map data) + pins {x,y in 0..1,label} + dashed route
  C.map = function (el, root) {
    const e2 = Object.assign({ w: W * 0.9, h: W * 0.9 * 0.62, in: "fade", inDur: 0.5 }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("map");
    const VW = 1000, VH = 620, seed = el.seed || 7, id = "m" + (el._i || 0);
    let dots = "";
    for (let gx = 14; gx < VW; gx += 18) for (let gy = 14; gy < VH; gy += 18) {
      const edge = Math.min(gx / VW, 1 - gx / VW, (gy / VH) * 0.62, (1 - gy / VH) * 0.62);
      const n = noise2(gx * 0.0065, gy * 0.0095, seed) + 0.45 * noise2(gx * 0.02, gy * 0.026, seed + 5) - (edge < 0.05 ? 1 : 0);
      if (n > 0.1) dots += `M${gx} ${gy}h0`;
    }
    let grid = "";
    for (let x = 100; x < VW; x += 100) grid += `M${x} 0V${VH}`;
    for (let y = 103; y < VH; y += 103) grid += `M0 ${y}H${VW}`;
    const pins = (el.pins || []).map(p => ({ x: p.x * VW, y: p.y * VH, label: p.label }));
    const legs = [];
    for (let j = 1; j < pins.length; j++) {
      const a = pins[j - 1], b = pins[j], dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy) || 1;
      let nx = dy / L, ny = -dx / L; if (ny > 0) { nx = -nx; ny = -ny; }     // bow upwards
      legs.push(`M${a.x},${a.y} Q${(a.x + b.x) / 2 + nx * L * 0.22},${(a.y + b.y) / 2 + ny * L * 0.22} ${b.x},${b.y}`);
    }
    inner.innerHTML = `<svg viewBox="0 0 ${VW} ${VH}" class="map-svg"><rect class="map-sea" width="${VW}" height="${VH}" rx="28"/><path class="map-grid" d="${grid}"/><path class="map-land" d="${dots}"/>` +
      `<defs>${legs.map((d, j) => `<mask id="${id}k${j}" maskUnits="userSpaceOnUse" x="0" y="0" width="${VW}" height="${VH}"><path class="map-reveal" d="${d}"/></mask>`).join("")}</defs>` +
      legs.map((d, j) => `<path class="map-route" d="${d}" mask="url(#${id}k${j})"/>`).join("") +
      pins.map(p => `<g class="map-pin" transform="translate(${p.x} ${p.y})"><g class="pin-in"><circle class="pin-pulse" r="16"/><circle class="pin-dot" r="11"/>${p.label ? `<text class="pin-label" y="-28">${esc(p.label)}</text>` : ""}</g></g>`).join("") +
      `<circle class="map-traveler" r="9"/></svg>`;
    if (el.title) h("div", "map-title", inner, esc(el.title));
    const reveals = Array.from(inner.querySelectorAll(".map-reveal")), routes = Array.from(inner.querySelectorAll(".map-route"));
    const pinG = Array.from(inner.querySelectorAll(".pin-in")), pulses = Array.from(inner.querySelectorAll(".pin-pulse")), trav = inner.querySelector(".map-traveler");
    const rd = el.routeDelay != null ? el.routeDelay : 0.6, legDur = el.legDur || 1.0;
    let lens = null;
    return windowed(e2, outer, inner, (t, ws) => {
      if (!lens) { lens = reveals.map(r => r.getTotalLength()); reveals.forEach((r, j) => { r.style.strokeDasharray = lens[j]; }); }
      let tip = null;
      reveals.forEach((r, j) => {
        const k = clamp((ws.lt - rd - j * legDur) / legDur), e = E.inOut(k);
        r.style.strokeDashoffset = lens[j] * (1 - e);
        if (k > 0 && k < 1) tip = routes[j].getPointAtLength(e * lens[j]);
      });
      pinG.forEach((g, j) => {
        const at = j === 0 ? rd - 0.35 : rd + j * legDur - 0.05, k = clamp((ws.lt - at) / 0.45);
        g.setAttribute("transform", `scale(${Math.max(0, spring(k * 0.45, { stiffness: 260, damping: 14 })).toFixed(3)})`);
        const ph = ((ws.lt - at) % 1.6) / 1.6;
        pulses[j].setAttribute("r", (11 + ph * 26).toFixed(1)); pulses[j].style.opacity = k >= 1 ? (1 - ph) * 0.6 : 0;
      });
      trav.style.display = tip ? "" : "none";
      if (tip) { trav.setAttribute("cx", tip.x); trav.setAttribute("cy", tip.y); }
    });
  };

  // Bar chart race: data [{label, values:[...], color}], labels (period names), top, raceDur
  C.barrace = function (el, root) {
    const data = el.data || [], top = Math.min(el.top || 6, data.length || 1);
    const e2 = Object.assign({ w: W * 0.9, h: 150 + top * 110, in: "rise" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("race");
    if (el.title) h("div", "race-title", inner, esc(el.title));
    const area = h("div", "race-area", inner); area.style.setProperty("--top", top);
    const period = h("div", "race-period", inner);
    const steps = Math.max(1, ...data.map(d => d.values.length));
    const rows = data.map((d, i) => {
      const r = h("div", "race-row", area); r.style.setProperty("--rc", d.color || PALETTE[i % PALETTE.length]);
      h("div", "race-label", r, esc(d.label));
      const tr = h("div", "race-track", r), fill = h("div", "race-fill", tr);
      return { r, fill, val: h("div", "race-val", tr) };
    });
    const valuesAt = f => { const i0 = Math.floor(f), u = f - i0; return data.map(d => { const v = d.values, a = v[Math.min(i0, v.length - 1)] || 0, b = v[Math.min(i0 + 1, v.length - 1)] || 0; return lerp(a, b, u); }); };
    const ranksAt = f => { const v = valuesAt(f), ord = v.map((_, i) => i).sort((a, b) => v[b] - v[a] || a - b), r = []; ord.forEach((idx, rank) => { r[idx] = rank; }); return r; };
    const delay = el.delay != null ? el.delay : 0.4;
    return windowed(e2, outer, inner, (t, ws) => {
      const span = el.raceDur || Math.max(1, Math.min(ws.dur, P.output.duration) - delay - 1.0);
      const fAt = lt => clamp((lt - delay) / span) * (steps - 1);
      const f = fAt(ws.lt), v = valuesAt(f), maxV = Math.max(...v) || 1;
      const pos = data.map(() => 0);
      for (let k = 0; k < 6; k++) ranksAt(fAt(ws.lt - k * 0.05)).forEach((r, i) => { pos[i] += r / 6; });   // smooth re-sort
      rows.forEach((R, i) => {
        R.r.style.transform = `translateY(${(pos[i] * 100).toFixed(2)}%)`;
        R.r.style.opacity = clamp(top - pos[i]);
        R.fill.style.width = (v[i] / maxV * 100).toFixed(2) + "%";
        R.val.textContent = (el.prefix || "") + fmtNum(v[i], el.decimals || 0, el.compact) + (el.suffix || "");
      });
      const lab = (el.labels || [])[Math.round(f)];
      period.textContent = lab != null ? lab : "";
    });
  };

  // Line chart: series [{values, label, color}] (or values), labels (x), min/max, drawDur
  C.linechart = function (el, root) {
    const e2 = Object.assign({ w: W * 0.88, in: "rise" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("lc");
    if (el.title) h("div", "lc-title", inner, esc(el.title));
    const series = el.series || [{ values: el.values || [], label: el.label, color: el.color }];
    const all = series.flatMap(s => s.values);
    const minV = el.min != null ? el.min : Math.min(0, ...all), maxV = el.max != null ? el.max : (Math.max(...all) * 1.1 || 1);
    const CW = 1000, CH = 600, pl = 24, pr = 150, pt = 40, pb = el.labels ? 70 : 24;
    const X = (i, n) => pl + (CW - pl - pr) * (n <= 1 ? 0 : i / (n - 1)), Y = v => CH - pb - (CH - pt - pb) * (v - minV) / ((maxV - minV) || 1);
    let svg = `<svg viewBox="0 0 ${CW} ${CH}" class="lc-svg"><defs>`;
    series.forEach((s, j) => { svg += `<linearGradient id="lg${el._i}_${j}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${s.color || PALETTE[j]}" stop-opacity=".35"/><stop offset="1" stop-color="${s.color || PALETTE[j]}" stop-opacity="0"/></linearGradient><clipPath id="lcc${el._i}_${j}"><rect class="lc-clip" x="0" y="0" height="${CH}" width="0"/></clipPath>`; });
    svg += `</defs>`;
    for (let g = 0; g <= 4; g++) { const y = pt + (CH - pt - pb) * g / 4; svg += `<line class="lc-grid" x1="${pl}" x2="${CW - pr}" y1="${y}" y2="${y}"/>`; }
    (el.labels || []).forEach((l, i, arr) => { svg += `<text class="lc-x" x="${X(i, arr.length)}" y="${CH - 20}">${esc(l)}</text>`; });
    const geo = series.map((s, j) => {
      const n = s.values.length, pts = s.values.map((v, i) => [X(i, n), Y(v)]);
      const cum = [0]; for (let i = 1; i < n; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
      const d = "M" + pts.map(p => p.join(",")).join(" L");
      const col = s.color || PALETTE[j];
      svg += `<path class="lc-area" d="${d} L${pts[n - 1][0]},${CH - pb} L${pts[0][0]},${CH - pb} Z" fill="url(#lg${el._i}_${j})" clip-path="url(#lcc${el._i}_${j})"/>`;
      svg += `<path class="lc-line" d="${d}" stroke="${col}" style="stroke-dasharray:${cum[n - 1] || 1};stroke-dashoffset:${cum[n - 1] || 1}"/>`;
      pts.forEach(p => { svg += `<circle class="lc-pt" cx="${p[0]}" cy="${p[1]}" r="0" stroke="${col}"/>`; });
      svg += `<text class="lc-end" x="${pts[n - 1][0] + 22}" y="${pts[n - 1][1] + 12}" fill="${col}">${esc((el.prefix || "") + fmtNum(s.values[n - 1], el.decimals || 0, el.compact) + (el.suffix || ""))}</text>`;
      return { n, pts, cum, total: cum[n - 1] || 1 };
    });
    inner.insertAdjacentHTML("beforeend", svg + "</svg>");
    if (series.some(s => s.label)) h("div", "lc-legend", inner, series.map((s, j) => s.label ? `<span><i style="background:${s.color || PALETTE[j]}"></i>${esc(s.label)}</span>` : "").join(""));
    const lines = inner.querySelectorAll(".lc-line"), clips = inner.querySelectorAll(".lc-clip"), ends = inner.querySelectorAll(".lc-end");
    const ptsEl = inner.querySelectorAll(".lc-pt");
    const delay = el.delay != null ? el.delay : 0.3, dd = el.drawDur || 1.4;
    return windowed(e2, outer, inner, (t, ws) => {
      let pi = 0;
      geo.forEach((G, j) => {
        const k = E.inOut(clamp((ws.lt - delay - j * 0.25) / dd)), Ld = k * G.total;
        lines[j].style.strokeDashoffset = G.total - Ld;
        let xr = G.pts[0][0];
        for (let i = 0; i < G.n; i++) {
          const pk = clamp((Ld - G.cum[i]) / (G.total * 0.08 + 1) + (i === 0 && k > 0 ? 1 : 0));
          ptsEl[pi++].setAttribute("r", (9 * E.backOut(pk)).toFixed(2));
          if (G.cum[i] <= Ld) xr = G.pts[i][0];
          if (i > 0 && G.cum[i - 1] <= Ld && Ld < G.cum[i]) xr = lerp(G.pts[i - 1][0], G.pts[i][0], (Ld - G.cum[i - 1]) / (G.cum[i] - G.cum[i - 1]));
        }
        clips[j].setAttribute("width", k >= 1 ? CW : xr);
        ends[j].style.opacity = E.out(clamp((ws.lt - delay - j * 0.25 - dd) / 0.3));
      });
    });
  };

  // Pie / donut: items [{label, value, color}], donut (or type "donut"), center, centerLabel
  C.piechart = function (el, root) {
    const donut = el.donut != null ? el.donut : el.type === "donut";
    const e2 = Object.assign({ w: W * 0.84, in: "springPop" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("pie");
    if (el.title) h("div", "pie-title", inner, esc(el.title));
    const items = el.items || [], total = items.reduce((a, b) => a + b.value, 0) || 1;
    const R = donut ? 38 : 25, SW = donut ? 16 : 50, CIRC = 2 * Math.PI * R;
    let acc = 0; const segs = items.map((it, i) => { const s = { start: acc / total, frac: it.value / total, color: it.color || PALETTE[i % PALETTE.length] }; acc += it.value; return s; });
    const wrap = h("div", "pie-wrap", inner,
      `<svg viewBox="0 0 100 100" class="pie-svg">${donut ? `<circle class="pie-track" cx="50" cy="50" r="${R}" stroke-width="${SW}"/>` : ""}` +
      segs.map(s => `<circle class="pie-seg" cx="50" cy="50" r="${R}" stroke="${s.color}" stroke-width="${SW}" transform="rotate(-90 50 50)" stroke-dasharray="0 ${CIRC}"/>`).join("") + "</svg>");
    if (donut) h("div", "pie-center", wrap, `<b>${esc(el.center != null ? el.center : Math.round(segs[0] ? segs[0].frac * 100 : 0) + "%")}</b>` + (el.centerLabel || (items[0] && items[0].label) ? `<span>${esc(el.centerLabel || items[0].label)}</span>` : ""));
    const legend = h("div", "pie-legend", inner);
    const rows = items.map((it, i) => h("div", "pie-row", legend, `<i style="background:${segs[i].color}"></i><span>${esc(it.label)}</span><b>${Math.round(segs[i].frac * 100)}%</b>`));
    const circles = inner.querySelectorAll(".pie-seg"), delay = el.delay != null ? el.delay : 0.25, dur = el.drawDur || 1.1, gapU = donut ? 0.8 : 0;
    return windowed(e2, outer, inner, (t, ws) => {
      const g = E.inOut(clamp((ws.lt - delay) / dur));
      segs.forEach((s, i) => {
        const vis = clamp(g - s.start, 0, s.frac) * CIRC, len = Math.max(0, vis - (vis > gapU ? gapU : vis));
        circles[i].setAttribute("stroke-dasharray", `${len.toFixed(3)} ${CIRC}`);
        circles[i].setAttribute("stroke-dashoffset", (-s.start * CIRC).toFixed(3));
        applyAnim(rows[i], animState("slideLeft", clamp((g - s.start) / Math.max(0.05, s.frac) * 1.5), "in"));
      });
    });
  };
  C.donut = C.piechart;
  C.pie = C.piechart;

  // Waveform from real peaks: el.peaks (array or {fps, values}) or P.peaks; fallback = fake equalizer.
  // mode "scroll" (window of `span` s centred on t) | "static" (whole element span across the bars)
  C.waveform = function (el, root) {
    const e2 = Object.assign({ w: W * 0.84, h: 200 }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("wave");
    const n = el.count || 56, bars = []; for (let i = 0; i < n; i++) bars.push(h("i", "", inner));
    if (el.playhead !== false && el.mode !== "static") h("b", "wave-head", inner);
    const src = el.peaks || P.peaks || null;
    let vals = null, pf = FPS;
    if (Array.isArray(src)) { vals = src; pf = el.peaksFps || FPS; } else if (src && Array.isArray(src.values)) { vals = src.values; pf = src.fps || FPS; }
    if (!vals || !vals.length) { vals = null; inner.classList.add("is-fake"); }
    const span = el.span || 2.4, gain = el.gain || 1;
    const sample = tm => { if (tm < 0) return 0; const x = tm * pf, i = Math.floor(x); if (i >= vals.length - 1) return i === vals.length - 1 ? vals[i] : 0; return lerp(vals[i], vals[i + 1], x - i); };
    return windowed(e2, outer, inner, (t, ws) => {
      const s0 = el.start || 0, speaking = vals ? 0 : isSpeaking(t);
      bars.forEach((b, i) => {
        const tm = el.mode === "static" ? s0 + (i / (n - 1)) * ws.dur : t + (i / (n - 1) - 0.5) * span;
        const v = vals ? clamp(sample(tm) * gain) : fakeLevel(t, i, speaking);
        b.style.transform = `scaleY(${Math.max(0.05, v).toFixed(3)})`;
        b.classList.toggle("is-past", vals ? tm <= t : false);
      });
    });
  };

  // Lyric lines with word fill sweep: el.lines [{text,start,end,words?}] or grouped from P.words
  C.lyric = function (el, root) {
    const e2 = Object.assign({ w: W * 0.88, y: H * 0.62, in: "fade" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("lyric");
    let lines;
    if (el.lines) {
      lines = el.lines.map(l => {
        let ws = l.words;
        if (!ws) {
          const fromP = (P.words || []).filter(w => w.start >= l.start && w.start < l.end);
          if (fromP.length) ws = fromP;
          else { const toks = String(l.text).split(/\s+/).filter(Boolean), d = (l.end - l.start) / (toks.length || 1); ws = toks.map((w, i) => ({ w, start: l.start + i * d, end: l.start + (i + 1) * d })); }
        }
        return { text: l.text, start: l.start, end: l.end, words: ws };
      });
    } else {
      lines = []; let cur = [];
      const maxW = el.maxWords || 6;
      (P.words || []).forEach((w, i, arr) => {
        if (cur.length && (cur.length >= maxW || w.start - arr[i - 1].end > 0.6)) { lines.push(cur); cur = []; }
        cur.push(w);
        if (SENT_END.test(w.w.trim())) { lines.push(cur); cur = []; }
      });
      if (cur.length) lines.push(cur);
      lines = lines.map((ws, i, arr) => ({ text: ws.map(w => w.w).join(" "), start: ws[0].start, end: Math.min(ws[ws.length - 1].end + 0.4, arr[i + 1] ? arr[i + 1][0].start : 1e9), words: ws }));
    }
    const cur = h("div", "lyric-cur", inner), nxt = h("div", "lyric-next", inner);
    const MASK = animSpec({ name: "maskUp", dur: 0.4 }, null, 0.4, null);
    let shown = -2, fills = [];
    return windowed(e2, outer, inner, t => {
      const li = lines.findIndex(l => t >= l.start && t < l.end);
      if (li !== shown) {
        cur.innerHTML = ""; fills = [];
        if (li >= 0) lines[li].words.forEach(w => { const s = h("span", "ly-w", cur, esc(w.w)); fills.push(h("span", "ly-fill", s, esc(w.w))); cur.appendChild(document.createTextNode(" ")); });
        nxt.textContent = li >= 0 && lines[li + 1] ? lines[li + 1].text : "";
        shown = li;
      }
      if (li < 0) return;
      const L = lines[li];
      L.words.forEach((w, j) => { const p = clamp((t - w.start) / Math.max(0.05, w.end - w.start)); fills[j].style.clipPath = `inset(-10% ${((1 - p) * 100).toFixed(2)}% -10% 0)`; });
      applyAnim(cur, animState(MASK.name, clamp((t - L.start) / MASK.dur), "in", MASK));
      applyAnim(nxt, animState("fade", clamp((t - L.start - 0.15) / 0.3), "in"));
    });
  };

  // Subscribe button + bell: cursor moves in, clicks at clickAt, bell rings at bellAt (s after start)
  const BELL_SVG = '<svg viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0-6 6v4l-2 3h16l-2-3V9a6 6 0 0 0-6-6z"/><path d="M10 19a2 2 0 0 0 4 0"/></svg>';
  const CURSOR_SVG = '<svg viewBox="0 0 24 24"><path d="M4 2 L4 20 L9 15 L12.5 22 L15.5 20.6 L12 14 L19 14 Z"/></svg>';
  C.subscribe = function (el, root) {
    const e2 = Object.assign({ y: H * 0.7, in: "springPop" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("subscribe");
    const row = h("div", "sub-row", inner);
    if (el.name) { const ch = h("div", "sub-chan", row); h("div", "sub-avatar", ch, esc(el.avatar || el.name[0])); h("div", "sub-name", ch, esc(el.name) + (el.handle ? `<span>${esc(el.handle)}</span>` : "")); }
    const btn = h("div", "sub-btn", row), btnTxt = h("span", "", btn, esc(el.label || "SUBSCRIBE"));
    const bell = h("div", "sub-bell", row, BELL_SVG);
    const cursor = h("div", "sub-cursor", inner, CURSOR_SVG);
    const ripple = h("div", "sub-ripple", inner);
    const clickAt = el.clickAt != null ? el.clickAt : 0.9, bellAt = el.bellAt != null ? el.bellAt : clickAt + 0.75;
    let geo = null, on = false;
    return windowed(e2, outer, inner, (t, ws) => {
      if (!geo) geo = { bx: btn.offsetLeft + btn.offsetWidth * 0.55, by: btn.offsetTop + btn.offsetHeight * 0.6, gx: bell.offsetLeft + bell.offsetWidth * 0.55, gy: bell.offsetTop + bell.offsetHeight * 0.6 };
      const lt = ws.lt, sx = geo.bx + 260, sy = geo.by + 240;
      let cx, cy;
      if (lt < clickAt) { const k = E.expoOut(clamp((lt - 0.2) / Math.max(0.1, clickAt - 0.25))); cx = lerp(sx, geo.bx, k); cy = lerp(sy, geo.by, k); }
      else { const k = E.inOut(clamp((lt - clickAt - 0.2) / Math.max(0.1, bellAt - clickAt - 0.25))); cx = lerp(geo.bx, geo.gx, k); cy = lerp(geo.by, geo.gy, k); }
      const press = (lt >= clickAt && lt < clickAt + 0.14) || (lt >= bellAt && lt < bellAt + 0.14);
      cursor.style.transform = `translate(${cx}px,${cy}px) scale(${press ? 0.84 : 1})`;
      cursor.style.opacity = 1 - clamp((lt - bellAt - 0.5) / 0.3);
      const nowOn = lt >= clickAt;
      if (nowOn !== on) { btn.classList.toggle("is-on", nowOn); btnTxt.textContent = nowOn ? (el.doneLabel || "SUBSCRIBED") : (el.label || "SUBSCRIBE"); on = nowOn; }
      btn.style.transform = nowOn ? `scale(${(0.9 + 0.1 * spring(lt - clickAt, { stiffness: 420, damping: 16 })).toFixed(4)})` : "";
      const rp = clamp((lt - clickAt) / 0.5);
      ripple.style.transform = `translate(${geo.bx}px,${geo.by}px) scale(${(0.2 + rp * 2.2).toFixed(3)})`; ripple.style.opacity = lt >= clickAt ? (1 - rp) * 0.7 : 0;
      const db = lt - bellAt;
      bell.style.transform = db >= 0 ? `rotate(${(Math.sin(db * 26) * 24 * Math.exp(-db * 3.2)).toFixed(2)}deg)` : "";
      bell.classList.toggle("is-on", db >= 0);
    });
  };

  // Generic social post card (not a specific platform's UI): avatar, name, handle, text, likes
  C.socialpost = function (el, root) {
    const e2 = Object.assign({ w: W * 0.86, in: "springPop" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("post");
    const head = h("div", "post-head", inner);
    const av = h("div", "post-avatar", head);
    if (el.avatarImage) { const im = h("img", "", av); im.src = assetUrl(el.avatarImage); } else av.textContent = el.avatar || (el.name || "?")[0];
    h("div", "post-who", head, `<b>${esc(el.name || "")}${el.verified ? '<i class="post-badge">✓</i>' : ""}</b><span>${esc(el.handle || "")}${el.time ? " · " + esc(el.time) : ""}</span>`);
    h("div", "post-text", inner, esc(el.text || "").replace(/([#@][\w]+)/g, '<em>$1</em>').replace(/\n/g, "<br>"));
    if (el.image) { const im = h("img", "post-img", inner); im.src = el.image; }
    const act = h("div", "post-actions", inner);
    const like = h("span", "post-like", act, '<svg viewBox="0 0 24 24"><path d="M12 21s-7.5-4.6-9.6-9.2C1 8.6 3 5 6.6 5c2 0 3.3 1.1 4.1 2.3h2.6C14.1 6.1 15.4 5 17.4 5 21 5 23 8.6 21.6 11.8 19.5 16.4 12 21 12 21z"/></svg>');
    const likeN = h("b", "", like);
    if (el.comments != null) h("span", "post-stat", act, `<svg viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4z"/></svg><b>${fmtNum(el.comments, 0, true)}</b>`);
    if (el.shares != null) h("span", "post-stat", act, `<svg viewBox="0 0 24 24"><path d="M4 12l16-8-6 16-3-6z"/></svg><b>${fmtNum(el.shares, 0, true)}</b>`);
    const likeAt = el.likeAt != null ? el.likeAt : 0.8, from = el.likesFrom || 0, to = el.likes != null ? el.likes : 0, cd = el.countDur || 1.6;
    const heart = like.querySelector("svg");
    return windowed(e2, outer, inner, (t, ws) => {
      const k = E.expoOut(clamp((ws.lt - likeAt) / cd));
      likeN.textContent = fmtNum(Math.round(lerp(from, to, k)), 0, true);
      like.classList.toggle("is-on", ws.lt >= likeAt);
      heart.style.transform = ws.lt >= likeAt ? `scale(${(0.6 + 0.4 * spring(ws.lt - likeAt, { stiffness: 380, damping: 12 })).toFixed(3)})` : "";
    });
  };

  // Checklist: items [{text, at}] or strings; box ticks when `at` (absolute) is reached. strike, reveal
  C.checklist = function (el, root) {
    const e2 = Object.assign({ w: W * 0.84, in: "rise" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("check");
    if (el.strike) inner.classList.add("is-strike");
    if (el.title) h("div", "check-title", inner, el.html ? el.title : esc(el.title));
    const s0 = el.start || 0;
    const items = (el.items || []).map((it, i) => {
      const o = typeof it === "string" ? { text: it } : it;
      const row = h("div", "check-row", inner, '<svg viewBox="0 0 40 40" class="ck"><rect class="ck-box" x="3" y="3" width="34" height="34" rx="9"/><path class="ck-mark" d="M11 21 L17.5 27.5 L29.5 13.5"/></svg>');
      h("span", "check-text", row, esc(o.text));
      return { row, mark: row.querySelector(".ck-mark"), at: o.at != null ? o.at : s0 + 0.6 + i * (el.itemStagger || 0.7) };
    });
    return windowed(e2, outer, inner, t => items.forEach(I => {
      I.mark.style.strokeDashoffset = 30 * (1 - E.out(clamp((t - I.at) / 0.3)));
      I.row.classList.toggle("is-done", t >= I.at);
      if (el.reveal) applyAnim(I.row, animState("slideLeft", clamp((t - I.at + 0.5) / 0.35), "in"));
    }));
  };

  // Numbered progress stepper: steps ["A","B"] or [{label, at}], vertical
  C.steps = function (el, root) {
    const e2 = Object.assign({ w: W * 0.9, in: "rise" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("steps", el.vertical ? "is-v" : "is-h");
    const list = (el.steps || []).map(s => typeof s === "string" ? { label: s } : s), n = list.length || 1;
    inner.style.setProperty("--n", n);
    const s0 = el.start || 0, ats = list.map((s, i) => s.at != null ? s.at : s0 + 0.4 + i * (el.stepStagger || 0.9));
    const track = h("div", "st-track", inner), fill = h("div", "st-fill", track);
    const nodes = list.map((s, i) => { const nd = h("div", "st-node", inner); const dot = h("div", "st-dot", nd, String(i + 1)); h("div", "st-label", nd, esc(s.label)); return { nd, dot, state: "" }; });
    return windowed(e2, outer, inner, t => {
      let prog = 0;
      for (let i = 1; i < n; i++) prog += clamp((t - (ats[i] - 0.35)) / 0.35);
      fill.style.transform = el.vertical ? `scaleY(${prog / Math.max(1, n - 1)})` : `scaleX(${prog / Math.max(1, n - 1)})`;
      nodes.forEach((N, i) => {
        const st = t >= (ats[i + 1] != null ? ats[i + 1] : 1e9) ? "done" : t >= ats[i] ? "active" : "todo";
        if (st !== N.state) { N.nd.className = "st-node is-" + st; N.dot.textContent = st === "done" ? "✓" : String(i + 1); N.state = st; }
        const dt = t - ats[i];
        N.dot.style.transform = dt >= 0 && dt < 0.5 ? `scale(${1 + 0.22 * Math.sin(dt / 0.5 * Math.PI)})` : "";
      });
    });
  };

  // Quote: big quote mark + word reveal + attribution (author, role)
  C.quote = function (el, root) {
    const e2 = Object.assign({ w: W * 0.86, in: "fade" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("quote");
    const mark = h("div", "q-mark", inner, "“");
    const body = h("div", "q-text", inner);
    const words = String(el.text || "").split(/\s+/).filter(Boolean).map(w => { const u = h("span", "unit", body, esc(w)); body.appendChild(document.createTextNode(" ")); return u; });
    const rule = h("div", "q-rule", inner);
    const by = el.author ? h("div", "q-by", inner, `<b>${esc(el.author)}</b>${el.role ? `<span>${esc(el.role)}</span>` : ""}`) : null;
    const stg = el.stagger != null ? el.stagger : 0.05, U = animSpec(el.unitIn || "rise", el.unitDur || null, 0.35, el.unitEase);
    const done = 0.3 + words.length * stg + U.dur;
    return windowed(e2, outer, inner, (t, ws) => {
      applyAnim(mark, animState("springPop", clamp(ws.lt / 0.6), "in", { dur: 0.6 }));
      words.forEach((u, i) => applyAnim(u, animState(U.name, clamp((ws.lt - 0.3 - i * stg) / U.dur), "in", U)));
      rule.style.transform = `scaleX(${E.expoOut(clamp((ws.lt - done) / 0.5))})`;
      if (by) applyAnim(by, animState("rise", clamp((ws.lt - done - 0.1) / 0.4), "in"));
    });
  };

  // Split layout: panes [{image | clip, label, clipOffset}] (2-4), layout "h" | "v" | "grid", paneIn
  C.split = function (el, root) {
    const e2 = Object.assign({ w: W * 0.92, h: H * 0.62, in: "none" }, el);
    const { outer, inner } = base(e2, root); inner.classList.add("split");
    const panes = (el.panes || []).slice(0, 4), n = panes.length;
    inner.classList.add("split-" + (el.layout || (n === 4 ? "grid" : PORTRAIT ? "v" : "h")));
    const ps = panes.map(p => {
      const node = h("div", "sp-pane", inner);
      let player = null;
      if (p.clip) player = clipPlayer(p.clip, p.clipOffset || 0, node, "sp-media");
      else if (p.image) { const im = h("img", "sp-media", node); im.src = assetUrl(p.image); }
      else node.classList.add("is-empty");
      if (p.label) h("div", "sp-label", node, esc(p.label));
      return { node, player };
    });
    const PS = animSpec(el.paneIn || "maskUp", el.paneDur || null, 0.6, el.paneEase), stg = el.stagger != null ? el.stagger : 0.15;
    return windowed(e2, outer, inner, async (t, ws) => {
      for (let i = 0; i < ps.length; i++) {
        applyAnim(ps[i].node, animState(PS.name, clamp((ws.lt - i * stg) / PS.dur), "in", PS));
        if (ps[i].player) await ps[i].player.seek(ws.lt);
      }
    });
  };

  // Full-frame overlays: vignette, letterbox, grain, lightleak
  C.vignette = function (el, root) {
    const e2 = fullFrame(el);
    const { outer, inner } = base(e2, root);
    const c = el.color || "0,0,0", s = el.strength != null ? el.strength : 0.6, size = el.size != null ? el.size : 0.5;
    inner.style.background = `radial-gradient(ellipse at 50% ${el.cy != null ? el.cy : 50}%, rgba(${c},0) ${size * 100}%, rgba(${c},${s}) 100%)`;
    return windowed(e2, outer, inner);
  };
  C.letterbox = function (el, root) {
    const e2 = fullFrame(el, { in: "none", out: "none", inDur: el.inDur != null ? el.inDur : 0.6, outDur: el.outDur != null ? el.outDur : 0.5 });
    const { outer, inner } = base(e2, root);
    const bar = el.bar != null ? el.bar : el.ratio ? Math.max(0, (H - W / el.ratio) / 2) : PORTRAIT ? H * 0.08 : Math.max(0, (H - W / 2.39) / 2);
    const top = h("div", "lb-bar lb-top", inner), bot = h("div", "lb-bar lb-bot", inner);
    [top, bot].forEach(b => { b.style.height = bar + "px"; if (el.color) b.style.background = el.color; });
    return windowed(e2, outer, inner, (t, ws) => {
      const k = Math.min(E.expoOut(ws.kin), E.expoOut(ws.kout));
      top.style.transform = `translateY(${-(1 - k) * 100}%)`; bot.style.transform = `translateY(${(1 - k) * 100}%)`;
    });
  };
  // grain: seeded per-frame noise canvas. amount = max alpha, scale = downsample factor, fps = grain rate
  C.grain = function (el, root) {
    const e2 = fullFrame(el);
    const { outer, inner } = base(e2, root); inner.classList.add("grain");
    const sc = el.scale || 2, cw = Math.ceil(W / sc), ch = Math.ceil(H / sc);
    const cv = h("canvas", "", inner); cv.width = cw; cv.height = ch;
    const ctx = cv.getContext("2d"), img = ctx.createImageData(cw, ch), d = img.data;
    const amount = el.amount != null ? el.amount : 0.16, seed = el.seed || 1;
    let lastF = null;
    return windowed(e2, outer, inner, t => {
      const f = Math.floor(t * (el.fps || FPS) + 1e-6);
      if (f === lastF) return;
      lastF = f;
      const rng = prng(hashInt(f * 7919 + seed));
      for (let i = 0, o = 0; i < cw * ch; i++, o += 4) {
        const r = rng(), v = r < 0.5 ? 0 : 255, a = Math.abs(r - 0.5) * 2;
        d[o] = d[o + 1] = d[o + 2] = v; d[o + 3] = a * a * 255 * amount;
      }
      ctx.putImageData(img, 0, 0);
    });
  };
  // lightleak: drifting warm radial glows (seeded value noise). intensity, colors ["r,g,b"], speed, count
  C.lightleak = function (el, root) {
    const e2 = fullFrame(el, { in: el.in || "fade", inDur: el.inDur != null ? el.inDur : 0.6 });
    const { outer, inner } = base(e2, root);
    const n = el.count || 3, seed = el.seed || 3, sp = el.speed || 0.25, I = el.intensity != null ? el.intensity : 0.55;
    const cols = el.colors || ["255,120,40", "255,190,90", "255,70,100"];
    return windowed(e2, outer, inner, (t, ws) => {
      const g = [];
      for (let i = 0; i < n; i++) {
        const x = 50 + 65 * noise2(ws.lt * sp, i * 3.1, seed), y = 50 + 65 * noise2(ws.lt * sp + 11, i * 5.7, seed);
        const r = 45 + 20 * noise2(ws.lt * sp * 0.7, i * 9.3 + 2, seed), a = I * (0.55 + 0.45 * noise2(ws.lt * sp * 1.3, i * 2.2 + 7, seed));
        const c = cols[i % cols.length];
        g.push(`radial-gradient(circle at ${x.toFixed(1)}% ${y.toFixed(1)}%, rgba(${c},${a.toFixed(3)}) 0%, rgba(${c},0) ${r.toFixed(1)}%)`);
      }
      inner.style.background = g.join(",");
    });
  };

  // ---------- transition overlays at a cut ----------
  // kind: wipe | iris | shape-mask | ink-blot | paper-tear | glitch | whip-blur | light-leak |
  //       flash-white | film-burn | zoom-blur. Window [at - dur/2, at + dur/2]; frame fully covered at `at`.
  const TR_COLOR = { wipe: "var(--c-accent)", iris: "#000", "shape-mask": "var(--c-accent)", "ink-blot": "#0d0d10", "paper-tear": "#f1ebdf" };
  function shapePts(kind, R, rot) {
    const n = kind === "diamond" ? 4 : kind === "hex" ? 6 : kind === "circle" ? 48 : 10, pts = [];
    for (let i = 0; i < n; i++) {
      const a = -Math.PI / 2 + (rot || 0) + i * 2 * Math.PI / n, r = kind === "star" || !kind ? (i % 2 ? R * 0.45 : R) : R;
      pts.push([Math.cos(a) * r, Math.sin(a) * r]);
    }
    return pts;
  }
  // fraction of the outer radius that the shape fully covers (inscribed circle), used to size the cover
  const SHAPE_INNER = { star: 0.4, diamond: Math.SQRT1_2, hex: Math.cos(Math.PI / 6), circle: 0.99 };
  C.transition = function (el, root) {
    const kind = el.kind || "wipe", dur = el.dur || 0.4;
    const at = el.at != null ? el.at : el.start != null ? el.start + dur / 2 : 0, s = at - dur / 2, e = at + dur / 2;
    const outer = h("div", "el el-transition tr-" + kind + (el.className ? " " + el.className : ""), root);
    outer.style.inset = "0";
    const dir = el.dir || "left", seed = el.seed || (el._i || 0) * 13 + 1, color = el.color || TR_COLOR[kind] || "#fff";
    const D = Math.hypot(W, H) / 2;
    const ctr = el.center ? [el.center[0] * W, el.center[1] * H] : [W / 2, H / 2];
    const pane = h("div", "tr-pane", outer); pane.style.background = color; styleObj(pane, el.style);
    let back = null, slices = [], band = null, streaks = null;
    if (kind === "wipe") { back = h("div", "tr-pane tr-back", outer); back.style.background = el.color2 || "var(--c-accent2)"; outer.appendChild(pane); }
    if (kind === "paper-tear") outer.style.filter = "drop-shadow(0 0 22px rgba(0,0,0,.45))";
    if (kind === "glitch") { pane.style.background = "transparent"; for (let i = 0; i < 16; i++) slices.push(h("div", "tr-slice", outer)); }
    if (kind === "whip-blur") { pane.style.background = "#fff"; band = h("div", "tr-band", outer); streaks = h("div", "tr-streaks", outer); }
    const vert = dir === "up" || dir === "down";
    // covered interval [lo, hi] (0..1 across the travel axis) for a band whose cover/uncover progress is a/b
    const span = (a, b) => (dir === "left" || dir === "up") ? [1 - a, 1 - b] : [b, a];
    const insetFor = (lo, hi) => vert ? `inset(${(Math.min(lo, hi) * 100).toFixed(3)}% 0 ${((1 - Math.max(lo, hi)) * 100).toFixed(3)}% 0)` : `inset(0 ${((1 - Math.max(lo, hi)) * 100).toFixed(3)}% 0 ${(Math.min(lo, hi) * 100).toFixed(3)}%)`;
    const poly = (pts, cx, cy) => pts.map(p => `${(cx + p[0]).toFixed(1)}px ${(cy + p[1]).toFixed(1)}px`).join(",");
    const blob = (R, sd) => { const pts = []; for (let i = 0; i < 72; i++) { const a = i / 72 * Math.PI * 2, c = Math.cos(a), sn = Math.sin(a); const r = R * (1 + 0.26 * noise2(c * 1.6 + 5, sn * 1.6 + 5, sd) + 0.09 * noise2(c * 5 + 9, sn * 5 + 9, sd + 1)); pts.push([c * r, sn * r]); } return pts; };
    // hole phase: frame rect minus shape as two subpaths (a polygon() bridge would leave a seam)
    const subpath = (pts, cx, cy) => "M" + pts.map(q => `${(cx + q[0]).toFixed(1)} ${(cy + q[1]).toFixed(1)}`).join(" L") + " Z";
    const holed = (pts, cx, cy) => `path(evenodd, "M-10 -10 H${W + 10} V${H + 10} H-10 Z ${subpath(pts, cx, cy)}")`;
    // torn edge polyline across the frame at travel position x (px); jag amplitude 26px
    const torn = (pos, sd, rev) => {
      const n = 28, pts = [];
      for (let i = 0; i <= n; i++) { const u = i / n, j = (hash2(i, 0, sd) - 0.5) * 52 + (hash2(i, 1, sd) - 0.5) * 18; pts.push(vert ? [u * W, pos + j] : [pos + j, u * H]); }
      return rev ? pts.reverse() : pts;
    };
    return {
      layer: el.layer || "front",
      update(t) {
        if (t < s || t >= e) { outer.style.display = "none"; return false; }
        outer.style.display = "";
        const p = (t - s) / dur, a = clamp(p * 2), b = clamp(p * 2 - 1);
        switch (kind) {
          case "wipe": {
            const ez = E.expoInOut, lead = clamp((t - s) / dur + 0.07);
            const [l0, h0] = span(ez(clamp(lead * 2)), ez(clamp(lead * 2 - 1))), [l1, h1] = span(ez(a), ez(b));
            back.style.clipPath = insetFor(l0, h0); pane.style.clipPath = insetFor(l1, h1);
            break;
          }
          case "iris": {
            const r = p < 0.5 ? D * (1 - E.inOut(a)) : D * E.inOut(b);
            const m = `radial-gradient(circle at ${ctr[0]}px ${ctr[1]}px, transparent ${r.toFixed(1)}px, #000 ${(r + 1.5).toFixed(1)}px)`;
            pane.style.webkitMaskImage = m; pane.style.maskImage = m;
            break;
          }
          case "shape-mask": {
            const sh = el.shape || "star", Rf = D / (SHAPE_INNER[sh] || 0.45) * 1.08;
            const rot = p * 0.7;   // spin the shape itself, never the pane (that would expose frame corners)
            pane.style.clipPath = p < 0.5 ? `polygon(${poly(shapePts(sh, Rf * E.cubicIn(a) + 1, rot), ctr[0], ctr[1])})`
              : holed(shapePts(sh, Rf * E.cubicOut(b) + 1, rot), ctr[0], ctr[1]);
            break;
          }
          case "ink-blot": {
            const Rf = D / 0.62;
            pane.style.clipPath = p < 0.5 ? `polygon(${poly(blob(Rf * E.quadIn(a) + 1, seed), ctr[0], ctr[1])})`
              : holed(blob(Rf * E.quadOut(b) + 1, seed + 7), ctr[0], ctr[1]);
            break;
          }
          case "paper-tear": {
            const L = vert ? H : W, ez = E.inOut, [lo, hi] = span(ez(a), ez(b));
            const p0 = lerp(-60, L + 60, Math.min(lo, hi)), p1 = lerp(-60, L + 60, Math.max(lo, hi));
            const pts = torn(p0, seed, false).concat(torn(p1, seed + 3, true));
            pane.style.clipPath = `polygon(${pts.map(q => `${q[0].toFixed(1)}px ${q[1].toFixed(1)}px`).join(",")})`;
            break;
          }
          case "glitch": {
            const f = Math.floor(t * FPS), I = tri(p), cols = ["rgba(255,0,90,.6)", "rgba(0,255,230,.55)", "rgba(255,255,255,.45)", "rgba(40,40,255,.5)"];
            slices.forEach((sl, i) => {
              const on = hash2(i, f, seed) < 0.25 + 0.7 * I;
              sl.style.display = on ? "" : "none"; if (!on) return;
              sl.style.top = (hash2(i, f + 1, seed) * H).toFixed(0) + "px"; sl.style.height = ((0.01 + 0.07 * hash2(i, f + 2, seed)) * H).toFixed(0) + "px";
              sl.style.transform = `translateX(${((hash2(i, f + 3, seed) - 0.5) * 220 * I).toFixed(0)}px)`;
              sl.style.background = cols[hashInt(i * 31 + f) % cols.length];
            });
            pane.style.background = `rgba(${hash2(f, 9, seed) > .5 ? "255,0,80" : "0,220,255"},${(0.22 * I).toFixed(3)})`;
            break;
          }
          case "whip-blur": {
            const I = tri(p), k = E.inOut(p), x = lerp(-0.9, 1.1, (dir === "left" || dir === "up") ? 1 - k : k);
            pane.style.opacity = (0.55 * Math.pow(I, 1.5)).toFixed(3);
            band.style.transform = vert ? `translateY(${(x * H).toFixed(0)}px) rotate(90deg)` : `translateX(${(x * W).toFixed(0)}px)`;
            band.style.opacity = I.toFixed(3);
            streaks.style.opacity = (0.8 * I).toFixed(3);
            break;
          }
          case "light-leak": {
            const I = Math.pow(Math.sin(p * Math.PI), 1.2), x = lerp(15, 85, p), x2 = lerp(90, 30, p);
            pane.style.background = `radial-gradient(circle at ${x}% 35%, rgba(255,236,190,${(0.95 * I).toFixed(3)}) 0%, rgba(255,140,40,${(0.75 * I).toFixed(3)}) 28%, rgba(255,60,20,0) 62%), radial-gradient(circle at ${x2}% 75%, rgba(255,90,60,${(0.6 * I).toFixed(3)}) 0%, rgba(255,90,60,0) 55%)`;
            break;
          }
          case "flash-white": pane.style.opacity = ((el.peak != null ? el.peak : 1) * (p < 0.5 ? E.quadIn(a) : 1 - E.quadOut(b))).toFixed(3); break;
          case "film-burn": {
            const I = Math.pow(Math.sin(p * Math.PI), 0.9), ex = { left: [105, 50], right: [-5, 50], up: [50, 105], down: [50, -5] }[dir] || [105, 50];
            const r = 30 + 90 * E.quadOut(a);
            pane.style.background = `radial-gradient(circle at ${ex[0]}% ${ex[1]}%, rgba(255,250,225,${I.toFixed(3)}) 0%, rgba(255,190,80,${(0.95 * I).toFixed(3)}) ${(r * 0.35).toFixed(1)}%, rgba(230,80,10,${(0.85 * I).toFixed(3)}) ${(r * 0.6).toFixed(1)}%, rgba(120,20,0,${(0.5 * I).toFixed(3)}) ${(r * 0.85).toFixed(1)}%, rgba(0,0,0,0) ${r.toFixed(1)}%)`;
            break;
          }
          case "zoom-blur": {
            const I = tri(p);
            pane.style.background = `radial-gradient(circle at 50% 50%, rgba(255,255,255,${(0.9 * I).toFixed(3)}) 0%, rgba(255,255,255,0) 35%), repeating-radial-gradient(circle at 50% 50%, rgba(255,255,255,${(0.5 * I).toFixed(3)}) 0 10px, rgba(255,255,255,0) 10px 48px)`;
            pane.style.transform = `scale(${(0.6 + E.expoIn(p) * 2.6).toFixed(3)})`;
            pane.style.filter = `blur(${(3 + 9 * I).toFixed(1)}px)`;
            break;
          }
          default: pane.style.opacity = tri(p);
        }
        return true;
      }
    };
  };

  // =====================================================================
  // 7. build
  // =====================================================================
  const themeVars = P.theme && P.theme.vars;
  if (themeVars) styleObj(document.documentElement, themeVars);
  if (/[\u0900-\u097F]/.test(JSON.stringify(P))) document.documentElement.lang = "hi";   // base.css :lang(hi) rules for Devanagari
  document.documentElement.style.setProperty("--W", W + "px");
  document.documentElement.style.setProperty("--H", H + "px");
  const roots = {};
  ["bg", "behind", "front"].forEach(l => { roots[l] = h("div", "layer layer-" + l, document.getElementById("stage")); });
  const comps = [];
  (P.elements || []).forEach((el, i) => {
    el._i = i;
    const f = C[el.type];
    if (!f) { console.warn("unknown element type", el.type); return; }
    const layer = el.layer || (el.type === "shape" ? "behind" : el.type === "background" ? "bg" : "front");
    el.layer = layer;
    const c = f(el, roots[layer]);
    c.layer = layer;
    comps.push(c);
  });

  window.__layersUsed = ["bg", "behind", "front"].filter(l => comps.some(c => c.layer === l));
  window.__render = async function (t, layer) {
    Object.keys(roots).forEach(l => { roots[l].style.display = !layer || l === layer ? "" : "none"; });
    let any = false;
    for (const c of comps) {
      if (layer && c.layer !== layer) continue;
      const v = await c.update(t);
      any = any || v;
    }
    return any;
  };
  window.__ready = (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => true);
})();
