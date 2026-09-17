// Shared drawing helpers + palette for the bike-lane essay diagrams.
const P = {
  ink:      '#202122',
  muted:    '#54595d',
  faint:    '#72777d',
  paper:    '#ffffff',
  panel:    '#f8f9fa',
  rule:     '#c8ccd1',
  asphalt:  '#dcdcd8',
  asphalt2: '#d0d0cb',
  sidewalk: '#eeeeec',
  curb:     '#a2a9b1',
  stripe:   '#ffffff',
  red:      '#b32424',
  redFill:  '#fbe7e6',
  green:    '#14866d',
  greenFill:'#e4f2ee',
  blue:     '#3366cc',
  blueFill: '#e3ecfa',
  carBody:  '#6c7b8b',
  carGlass: '#aab7c4',
  carBody2: '#8a97a4',
  amber:    '#a15c00',
  amberFill:'#fdf0d5',
};

const esc = s => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const FONT = 'Liberation Sans, Arial, Helvetica, sans-serif';

function text(x, y, s, o = {}) {
  const a = [
    `x="${r(x)}"`, `y="${r(y)}"`,
    `font-family="${FONT}"`,
    `font-size="${o.size || 15}"`,
    `fill="${o.fill || P.ink}"`,
  ];
  if (o.weight) a.push(`font-weight="${o.weight}"`);
  if (o.anchor) a.push(`text-anchor="${o.anchor}"`);
  if (o.style)  a.push(`font-style="${o.style}"`);
  if (o.spacing) a.push(`letter-spacing="${o.spacing}"`);
  if (o.opacity) a.push(`opacity="${o.opacity}"`);
  if (o.transform) a.push(`transform="${o.transform}"`);
  return `<text ${a.join(' ')}>${esc(s)}</text>`;
}

const r = n => Math.round(n * 100) / 100;

function rect(x, y, w, h, o = {}) {
  const a = [`x="${r(x)}"`, `y="${r(y)}"`, `width="${r(w)}"`, `height="${r(h)}"`];
  a.push(`fill="${o.fill || 'none'}"`);
  if (o.stroke) { a.push(`stroke="${o.stroke}"`, `stroke-width="${o.sw || 1}"`); }
  if (o.rx) a.push(`rx="${o.rx}"`);
  if (o.opacity) a.push(`opacity="${o.opacity}"`);
  if (o.dash) a.push(`stroke-dasharray="${o.dash}"`);
  return `<rect ${a.join(' ')}/>`;
}

function line(x1, y1, x2, y2, o = {}) {
  const a = [`x1="${r(x1)}"`, `y1="${r(y1)}"`, `x2="${r(x2)}"`, `y2="${r(y2)}"`];
  a.push(`stroke="${o.stroke || P.ink}"`, `stroke-width="${o.sw || 1}"`);
  if (o.dash) a.push(`stroke-dasharray="${o.dash}"`);
  if (o.cap) a.push(`stroke-linecap="${o.cap}"`);
  if (o.opacity) a.push(`opacity="${o.opacity}"`);
  return `<line ${a.join(' ')}/>`;
}

function path(d, o = {}) {
  const a = [`d="${d}"`, `fill="${o.fill || 'none'}"`];
  if (o.stroke) a.push(`stroke="${o.stroke}"`, `stroke-width="${o.sw || 1}"`);
  if (o.dash) a.push(`stroke-dasharray="${o.dash}"`);
  if (o.opacity) a.push(`opacity="${o.opacity}"`);
  if (o.join) a.push(`stroke-linejoin="${o.join}"`);
  if (o.cap) a.push(`stroke-linecap="${o.cap}"`);
  return `<path ${a.join(' ')}/>`;
}

// Vertical dimension bracket (|<--->|) drawn at x, spanning y1..y2, label to the left.
function dimV(x, y1, y2, label, o = {}) {
  const col = o.stroke || P.muted;
  const tick = o.tick || 5;
  const [a, b] = y1 < y2 ? [y1, y2] : [y2, y1];
  const mid = (a + b) / 2;
  let s = '';
  s += line(x - tick, a, x + tick, a, { stroke: col, sw: 1 });
  s += line(x - tick, b, x + tick, b, { stroke: col, sw: 1 });
  s += line(x, a, x, b, { stroke: col, sw: 1 });
  s += path(`M${r(x)} ${r(a)} l -3 6 l 6 0 z`, { fill: col });
  s += path(`M${r(x)} ${r(b)} l -3 -6 l 6 0 z`, { fill: col });
  if (label) {
    const lx = o.side === 'right' ? x + 10 : x - 10;
    const anchor = o.side === 'right' ? 'start' : 'end';
    s += text(lx, mid + 5, label, { size: o.size || 14, fill: o.labelFill || P.ink,
                                     anchor, weight: o.weight || 'bold' });
  }
  return s;
}

// Horizontal dimension bracket.
function dimH(y, x1, x2, label, o = {}) {
  const col = o.stroke || P.muted;
  const tick = o.tick || 5;
  const [a, b] = x1 < x2 ? [x1, x2] : [x2, x1];
  const mid = (a + b) / 2;
  let s = '';
  s += line(a, y - tick, a, y + tick, { stroke: col, sw: 1 });
  s += line(b, y - tick, b, y + tick, { stroke: col, sw: 1 });
  s += line(a, y, b, y, { stroke: col, sw: 1 });
  if (label) {
    s += text(mid, y - 8, label, { size: o.size || 14, anchor: 'middle',
                                    fill: o.labelFill || P.ink, weight: o.weight || 'bold' });
  }
  return s;
}

module.exports = { P, FONT, text, rect, line, path, dimV, dimH, esc, r };

// ---------------------------------------------------------------------------
// Plan view of an ordinary city bike: ~5.8 ft long, 700c wheels, bars ~1.8 ft.
// Most bikes on a street are this, so most bikes in these figures are too.
// ---------------------------------------------------------------------------
function cityBike(cx, cy, S, o = {}) {
    const col = o.color || '#16365c';
    const L = 5.8;
    const f = n => n * S;
    const x0 = cx - f(L / 2);
    const X = n => x0 + f(n);

    let g = '';
    g += line(X(0.4), cy, X(5.4), cy, { stroke: col, sw: Math.max(1.1, f(0.085)), cap: 'round' });
    g += rect(X(0),    cy - f(0.14), f(2.25), f(0.28), { fill: col, rx: f(0.14) });
    g += rect(X(3.55), cy - f(0.14), f(2.25), f(0.28), { fill: col, rx: f(0.14) });
    g += line(X(3.40), cy - f(0.90), X(3.40), cy + f(0.90), { stroke: col, sw: Math.max(1.5, f(0.14)), cap: 'round' });
    g += rect(X(1.68), cy - f(0.74), f(0.44), f(1.48), { fill: col, rx: f(0.22), opacity: 0.85 });
    g += `<circle cx="${r(X(1.90))}" cy="${r(cy)}" r="${r(f(0.34))}" fill="${col}"/>`;
    return g;
}

// ---------------------------------------------------------------------------
// Plan view of a front-loading cargo bike, Riese & Müller Load 75 proportions:
// ~8.4 ft long, 20" front wheel ahead of the box, 27.5" rear under the rider.
// Drawn to the diagram's own scale so it stays honest about the space it takes.
//
//   cx, cy : centre of the bike's footprint, on the lateral centreline
//   S      : px per foot for the diagram it is being drawn into
// ---------------------------------------------------------------------------
function cargoBike(cx, cy, S, o = {}) {
    const col     = o.color   || '#16365c';
    const boxFill = o.boxFill || '#ffffff';
    const L = 8.4;                 // overall length, ft
    const f = n => n * S;
    const x0 = cx - f(L / 2);
    const X = n => x0 + f(n);
    const lw = Math.max(1.8, f(0.16));

    let g = '';

    // frame spine, running the whole length to the front fork
    g += line(X(0.9), cy, X(7.7), cy, { stroke: col, sw: Math.max(1.2, f(0.09)), cap: 'round' });

    // wheels, seen from above as strips: 27.5 in at the back, 20 in at the front
    g += rect(X(0),    cy - f(0.15), f(2.29), f(0.30), { fill: col, rx: f(0.15) });
    g += rect(X(6.73), cy - f(0.14), f(1.67), f(0.28), { fill: col, rx: f(0.14) });

    // the cargo box, which is the whole point of a front-loader
    g += rect(X(3.95), cy - f(1.08), f(2.9), f(2.16), { fill: boxFill, stroke: col, sw: lw, rx: f(0.18) });
    if (S > 9) {
        g += rect(X(4.13), cy - f(0.90), f(2.54), f(1.80), { fill: 'none', stroke: col, sw: Math.max(0.6, f(0.04)), rx: f(0.12), opacity: 0.30 });
    }

    // handlebars
    g += line(X(3.0), cy - f(1.05), X(3.0), cy + f(1.05), { stroke: col, sw: Math.max(1.6, f(0.15)), cap: 'round' });

    // rider, from above: shoulders across the bike, head on top
    g += rect(X(1.63), cy - f(0.74), f(0.44), f(1.48), { fill: col, rx: f(0.22), opacity: 0.85 });
    g += `<circle cx="${r(X(1.85))}" cy="${r(cy)}" r="${r(f(0.34))}" fill="${col}"/>`;

    // a kid in the box, arms out. Seen from above, a raised arm is a short
    // stroke reaching forward with a hand on the end - crossing lines just
    // read as scratches at this size.
    if (o.kid) {
        const kx = X(5.4);
        const kr = Math.max(3.4, f(0.40));
        const armW = Math.max(2, f(0.13));
        const handR = Math.max(1.6, f(0.16));
        for (const side of [-1, 1]) {
            g += line(kx + f(0.18), cy + side * f(0.26), kx + f(0.60), cy + side * f(0.66),
                      { stroke: col, sw: armW, cap: 'round' });
            g += `<circle cx="${r(kx + f(0.60))}" cy="${r(cy + side * f(0.66))}" r="${r(handR)}" fill="${col}"/>`;
        }
        g += `<circle cx="${r(kx)}" cy="${r(cy)}" r="${r(kr)}" fill="${col}"/>`;
    }

    return g;
}

module.exports.cargoBike = cargoBike;
module.exports.cityBike = cityBike;
