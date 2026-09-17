const { P, text, rect, line, path, r, cargoBike, cityBike } = require('./lib');

const W = 1264, H = 672;
const CW = 224, CGAP = 23, CX0 = 26;      // column width / gap / first column x
const cxOf = i => CX0 + i * (CW + CGAP);

const S = 6;                              // px per foot inside the mini streets
const TOP = 174, DEPTH = 27;              // strip top, feet of street shown
const BASE = TOP + DEPTH * S;
const ftY = ft => BASE - ft * S;

let s = `<defs>
<pattern id="hr2" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
  <rect width="7" height="7" fill="${P.redFill}"/><line x1="0" y1="0" x2="0" y2="7" stroke="${P.red}" stroke-width="1.2" opacity="0.42"/></pattern>
<pattern id="ha2" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
  <rect width="7" height="7" fill="${P.amberFill}"/><line x1="0" y1="0" x2="0" y2="7" stroke="${P.amber}" stroke-width="1.2" opacity="0.42"/></pattern>
<linearGradient id="wh" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#3d4145" stop-opacity="0"/>
  <stop offset="0.55" stop-color="#3d4145" stop-opacity="0.35"/>
  <stop offset="1" stop-color="#3d4145" stop-opacity="0.9"/></linearGradient>
<pattern id="hb2" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
  <rect width="6" height="6" fill="#ffffff"/><line x1="0" y1="0" x2="0" y2="6" stroke="${P.faint}" stroke-width="1" opacity="0.55"/></pattern>
</defs>` + rect(0, 0, W, H, { fill: P.paper });

s += text(W / 2, 46, 'Two different questions a street treatment can answer', { size: 27, weight: 'bold', anchor: 'middle' });
s += text(W / 2, 72, 'Every option below separates the rider from the car a little better than the last. Only the last two do anything at all to the car’s speed.',
  { size: 14, anchor: 'middle', fill: P.muted });
s += text(W / 2, 94, 'The streaks behind each moving car are its speed.', { size: 13, anchor: 'middle', fill: P.faint, style: 'italic' });

// ---- mini-street helpers --------------------------------------------------
const band = (x, a, b, f) => rect(x, ftY(b), CW, (b - a) * S, { fill: f });
function kerb(x) {
  return rect(x, BASE, CW, 12, { fill: P.sidewalk })
    + line(x, BASE, x + CW, BASE, { stroke: P.curb, sw: 2 });
}
function miniCar(x, a, b, len, body) {
  const L = len * S;
  return rect(x, ftY(b), L, (b - a) * S, { fill: body || P.carBody, rx: 3 })
    + rect(x + L * 0.32, ftY(b) + 2, L * 0.32, (b - a) * S - 4, { fill: P.carGlass, rx: 2, opacity: 0.85 });
}
const stripe = (x, ft) => line(x, ftY(ft), x + CW, ftY(ft), { stroke: P.stripe, sw: 2 });

// Speed streaks trailing a moving car. Length carries the message: the
// treatments that do not calm anything get a car that is still travelling.
function whoosh(carX, a, b, len) {
  if (!len) return '';
  const top = ftY(b), h = (b - a) * S;
  let g = '';
  [0.16, 0.38, 0.62, 0.84].forEach((f, i) => {
    const L = len * (i % 2 ? 0.66 : 1);
    g += rect(carX - L - 5, top + h * f - 1.7, L, 3.4, { fill: 'url(#wh)', rx: 1.7 });
  });
  return g;
}
const FAST = 78, SLOW = 24;

// ---- the five options -----------------------------------------------------
const OPTS = [
  {
    name: 'Paint only',
    sub: 'A stripe, nothing else',
    away: 0, slow: 0,
    note: ['The rider is inside the door zone', 'and inside the same lane the car', 'is travelling in.'],
    draw(x) {
      let g = band(x, 13, 27, P.asphalt) + band(x, 8, 13, P.greenFill) + band(x, 0, 8, P.asphalt2);
      g += miniCar(x + 14, 0.5, 6.5, 16);
      g += rect(x, ftY(10), CW, 3.5 * S, { fill: 'url(#hr2)' });
      g += stripe(x, 8) + stripe(x, 13);
      g += whoosh(x + 150, 13.5, 19.5, FAST) + miniCar(x + 150, 13.5, 19.5, 16);
      g += cityBike(x + 126, ftY(10.5), S);
      return g + kerb(x);
    },
  },
  {
    name: 'Buffered paint',
    sub: 'A stripe and some hatching',
    away: 1, slow: 0,
    note: ['The buffer is put on the traffic', 'side, so the door zone is exactly', 'where it was before.'],
    draw(x) {
      let g = band(x, 16, 27, P.asphalt) + band(x, 13, 16, '#ffffff') + band(x, 8, 13, P.greenFill) + band(x, 0, 8, P.asphalt2);
      g += rect(x, ftY(16), CW, 3 * S, { fill: 'url(#hb2)' });
      g += miniCar(x + 14, 0.5, 6.5, 16);
      g += rect(x, ftY(10), CW, 3.5 * S, { fill: 'url(#hr2)' });
      g += stripe(x, 8) + stripe(x, 13) + stripe(x, 16);
      g += whoosh(x + 150, 16.5, 22.5, FAST) + miniCar(x + 150, 16.5, 22.5, 16);
      g += cityBike(x + 126, ftY(10.5), S);
      return g + kerb(x);
    },
  },
  {
    name: 'Parking-protected',
    sub: 'The parked cars do the work',
    away: 4, slow: 0,
    note: ['A real barrier at last — but the', 'passenger doors still swing in,', 'and the traffic is unchanged.'],
    draw(x) {
      let g = band(x, 14, 27, P.asphalt) + band(x, 6, 14, P.asphalt2) + band(x, 0, 6, P.greenFill);
      g += miniCar(x + 14, 6.5, 12.5, 16);
      g += rect(x, ftY(6), CW, 3 * S, { fill: 'url(#ha2)' });
      g += stripe(x, 6) + stripe(x, 14);
      g += whoosh(x + 150, 14.5, 20.5, FAST) + miniCar(x + 150, 14.5, 20.5, 16);
      g += cityBike(x + 124, ftY(3), S);
      return g + kerb(x);
    },
  },
  {
    name: 'Narrowed carriageway',
    sub: 'Kerb-separated track as well',
    away: 5, slow: 3,
    note: ['Taking the width away from the', 'carriageway is the first thing here', 'that actually slows anybody down.'],
    draw(x) {
      let g = band(x, 20, 27, P.asphalt) + band(x, 10, 20, P.asphalt) + band(x, 8, 10, P.curb) + band(x, 0, 8, P.greenFill);
      g += line(x, ftY(20), x + CW, ftY(20), { stroke: '#e8c44a', sw: 2, dash: '10 7' });
      g += whoosh(x + 128, 10.5, 16.5, SLOW) + miniCar(x + 128, 10.5, 16.5, 16);
      g += cityBike(x + 62, ftY(4), S) + cityBike(x + 152, ftY(4), S);
      g += text(x + 6, ftY(14.4), '10 ft lane', { size: 10.5, fill: P.muted, weight: 'bold' });
      return g + kerb(x);
    },
  },
  {
    name: 'Modal filter',
    sub: 'No through route for motor traffic',
    away: 5, slow: 5,
    note: ['Through traffic is removed rather', 'than accommodated. The whole', 'surface becomes usable again.'],
    draw(x) {
      let g = band(x, 0, 27, P.asphalt);
      const bx = x + 122;
      g += line(bx, ftY(0.5), bx, ftY(26.5), { stroke: P.green, sw: 1.2, dash: '3 7' });
      for (let i = 0; i < 8; i++) g += `<circle cx="${r(bx)}" cy="${r(ftY(1.5 + i * 3.4))}" r="4.2" fill="${P.green}"/>`;
      g += miniCar(x + 4, 13, 19, 16, P.carBody);
      g += path(`M${r(x+112)} ${r(ftY(16))} l 0 -7 l -13 7 l 13 7 z`, { fill: P.muted });
      g += text(x + 110, ftY(21.4), 'no through route', { size: 10.5, anchor: 'end', fill: P.muted, weight: 'bold' });
      g += cityBike(x + 170, ftY(5), S) + cargoBike(x + 172, ftY(14), S) + cityBike(x + 166, ftY(23), S);
      return g + kerb(x);
    },
  },
];

// ---- columns --------------------------------------------------------------
OPTS.forEach((o, i) => {
  const x = cxOf(i);
  s += `<circle cx="${r(x+11)}" cy="${r(TOP-52)}" r="11" fill="${P.ink}"/>`;
  s += text(x + 11, TOP - 47, String(i + 1), { size: 13, anchor: 'middle', fill: '#fff', weight: 'bold' });
  s += text(x + 30, TOP - 46, o.name, { size: 16.5, weight: 'bold' });
  s += text(x, TOP - 24, o.sub, { size: 12.5, fill: P.muted });
  s += `<clipPath id="cc${i}"><rect x="${r(x)}" y="${TOP}" width="${CW}" height="${DEPTH * S + 12}"/></clipPath>`;
  s += `<g clip-path="url(#cc${i})">` + o.draw(x) + `</g>`;
  s += rect(x, TOP, CW, DEPTH * S, { stroke: P.rule, sw: 1 });
  o.note.forEach((L, k) => s += text(x, BASE + 40 + k * 18, L, { size: 12.5, fill: P.ink }));
});

// ---- the two meters -------------------------------------------------------
function meter(x, n, col) {
  let g = '';
  for (let k = 0; k < 5; k++) {
    g += rect(x + k * 21, 0, 16, 13, { fill: k < n ? col : '#ffffff', stroke: k < n ? col : P.rule, sw: 1.2, rx: 2 });
  }
  return g;
}
const MY1 = BASE + 122, MY2 = BASE + 176;
[[MY1, 'Does it keep you away from the cars?', 'away', P.blue],
 [MY2, 'Does it slow the cars down?', 'slow', P.green]].forEach(([y, label, key, col]) => {
  s += rect(16, y - 26, W - 32, 46, { fill: P.panel, rx: 4 });
  s += text(26, y - 8, label, { size: 14.5, weight: 'bold' });
  OPTS.forEach((o, i) => { s += `<g transform="translate(${r(cxOf(i))} ${r(y - 2)})">` + meter(0, o[key], col) + `</g>`; });
});
[0, 1, 2].forEach(i => s += text(cxOf(i) + 112, MY2 + 9, 'none at all', { size: 12.5, fill: P.red, weight: 'bold' }));

// ---- the two groups -------------------------------------------------------
const GY = MY2 + 58;
function brace(x0, x1, col, head, body) {
  let g = line(x0, GY, x1, GY, { stroke: col, sw: 2.5 });
  g += line(x0, GY, x0, GY + 8, { stroke: col, sw: 2.5 });
  g += line(x1, GY, x1, GY + 8, { stroke: col, sw: 2.5 });
  g += text((x0 + x1) / 2, GY + 30, head, { size: 16, anchor: 'middle', weight: 'bold', fill: col });
  g += text((x0 + x1) / 2, GY + 52, body, { size: 13.5, anchor: 'middle', fill: P.ink });
  return g;
}
s += brace(cxOf(0), cxOf(2) + CW, P.red, 'These rearrange the bicycle',
  'The car keeps its speed, its width and its priority. Nothing has been calmed.');
s += brace(cxOf(3), cxOf(4) + CW, P.green, 'These rearrange the car',
  'Width or access is taken away, so the driving changes.');

require('fs').writeFileSync(__dirname + '/d2-ladder.svg',
  `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${s}</svg>`);
console.log('d2 ok');
