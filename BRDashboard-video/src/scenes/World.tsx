// The motion-graphics layer: one paper world (a wall of lot tiles in the app's
// own palette) that the camera travels through. The opening pushes into the
// WK-008 tile and lands on the filmed Morning screen; the ending pulls back out
// of the footage, shows where the evidence lives, and settles on the tagline.
// Both read absolute video time, like parts/Screen.tsx, so they sit outside any
// <Sequence>. Headline times are narration word times inside each beat.
import React from 'react';
import { AbsoluteFill, Easing, interpolate, random, useCurrentFrame } from 'remotion';
import { FPS, W, H, at, endOf, BRAND, TAGLINE, CARDS_CONFIG } from '../timeline';
import { C, FONT } from '../theme';

const MISS: string = (C as Record<string, string>).miss;
const clampOpts = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
const ramp = (t: number, from: number, to: number, a = 0, b = 1, easing?: (n: number) => number) =>
  interpolate(t, [from, to], [a, b], { ...clampOpts, easing });

// --- the wall --------------------------------------------------------------
const COLS = 10;
const ROWS = 7;
const TILE_W = 250;
const TILE_H = 140;
const GAP = 22;
const WALL_W = COLS * TILE_W + (COLS - 1) * GAP;
const WALL_H = ROWS * TILE_H + (ROWS - 1) * GAP;
const YARDS = ['PN', 'HS', 'WK', 'PC'];
const CHOSEN = 35; // row 3, col 5: just right of centre
const lotId = (i: number) => `${YARDS[i % 4]}-${String(Math.floor(i / 4) + 1).padStart(3, '0')}`;
const WK008 = 30; // where WK-008 falls in the plain sequence; swapped into CHOSEN
const idAt = (i: number) => (i === CHOSEN ? lotId(WK008) : i === WK008 ? lotId(CHOSEN) : lotId(i));
const CHOSEN_X = (CHOSEN % COLS) * (TILE_W + GAP) + TILE_W / 2;
const CHOSEN_Y = Math.floor(CHOSEN / COLS) * (TILE_H + GAP) + TILE_H / 2;

/** miss: share of tiles marked red (0-1). thin: share with records missing. lit: the WK-008 tile is the destination. */
const Wall: React.FC<{ miss?: number; thin?: number; lit?: number }> = ({ miss = 0, thin = 0, lit = 0 }) => (
  <div style={{ position: 'relative', width: WALL_W, height: WALL_H }}>
    {Array.from({ length: COLS * ROWS }).map((_, i) => {
      const chosen = i === CHOSEN;
      const isMiss = !chosen && random(`m${i}`) < miss;
      const isThin = !chosen && !isMiss && random(`r${i}`) < thin;
      const ink = chosen && lit > 0 ? C.accent3 : isMiss ? MISS : C.text;
      return (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: (i % COLS) * (TILE_W + GAP),
            top: Math.floor(i / COLS) * (TILE_H + GAP),
            width: TILE_W,
            height: TILE_H,
            boxSizing: 'border-box',
            padding: '18px 20px',
            borderRadius: chosen ? 12 : 0,
            background: chosen ? C.card : isMiss ? `color-mix(in oklch, ${MISS} 9%, ${C.bg})` : C.bg,
            border: `${chosen ? 2 + lit * 2 : 1.5}px ${isThin ? 'dashed' : 'solid'} ${chosen && lit > 0 ? C.accent3 : C.line}`,
            boxShadow: chosen ? `0 ${10 * lit}px ${40 * lit}px oklch(20% 0.02 255 / ${0.18 * lit})` : 'none',
          }}
        >
          <div style={{ fontFamily: FONT.mono, fontWeight: 500, fontSize: 30, lineHeight: 1, color: ink, opacity: chosen ? 1 : 0.62 }}>{idAt(i)}</div>
          <div style={{ height: 8, width: `${48 + random(`a${i}`) * 44}%`, background: isMiss ? MISS : C.text, opacity: isThin ? 0 : 0.3, marginTop: 24 }} />
          <div style={{ height: 8, width: `${30 + random(`b${i}`) * 40}%`, background: C.text, opacity: isThin ? 0 : 0.16, marginTop: 12 }} />
        </div>
      );
    })}
  </div>
);

const Paper: React.FC<{ drift: number; children: React.ReactNode; opacity?: number }> = ({ drift, children, opacity = 1 }) => (
  <AbsoluteFill
    style={{
      opacity,
      backgroundColor: C.bg,
      backgroundImage: `radial-gradient(oklch(20% 0.02 255 / 0.13) 1.2px, transparent 1.4px)`,
      backgroundSize: '22px 22px',
      backgroundPosition: `${-drift * 0.4}px ${-drift * 0.25}px`,
      overflow: 'hidden',
    }}
  >
    {children}
  </AbsoluteFill>
);

/** The wall with the camera aimed at the WK-008 tile: `s` scales about that tile, which sits at (cx, cy) on the stage. */
const WallCam: React.FC<{ s: number; cx: number; cy: number; drift: number; children: React.ReactNode }> = ({ s, cx, cy, drift, children }) => (
  <div
    style={{
      position: 'absolute',
      left: cx - CHOSEN_X + drift,
      top: cy - CHOSEN_Y,
      transformOrigin: `${CHOSEN_X}px ${CHOSEN_Y}px`,
      transform: `scale(${s}) rotate(-2deg)`,
    }}
  >
    {children}
  </div>
);

const Veil: React.FC<{ opacity: number }> = ({ opacity }) => (
  <AbsoluteFill style={{ opacity, background: `radial-gradient(ellipse 62% 56% at 50% 50%, ${C.bg} 0%, ${C.bg} 52%, transparent 100%)` }} />
);

// --- kinetic type ----------------------------------------------------------
type Line = { text: string; from: number; to: number; size: number; split?: boolean };

/** Word slam (scale 1.15 -> 1, 120ms, ease-out) or split-text reveal (words 40ms apart, 24px rise, 200ms). Exits upward in 200ms. */
const Headline: React.FC<{ t: number; line: Line; color?: string }> = ({ t, line, color = C.text }) => {
  if (t < line.from || t > line.to) return null;
  const out = ramp(t, line.to - 0.2, line.to);
  const slam = ramp(t, line.from, line.from + 0.12, 0, 1, Easing.out(Easing.cubic));
  const words = line.text.split(' ');
  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', padding: '0 160px' }}>
      <div
        style={{
          fontFamily: FONT.sans, fontWeight: 600, fontSize: line.size, lineHeight: 1.04, letterSpacing: '-0.03em',
          color, textAlign: 'center', maxWidth: 1500,
          opacity: (line.split ? 1 : slam) * (1 - out),
          transform: `translateY(${-28 * out}px) scale(${line.split ? 1 : 1.15 - 0.15 * slam})`,
        }}
      >
        {line.split
          ? words.map((w, i) => {
              const a = ramp(t, line.from + i * 0.04, line.from + i * 0.04 + 0.2, 0, 1, Easing.out(Easing.cubic));
              return (
                <span key={i} style={{ display: 'inline-block', marginRight: '0.26em', opacity: a, transform: `translateY(${(1 - a) * 24}px)` }}>{w}</span>
              );
            })
          : line.text}
      </div>
    </AbsoluteFill>
  );
};

// --- opening: hook + problem, then the push into WK-008 ---------------------
export const Opening: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  const t0 = at('hook');
  const end = endOf('problem');
  if (t > end + 0.5) return null;
  const a = t - t0; // narration time

  const lines: Line[] = [
    { text: 'Bovine respiratory disease costs feedlots millions.', from: 0.84, to: 4.3, size: 104, split: true },
    { text: 'In treatment.', from: 4.36, to: 5.3, size: 150 },
    { text: 'In lost performance.', from: 5.36, to: 7.1, size: 150 },
    { text: 'In cattle that never make it.', from: 7.16, to: 8.95, size: 128 },
    { text: 'The people making the calls', from: 9.1, to: 10.9, size: 104, split: true },
    { text: 'Incomplete records.', from: 11.0, to: 12.3, size: 150 },
    { text: 'Not enough hours.', from: 12.36, to: 13.75, size: 150 },
  ];
  const miss = a < 4.36 ? 0 : a < 5.36 ? 0.14 : a < 7.16 ? 0.28 : 0.42;
  const thin = a < 11.0 ? 0 : 0.5;
  const pushFrom = end - 0.75;
  const push = ramp(t, pushFrom, end + 0.45, 0, 1, Easing.in(Easing.cubic));
  const s = interpolate(t, [0, pushFrom], [0.94, 1.12], clampOpts) + push * 9;
  const lit = ramp(t, pushFrom - 0.5, pushFrom);

  return (
    <Paper drift={t * 14} opacity={1 - ramp(t, end - 0.05, end + 0.45)}>
      <WallCam s={s} cx={W * 0.56 - push * W * 0.06} cy={H / 2} drift={-t * 9}>
        <Wall miss={miss} thin={thin} lit={lit} />
      </WallCam>
      <Veil opacity={1 - ramp(t, pushFrom - 0.6, pushFrom)} />
      {lines.map((line) => (
        <Headline key={line.text} t={a} line={line} color={line.text.startsWith('In ') ? MISS : C.text} />
      ))}
    </Paper>
  );
};

// --- ending: where the evidence lives, then the tagline ---------------------
type Sheet = { title: string; path: string };

export const Ending: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  const t0 = at('docs');
  const closeAt = at('close');
  if (t < t0 - 0.3) return null;
  const a = t - t0;
  const c = t - closeAt;
  const sheets: Sheet[] = CARDS_CONFIG.docs?.sheets ?? [];
  const stack: string = CARDS_CONFIG.docs?.stack ?? '';

  // Pull back out of the footage, then glide down one screen to the close.
  const pull = ramp(t, t0 - 0.1, t0 + 0.9, 0, 1, Easing.out(Easing.cubic));
  const glide = ramp(t, closeAt - 0.45, closeAt + 0.55, 0, 1, Easing.inOut(Easing.cubic));
  const words: Line[] = [
    { text: 'The evidence.', from: 0.5, to: 1.35, size: 150 },
    { text: 'The methods.', from: 1.4, to: 2.25, size: 150 },
    { text: 'Every number.', from: 2.3, to: 3.0, size: 150 },
  ];
  const sheetIn = [3.04, 4.38];
  const stackIn = ramp(a, 5.3, 5.6, 0, 1, Easing.out(Easing.cubic));
  const mark = ramp(c, 0.3, 0.42, 0, 1, Easing.out(Easing.cubic));
  const rule = ramp(c, 0.5, 1.5, 0, 1, Easing.inOut(Easing.cubic));
  const tagFrom = 1.8;

  return (
    <Paper drift={t * 14 + glide * 300} opacity={ramp(t, t0 - 0.1, t0 + 0.4)}>
      <WallCam s={2.4 - pull * 1.42 - glide * 0.06} cx={W * 0.5} cy={H * 0.5 - glide * 420} drift={-(t - t0) * 9}>
        <Wall miss={0.1} lit={1} />
      </WallCam>
      <Veil opacity={ramp(t, t0 + 0.2, t0 + 0.9)} />

      <div style={{ position: 'absolute', inset: 0, transform: `translateY(${-glide * H}px)` }}>
        {/* screen 1: the docs */}
        {words.map((line) => <Headline key={line.text} t={a} line={line} />)}
        <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 54 }}>
          <div style={{ display: 'flex', gap: 48 }}>
            {sheets.map((sheet, i) => {
              const p = ramp(a, sheetIn[i] ?? 3, (sheetIn[i] ?? 3) + 0.32, 0, 1, Easing.out(Easing.cubic));
              return (
                <div
                  key={sheet.path}
                  style={{
                    width: 700, boxSizing: 'border-box', padding: '44px 48px 52px', borderRadius: 12,
                    background: C.card, border: `2px solid ${C.text}`,
                    boxShadow: '0 18px 50px oklch(20% 0.02 255 / 0.16)',
                    opacity: p, transform: `translateY(${(1 - p) * 60}px) rotate(${(1 - p) * (i ? 3 : -3)}deg)`,
                  }}
                >
                  <div style={{ fontFamily: FONT.mono, fontWeight: 500, fontSize: 30, color: C.accent3 }}>{sheet.path}</div>
                  <div style={{ fontFamily: FONT.sans, fontWeight: 600, fontSize: 68, letterSpacing: '-0.03em', lineHeight: 1.05, color: C.text, marginTop: 22 }}>{sheet.title}</div>
                </div>
              );
            })}
          </div>
          <div style={{ fontFamily: FONT.mono, fontWeight: 500, fontSize: 30, color: C.text, opacity: stackIn, transform: `translateY(${(1 - stackIn) * 16}px)` }}>{stack}</div>
        </AbsoluteFill>

        {/* screen 2: the close */}
        <AbsoluteFill style={{ top: H, alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
          <div style={{ fontFamily: FONT.sans, fontWeight: 600, fontSize: 176, letterSpacing: '-0.04em', lineHeight: 1, color: C.text, opacity: mark, transform: `scale(${1.15 - 0.15 * mark})` }}>{BRAND}</div>
          <div style={{ height: 8, width: 240 * rule, background: C.accent, marginTop: 34 }} />
          <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: 58, letterSpacing: '-0.02em', color: C.text, marginTop: 40 }}>
            {[...TAGLINE].map((ch, i) => {
              const p = ramp(c, tagFrom + i * 0.03, tagFrom + i * 0.03 + 0.2, 0, 1, Easing.out(Easing.cubic));
              return <span key={i} style={{ display: 'inline-block', whiteSpace: 'pre', opacity: p, transform: `translateY(${(1 - p) * 12}px)` }}>{ch}</span>;
            })}
          </div>
        </AbsoluteFill>
      </div>
    </Paper>
  );
};
