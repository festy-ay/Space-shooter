#version 330
// Procedural 2D space background with a style dial between realistic and cartoon.
//   toon = 0.0  soft, painterly and fairly realistic
//   toon = 1.0  flat colours, crisp edges, ink outlines (the cartoon version)
// The default sits in between. Change it with the `toon` uniform (the demo script has [ and ] keys).
// Everything is generated from `seed`, so each seed is a different but repeatable sky.
// `scroll` moves the camera (in screen heights). Layers move at different speeds (parallax).

in vec2 uv;
out vec4 fragColor;

uniform vec2  resolution;
uniform float time;
uniform int   seed;
uniform vec2  scroll;

uniform float toon           = 0.4;    // 0 = realistic-ish, 1 = full cartoon
uniform float nebula_amount  = 1.0;    // 0 = no nebula, 1 = normal, 2 = very cloudy
uniform float star_density   = 1.0;    // multiplies the number of small stars
uniform float bigstar_chance = 0.45;   // chance that a big-star cell contains a star (0..1)
uniform float planet_chance  = 0.55;   // chance that a planet cell contains a planet (0..1)

const vec3 OUTLINE = vec3(0.06, 0.03, 0.13);   // dark indigo ink for planet outlines

uint SEED;
float S;     // edge softness multiplier, set in main() from `toon`

// ------------------------------------------------------------------ random numbers
uint pcg(uint v) {
    uint s = v * 747796405u + 2891336653u;
    uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u;
    return (w >> 22u) ^ w;
}
float u01(uint h) { return float(h >> 8) * (1.0 / 16777216.0); }
float rnd(ivec2 c, uint salt)  { return u01(pcg(uint(c.x) + pcg(uint(c.y) + pcg(salt + SEED)))); }
float rnd3(ivec3 c, uint salt) { return u01(pcg(uint(c.x) + pcg(uint(c.y) + pcg(uint(c.z) + pcg(salt + SEED))))); }
float rnd1(uint salt)          { return u01(pcg(pcg(salt) ^ SEED)); }

// ------------------------------------------------------------------ noise
float vnoise(vec2 p, uint salt) {
    ivec2 i = ivec2(floor(p));
    vec2 fr = fract(p);
    vec2 u = fr * fr * (3.0 - 2.0 * fr);
    float a = rnd(i, salt);
    float b = rnd(i + ivec2(1, 0), salt);
    float c = rnd(i + ivec2(0, 1), salt);
    float d = rnd(i + ivec2(1, 1), salt);
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p, uint salt, int octaves) {
    float s = 0.0, a = 0.5;
    for (int i = 0; i < octaves; i++) {
        s += a * vnoise(p, salt + uint(i));
        p = mat2(1.6, 1.2, -1.2, 1.6) * p + 7.3;
        a *= 0.5;
    }
    return s;
}

float vnoise3(vec3 p, uint salt) {
    ivec3 i = ivec3(floor(p));
    vec3 fr = fract(p);
    vec3 u = fr * fr * (3.0 - 2.0 * fr);
    float a = rnd3(i, salt);
    float b = rnd3(i + ivec3(1, 0, 0), salt);
    float c = rnd3(i + ivec3(0, 1, 0), salt);
    float d = rnd3(i + ivec3(1, 1, 0), salt);
    float e = rnd3(i + ivec3(0, 0, 1), salt);
    float f = rnd3(i + ivec3(1, 0, 1), salt);
    float g = rnd3(i + ivec3(0, 1, 1), salt);
    float h = rnd3(i + ivec3(1, 1, 1), salt);
    return mix(mix(mix(a, b, u.x), mix(c, d, u.x), u.y),
               mix(mix(e, f, u.x), mix(g, h, u.x), u.y), u.z);
}

// Smooth blobs, plus a third layer of fine detail that fades in as `toon` goes down.
float fbm3s(vec3 p, uint salt) {
    float fine = 1.0 - toon;
    float s = 0.5 * vnoise3(p, salt) + 0.25 * vnoise3(p * 2.03 + 5.1, salt + 1u);
    s += fine * 0.125 * vnoise3(p * 4.1 + 11.7, salt + 2u);
    return s / (0.75 + fine * 0.125);
}

// ------------------------------------------------------------------ helpers
// Step from 0 to 1 at `e`. Its edge gets softer when `toon` is low.
float band(float x, float e, float w) {
    w *= S;
    return smoothstep(e - w, e + w, x);
}
// Same step, but always crisp (used for ring edges)
float crisp(float x, float e, float w) { return smoothstep(e - w, e + w, x); }

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

vec3 star_color(float t) {
    return t < 0.5  ? vec3(1.00, 1.00, 1.00) :
           t < 0.7  ? vec3(1.00, 0.92, 0.45) :
           t < 0.85 ? vec3(0.55, 0.90, 1.00) :
                      vec3(1.00, 0.60, 0.85);
}

// ------------------------------------------------------------------ nebula
vec3 nebula(vec2 P) {
    int pal = int(rnd1(1u) * 4.0);
    float hA, hB;
    if (pal == 0)      { hA = 0.62; hB = 0.50; }     // blue / cyan
    else if (pal == 1) { hA = 0.76; hB = 0.90; }     // purple / pink
    else if (pal == 2) { hA = 0.47; hB = 0.34; }     // teal / green
    else               { hA = 0.03; hB = 0.11; }     // red / orange
    hA += (rnd1(2u) - 0.5) * 0.05;
    hB += (rnd1(7u) - 0.5) * 0.05;

    vec3 base = hsv2rgb(vec3(hA, 0.85, 0.08));
    vec3 c1 = hsv2rgb(vec3(hA, 0.80, 0.20));
    vec3 c2 = hsv2rgb(vec3(mix(hA, hB, 0.5), 0.72, 0.33));
    vec3 c3 = hsv2rgb(vec3(hB, 0.62, 0.48));
    vec3 c4 = hsv2rgb(vec3(hB, 0.35, 0.75));

    float amount = mix(0.35, 1.3, rnd1(3u)) * nebula_amount;
    vec2 p = P * mix(1.0, 2.2, rnd1(4u)) + vec2(rnd1(5u), rnd1(6u)) * 100.0;

    vec2 q = vec2(fbm(p, 400u, 3), fbm(p + 5.2, 410u, 3));
    float f = fbm(p + 3.0 * q, 420u, 4);
    float mask = smoothstep(0.3, 0.7, fbm(p * 0.4 + 20.0, 430u, 3));
    float d = smoothstep(0.3, 0.85, f) * mask * amount;

    // wispy fine texture inside the clouds, stronger when `toon` is low
    float wisp = fbm(p * 3.0 + 60.0, 450u, 3);
    d += (1.0 - toon) * 0.25 * (wisp - 0.5) * smoothstep(0.02, 0.2, d);

    float w = 0.012;
    vec3 col = base;
    col = mix(col, c1, band(d, 0.10, w));
    col = mix(col, c2, band(d, 0.35, w));
    col = mix(col, c3, band(d, 0.62, w));
    col = mix(col, c4, band(d, 0.90, w));
    return col;
}

// ------------------------------------------------------------------ small stars
void star_layer(vec2 P, float cell, float chance, float size_px, uint salt, inout vec3 col) {
    vec2 g = P / cell;
    ivec2 id = ivec2(floor(g));
    vec2 fr = fract(g);
    if (rnd(id, salt) > chance) return;

    vec2 pos = vec2(0.3) + 0.4 * vec2(rnd(id, salt + 1u), rnd(id, salt + 2u));
    vec2 dv = (fr - pos) * cell;
    float px = 1.0 / resolution.y;
    float r = size_px * px * (0.55 + 0.45 * rnd(id, salt + 4u));

    float shape;
    if (rnd(id, salt + 3u) < mix(0.15, 0.40, toon)) {
        // 4-point sparkle that pulses in size
        r *= 1.5 * (0.8 + 0.2 * sin(time * (1.0 + 3.0 * rnd(id, salt + 5u)) + 6.2831 * rnd(id, salt + 6u)));
        float k = pow(abs(dv.x) / r, 0.6) + pow(abs(dv.y) / r, 0.6);
        float sw = 0.1 + 0.7 * (1.0 - toon);
        shape = 1.0 - smoothstep(1.0 - sw, 1.1, k);
    } else {
        float d = length(dv);
        float hard = 1.0 - smoothstep(r - px, r + px, d);
        float glow = exp(-(d * d) / (r * r * 1.6));
        shape = mix(glow, hard, toon);
    }
    vec3 sc = mix(star_color(rnd(id, salt + 7u)), vec3(1.0), 0.25 * (1.0 - toon));
    col = mix(col, sc, shape);
}

// ------------------------------------------------------------------ big stars: glowing orbs with rays
void big_stars(vec2 P, inout vec3 col) {
    const float CELL = 0.9;
    ivec2 id0 = ivec2(floor(P / CELL));
    float px = 1.0 / resolution.y;

    for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
            ivec2 id = id0 + ivec2(i, j);
            if (rnd(id, 100u) > bigstar_chance) continue;

            vec2 center = (vec2(id) + 0.1 + 0.8 * vec2(rnd(id, 101u), rnd(id, 102u))) * CELL;
            vec2 dv = P - center;
            float d = length(dv);
            float pulse = 1.0 + 0.05 * sin(time * (0.6 + rnd(id, 107u)) + 6.2831 * rnd(id, 108u));
            float size = mix(0.022, 0.055, pow(rnd(id, 103u), 1.5)) * pulse;
            if (d > size * 6.5) continue;

            float pick = rnd(id, 104u);
            vec3 tint = pick < 0.40 ? vec3(0.20, 0.65, 1.00) :
                        pick < 0.70 ? vec3(1.00, 0.60, 0.10) :
                        pick < 0.88 ? vec3(1.00, 0.35, 0.65) :
                                      vec3(0.45, 1.00, 0.55);
            vec3 light = mix(tint, vec3(1.0), 0.6);

            // rays
            int N = 8 + int(rnd(id, 105u) * 7.0);
            float turn = fract(atan(dv.y, dv.x) / 6.2831853 + rnd(id, 106u));
            float sec = turn * float(N);
            float idx = min(floor(sec), float(N - 1));
            float off = fract(sec) - 0.5;
            float len = size * mix(1.7, 4.4, rnd(id + ivec2(int(idx), 31), 110u));
            float ray = 0.0;
            if (d < len) {
                float w = 0.38 * (1.0 - d / len);
                float rw = 0.10 + 0.25 * (1.0 - toon);                 // softer ray edges when realistic
                ray = 1.0 - smoothstep(w - rw, w, abs(off));
            }
            col = mix(col, light, ray * mix(0.55, 0.85, toon));

            // halo: soft glow when realistic, flat disc when cartoon
            float halo_soft = exp(-d / (size * 1.4)) * 0.55;
            float halo_flat = (1.0 - smoothstep(size * 1.55, size * 1.7, d)) * 0.35;
            col = mix(col, tint, mix(halo_soft, halo_flat, toon));

            // orb: rim, body, white core
            float edge = px * 1.2 + size * 0.22 * (1.0 - toon);
            col = mix(col, light, 1.0 - smoothstep(size - edge, size + edge, d));
            col = mix(col, mix(tint, light, 0.45 * (1.0 - toon)), 1.0 - smoothstep(size * 0.78 - edge, size * 0.78 + edge, d));
            col = mix(col, vec3(1.0), 1.0 - smoothstep(size * 0.45 - edge, size * 0.45 + edge, d));
        }
    }
}

// ------------------------------------------------------------------ planets
vec3 planet_surface(vec3 q, int type, ivec2 id, out float emis, out float gloss) {
    emis = 0.0; gloss = 0.0;
    float off = 20.0 * rnd(id, 250u);
    float v1 = rnd(id, 251u), v2 = rnd(id, 252u), v3 = rnd(id, 253u);
    vec3 col;

    if (type == 0) {                                   // rocky / desert
        vec3 base = hsv2rgb(vec3(0.03 + 0.12 * v1, 0.55 + 0.25 * v2, 0.90));
        col = base;
        col = mix(col, base * vec3(0.78, 0.62, 0.62), band(fbm3s(q * 2.5 + off, 300u), 0.55, 0.015));
        col = mix(col, base * 0.55, band(fbm3s(q * 7.0 + off, 310u), 0.68, 0.015));      // craters
    } else if (type == 1) {                            // ocean world
        float h = fbm3s(q * 2.4 + off, 330u);
        float sea = 0.42 + 0.14 * v1;
        float lh = v3 < 0.6 ? 0.30 : (v3 < 0.8 ? 0.78 : 0.08);
        vec3 deep = hsv2rgb(vec3(0.58 + 0.06 * v2, 0.85, 0.85));
        vec3 shallow = hsv2rgb(vec3(0.52 + 0.05 * v2, 0.65, 0.98));
        vec3 sand = vec3(0.98, 0.85, 0.50);
        vec3 land1 = hsv2rgb(vec3(lh, 0.65, 0.85));
        vec3 land2 = hsv2rgb(vec3(lh, 0.70, 0.60));
        col = deep;
        col = mix(col, shallow, band(h, sea - 0.07, 0.012));
        col = mix(col, sand, band(h, sea, 0.012));
        col = mix(col, land1, band(h, sea + 0.04, 0.012));
        col = mix(col, land2, band(h, sea + 0.17, 0.012));
        gloss = 1.0 - band(h, sea, 0.012);
        float pol = band(abs(q.y) + (fbm3s(q * 5.0, 340u) - 0.5) * 0.25, 0.82, 0.015);
        col = mix(col, vec3(0.95, 0.98, 1.0), pol);
        float cloud = band(fbm3s(q * 3.0 + vec3(time * 0.015, 0.0, 0.0), 350u), 0.64, 0.015);
        col = mix(col, vec3(1.0), cloud);
        gloss *= (1.0 - pol) * (1.0 - cloud);
    } else if (type == 2) {                            // gas giant
        float hueG = v3 > 0.65 ? 0.55 + 0.1 * v1 : 0.04 + 0.1 * v1;
        float warp = fbm3s(q * vec3(1.5, 3.0, 1.5) + 3.0, 360u);
        float lat = q.y + (warp - 0.5) * 0.3;
        float s = sin(lat * (7.0 + 8.0 * v2) + 5.0 * warp);
        vec3 a = hsv2rgb(vec3(hueG, 0.45 + 0.2 * v2, 1.0));
        vec3 b = hsv2rgb(vec3(hueG + 0.04, 0.75, 0.90));
        vec3 c = hsv2rgb(vec3(hueG + 0.08, 0.35, 1.0));
        col = mix(a, b, band(s, 0.0, 0.06));
        col = mix(col, c, band(s, 0.82, 0.05));
        vec3 spot_dir = normalize(vec3(0.6, -0.3 + 0.5 * v1, 0.75));
        col = mix(col, hsv2rgb(vec3(hueG + 0.02, 0.8, 0.75)), band(dot(q, spot_dir), 0.94, 0.01));
        col = mix(col, a, band(dot(q, spot_dir), 0.975, 0.008));
        gloss = 0.4;
    } else if (type == 3) {                            // lava world
        float h = fbm3s(q * 3.0 + off, 380u);
        vec3 rock = vec3(0.32, 0.16, 0.10);
        vec3 rock_l = vec3(0.50, 0.27, 0.16);
        col = mix(rock, rock_l, band(h, 0.55, 0.02));
        float cr = fbm3s(q * 4.0 + off, 390u);
        float crack = 1.0 - band(abs(cr - 0.5), 0.045, 0.012);
        float core = 1.0 - band(abs(cr - 0.5), 0.018, 0.008);
        float pool = band(h, 0.74, 0.015);
        col = mix(col, vec3(1.0, 0.45, 0.05), max(crack, pool));
        col = mix(col, vec3(1.0, 0.88, 0.30), core);
        emis = max(crack, pool);
    } else {                                           // ice world
        float h = fbm3s(q * 3.0 + off, 395u);
        col = mix(vec3(0.45, 0.75, 1.0), vec3(0.80, 0.95, 1.0), band(h, 0.5, 0.015));
        col = mix(col, vec3(0.25, 0.50, 0.90), band(fbm3s(q * 6.0 + off, 397u), 0.68, 0.015));
        float cr = fbm3s(q * 5.0 + off * 0.5, 399u);
        col = mix(col, vec3(1.0), 1.0 - band(abs(cr - 0.5), 0.02, 0.008));
        gloss = 0.8;
    }
    return col;
}

vec3 atmosphere(int type, ivec2 id) {
    if (type == 1) return vec3(0.45, 0.75, 1.00);
    if (type == 2) return hsv2rgb(vec3(0.05 + 0.15 * rnd(id, 251u), 0.4, 1.0));
    return vec3(0.65, 0.85, 1.00);
}

void planets(vec2 P, inout vec3 col) {
    const float CELL = 1.9;
    ivec2 id = ivec2(floor(P / CELL));
    if (rnd(id, 200u) > planet_chance) return;

    int type = int(rnd(id, 204u) * 5.0);
    float r = mix(0.07, 0.25, pow(rnd(id, 201u), 1.3)) * (type == 2 ? 1.3 : 1.0);
    bool has_ring = rnd(id, 205u) < (type == 2 ? 0.55 : 0.18);
    bool has_atmo = (type == 1 || type == 2 || type == 4);
    float margin = r * (has_ring ? 2.05 : 1.45) / CELL;
    vec2 center = (vec2(id) + margin + (1.0 - 2.0 * margin) * vec2(rnd(id, 202u), rnd(id, 203u))) * CELL;

    vec2 x = (P - center) / r;
    float dist = length(x);
    if (dist > (has_ring ? 2.05 : 1.45)) return;

    float aa = 1.5 / (resolution.y * r);
    float ow = toon * 3.0 / (resolution.y * r);                // outline thickness: 0 to 3 pixels
    float la = 6.2831853 * rnd(id, 206u);
    vec3 L = normalize(vec3(cos(la) * 0.85, sin(la) * 0.85, 0.5));
    vec2 L2 = L.xy / length(L.xy);
    vec2 dir = x / max(dist, 1e-4);

    // ----- ring
    float ring_a = 0.0;
    vec3 ring_c = vec3(0.0);
    float ring_side = 0.0;
    if (has_ring) {
        float ra = 6.2831853 * rnd(id, 260u);
        vec2 qr = mat2(cos(ra), sin(ra), -sin(ra), cos(ra)) * x;
        float open_amt = mix(0.16, 0.42, rnd(id, 261u));
        float rr = length(vec2(qr.x, qr.y / open_amt));
        float u = (rr - 1.35) / 0.65;
        float inner = crisp(u, 0.0, 0.02) * (1.0 - crisp(u, 1.0, 0.02));
        float uc = clamp(u, 0.0, 0.999);
        float seg = floor(uc * 5.0);
        float sr = rnd(id + ivec2(int(seg), 5), 270u);
        vec3 tint = hsv2rgb(vec3(0.04 + 0.12 * rnd(id, 263u) + (type == 4 ? 0.5 : 0.0), 0.45, 0.95));
        vec3 seg_c = sr < 0.55 ? tint * vec3(0.78, 0.70, 0.90) : tint;
        float fu = fract(uc * 5.0);
        float line = 1.0 - crisp(min(fu, 1.0 - fu), 0.10, 0.03);
        float edge = 1.0 - crisp(min(u, 1.0 - u), 0.06, 0.02);
        ring_c = mix(seg_c, OUTLINE, max(line, edge) * toon);            // ink lines fade out when realistic
        ring_c *= mix(0.45, 1.0, smoothstep(-0.5, 0.5, dot(dir, L2)));  // darker on the unlit side
        ring_a = inner * (sr < 0.15 ? 0.0 : 1.0) * mix(0.8, 1.0, toon);
        ring_side = qr.y;
    }
    if (has_ring && ring_side <= 0.0) col = mix(col, ring_c, ring_a);

    // ----- atmosphere glow outside the planet: soft when realistic, a flat band when cartoon
    if (has_atmo && dist >= 1.0) {
        float gw = 7.0 / (resolution.y * r);
        float flat_band = 1.0 - smoothstep(1.0 + ow + gw - aa, 1.0 + ow + gw + aa, dist);
        float soft_glow = exp(-(dist - 1.0) * 12.0) * (1.0 - smoothstep(1.1, 1.45, dist));
        float glow = mix(soft_glow * 0.9, flat_band * 0.45, toon);
        float side = smoothstep(-0.5, 0.4, dot(dir, L2));
        col = mix(col, atmosphere(type, id), glow * side);
    }

    // ----- thin outline, then the planet itself
    float outer = 1.0 - smoothstep(1.0 + ow - aa, 1.0 + ow + aa, dist);
    col = mix(col, OUTLINE, outer);

    float cover = 1.0 - smoothstep(1.0 - aa, 1.0 + aa, dist);
    if (cover > 0.0) {
        float z = sqrt(max(1.0 - dot(x, x), 0.0));
        vec3 n = vec3(x, z);
        float a = time * (rnd(id, 207u) - 0.5) * 0.12 + 6.2831853 * rnd(id, 208u);
        vec3 q = vec3(cos(a) * n.x + sin(a) * n.z, n.y, -sin(a) * n.x + cos(a) * n.z);
        float tilt = (rnd(id, 209u) - 0.5) * 0.9;
        q.xy = mat2(cos(tilt), sin(tilt), -sin(tilt), cos(tilt)) * q.xy;

        float emis, gloss;
        vec3 surf = planet_surface(q, type, id, emis, gloss);
        float lum = dot(surf, vec3(0.299, 0.587, 0.114));
        surf = mix(vec3(lum), surf, mix(0.8, 1.0, toon));                // slightly less saturated when realistic

        // lighting: terminator softness and shadow colour depend on `toon`
        float ndl = dot(n, L);
        float tw = mix(0.40, 0.02, toon);
        vec3 shadow = surf * mix(vec3(0.10, 0.11, 0.20), vec3(0.42, 0.38, 0.72), toon);
        vec3 c = mix(shadow, surf, smoothstep(0.12 - tw, 0.12 + tw, ndl));
        c = mix(c, min(surf * 1.12 + 0.06, vec3(1.0)), smoothstep(0.60 - tw, 0.60 + tw, ndl));
        if (has_atmo) {
            float rim = band(1.0 - z, 0.70, 0.03) * band(ndl, 0.0, 0.1);
            c = mix(c, mix(atmosphere(type, id), vec3(1.0), 0.3), rim * mix(0.4, 0.6, toon));
        }
        float spec = band(dot(n, normalize(L + vec3(0.0, 0.0, 1.0))), 0.97, 0.006) * gloss;
        c = mix(c, vec3(1.0), spec * mix(0.4, 0.85, toon));
        c = mix(c, surf, emis);
        col = mix(col, c, cover);
    }

    if (has_ring && ring_side > 0.0) col = mix(col, ring_c, ring_a);
}

// ------------------------------------------------------------------ main
void main() {
    SEED = uint(seed);
    S = mix(6.0, 1.0, toon);
    vec2 p = (gl_FragCoord.xy - 0.5 * resolution) / resolution.y;

    vec3 col = nebula(p + scroll * 0.10);

    star_layer(p + scroll * 0.05,       0.050, 0.20 * star_density,  5.0, 500u, col);
    star_layer(p + scroll * 0.12 + 3.1, 0.075, 0.25 * star_density,  7.0, 520u, col);
    star_layer(p + scroll * 0.25 + 7.7, 0.110, 0.30 * star_density, 10.0, 540u, col);
    big_stars(p + scroll * 0.35, col);

    planets(p + scroll * 0.6, col);

    col += (rnd(ivec2(gl_FragCoord.xy), 999u) - 0.5) / 255.0;       // dither, hides banding in smooth gradients
    fragColor = vec4(col, 1.0);
}
