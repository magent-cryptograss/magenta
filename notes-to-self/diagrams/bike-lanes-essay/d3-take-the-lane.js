const { P, text, rect, line, path, dimV, r, cargoBike, cityBike } = require('./lib');

const W = 1260, H = 792;
const S = 13;                       // px per foot
const PW = 396, GAP = 12;           // panel width / gap
const PY = 150, PH = 31 * S;        // panel top / height (0 -> 31 ft of street)
const BASE = PY + PH;               // y of the curb face
const ftY = ft => BASE - ft * S;

const PARK = [0, 8], BIKE = [8, 13], TRAV = [13, 24], OPP = [24, 31];

let s = `<defs>
<pattern id="hr" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
  <rect width="8" height="8" fill="${P.redFill}"/><line x1="0" y1="0" x2="0" y2="8" stroke="${P.red}" stroke-width="1.3" opacity="0.38"/>
</pattern>
<pattern id="hw" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
  <rect width="6" height="6" fill="${P.sidewalk}"/><line x1="0" y1="0" x2="0" y2="6" stroke="${P.curb}" stroke-width="0.7" opacity="0.45"/>
</pattern>
<clipPath id="c1"><rect x="24" y="${PY}" width="${PW}" height="${PH + 22}"/></clipPath>
<clipPath id="c2"><rect x="${24 + PW + GAP}" y="${PY}" width="${PW}" height="${PH + 22}"/></clipPath>
<clipPath id="c3"><rect x="${24 + 2 * (PW + GAP)}" y="${PY}" width="${PW}" height="${PH + 22}"/></clipPath>
</defs>` + rect(0, 0, W, H, { fill: P.paper });

s += text(W / 2, 46, 'Where you ride decides how you are passed', { size: 27, weight: 'bold', anchor: 'middle' });
s += text(W / 2, 72, 'The same street in all three panels. Only the rider’s position changes — and with it, what the driver behind has to do.',
  { size: 14, anchor: 'middle', fill: P.muted });

// ---- street chrome, drawn once per panel ---------------------------------
function street(x, showBikeLane) {
  const b = (a, c, f) => rect(x, ftY(c), PW, (c - a) * S, { fill: f });
  let g = b(OPP[0], OPP[1], P.asphalt);
  g += b(TRAV[0], TRAV[1], P.asphalt);
  g += b(BIKE[0], BIKE[1], showBikeLane ? P.greenFill : P.asphalt);
  g += b(PARK[0], PARK[1], P.asphalt2);
  g += rect(x, BASE, PW, 22, { fill: 'url(#hw)' });
  g += line(x, BASE, x + PW, BASE, { stroke: P.curb, sw: 2.5 });
  if (showBikeLane) {
    g += line(x, ftY(BIKE[0]), x + PW, ftY(BIKE[0]), { stroke: P.stripe, sw: 3 });
    g += line(x, ftY(BIKE[1]), x + PW, ftY(BIKE[1]), { stroke: P.stripe, sw: 3 });
  }
  g += line(x, ftY(TRAV[1]), x + PW, ftY(TRAV[1]), { stroke: '#e8c44a', sw: 2.5, dash: '18 12' });
  return g;
}

function parkedCars(x) {
  let g = '';
  for (let i = 0; i < 2; i++) {
    const cx0 = x + 8 + i * 19 * S, L = 16 * S, y = ftY(6.5), h = 6 * S;
    g += rect(cx0, y, L, h, { fill: i ? P.carBody2 : P.carBody, rx: 6 });
    g += rect(cx0 + L * 0.30, y + 4, L * 0.34, h - 8, { fill: P.carGlass, rx: 4, opacity: 0.85 });
  }
  // the door zone is a property of the parking row, not of the rider
  g += rect(x, ftY(10), PW, 3.5 * S, { fill: 'url(#hr)' });
  return g;
}

function car(x, y0, y1, len, label, body) {
  const L = len * S;
  let g = rect(x, ftY(y1), L, (y1 - y0) * S, { fill: body || P.carBody, rx: 6 });
  g += rect(x + L * 0.30, ftY(y1) + 4, L * 0.34, (y1 - y0) * S - 8, { fill: P.carGlass, rx: 4, opacity: 0.85 });
  if (label) g += text(x + L / 2, ftY((y0 + y1) / 2) + 4, label, { size: 11, anchor: 'middle', fill: '#fff', weight: 'bold' });
  return g;
}

// ---- panel frame ----------------------------------------------------------
function header(x, n, title, sub) {
  let g = `<circle cx="${r(x+13)}" cy="${r(PY-46)}" r="12" fill="${P.ink}"/>`;
  g += text(x + 13, PY - 41, String(n), { size: 14, anchor: 'middle', fill: '#fff', weight: 'bold' });
  g += text(x + 34, PY - 40, title, { size: 18, weight: 'bold' });
  g += text(x, PY - 16, sub, { size: 13, fill: P.muted });
  return g;
}

// verdict strip under each panel
function verdict(x, tone, head, body) {
  const col = tone === 'bad' ? P.red : tone === 'ok' ? P.amber : P.green;
  const fill = tone === 'bad' ? P.redFill : tone === 'ok' ? P.amberFill : P.greenFill;
  let g = rect(x, BASE + 40, PW, 96, { fill, stroke: col, sw: 1.4, rx: 4 });
  g += text(x + 14, BASE + 66, head, { size: 15, weight: 'bold', fill: col });
  body.forEach((L, i) => g += text(x + 14, BASE + 90 + i * 19, L, { size: 13, fill: P.ink }));
  return g;
}

// ===========================================================================
// 1. riding the paint
const X1 = 24;
s += header(X1, 1, 'Riding the paint', 'Rider in the centre of the marked lane');
s += `<g clip-path="url(#c1)">`;
s += street(X1, true);
s += parkedCars(X1);
s += rect(X1, ftY(11.75), PW, 2.5 * S, { fill: P.blueFill, opacity: 0.8 });
s += rect(X1, ftY(10), PW, 0.75 * S, { fill: P.red, opacity: 0.4 });
s += car(X1 + 138, 13.5, 19.5, 17, 'no lane change', P.carBody);
s += cityBike(X1 + 250, ftY(10.5), S);
s += `</g>`;
s += dimV(X1 + 316, ftY(11.75), ftY(13.5), '', { stroke: P.red });
s += text(X1 + 326, ftY(12.6) + 4, '1¾ ft', { size: 12.5, weight: 'bold', fill: P.red });
s += verdict(X1, 'bad', 'The driver does nothing', [
  'Passing costs the driver no time and no',
  'attention, so nothing about the street',
  'gets slower or calmer.',
]);

// ===========================================================================
// 2. taking the lane
const X2 = X1 + PW + GAP;
s += header(X2, 2, 'Taking the lane', 'Rider in the centre of the travel lane');
s += `<g clip-path="url(#c2)">`;
s += street(X2, true);
s += parkedCars(X2);
s += rect(X2, ftY(19.75), PW, 2.5 * S, { fill: P.blueFill, opacity: 0.8 });
s += car(X2 + 138, 24.5, 30.5, 17, 'full lane change', P.carBody);
s += cityBike(X2 + 250, ftY(18.5), S);
s += `</g>`;
s += dimV(X2 + 316, ftY(19.75), ftY(24.5), '', { stroke: P.green });
s += text(X2 + 326, ftY(22.1) + 4, '4¾ ft', { size: 12.5, weight: 'bold', fill: P.green });
s += text(X2 + 8, ftY(23.1), 'the driver must cross the centre line to pass', { size: 11.5, fill: P.amber, weight: 'bold' });
s += verdict(X2, 'ok', 'The driver has to decide', [
  'Overtaking now needs a gap in oncoming',
  'traffic. Drivers wait, and waiting is what',
  'traffic calming actually is.',
]);

// ===========================================================================
// 3. riding in formation
const X3 = X2 + PW + GAP;
s += header(X3, 3, 'Riding in formation', 'Two riders hold the lane; a family bike tucks inside');
s += `<g clip-path="url(#c3)">`;
s += street(X3, true);
s += parkedCars(X3);
s += rect(X3, ftY(22), PW, 6.5 * S, { fill: P.blueFill, opacity: 0.8 });
s += car(X3 + 116, 24.5, 30.5, 17, 'changes lanes and slows', P.carBody);
s += cityBike(X3 + 306, ftY(20.7), S);
s += cityBike(X3 + 190, ftY(20.2), S);
s += cargoBike(X3 + 236, ftY(17.1), S, { color: '#8a5d1f', boxFill: '#fdf3e2', kid: true });
s += `</g>`;
s += text(X3 + 8, ftY(23.1), 'the driver must cross the centre line to pass', { size: 11.5, fill: P.amber, weight: 'bold' });
s += line(X3 + 236, ftY(15.9), X3 + 236, ftY(14.4), { stroke: '#8a5d1f', sw: 1.3, dash: '4 3' });
s += text(X3 + 236, ftY(13.4), 'the rider being sheltered', { size: 12, anchor: 'middle', weight: 'bold', fill: '#8a5d1f' });
s += verdict(X3, 'good', 'The street works for everyone', [
  'The strong riders spend the risk. The slow,',
  'the young and the old get a lane that is',
  'calm enough to use.',
]);

s += line(24, H - 46, W - 24, H - 46, { stroke: P.rule, sw: 1 });
s += text(24, H - 24, 'Plan view, drawn to scale, same 8 ft / 5 ft / 11 ft street as the previous figure. Clearances measured from the outside of the handlebar.',
  { size: 12.5, fill: P.faint, style: 'italic' });

require('fs').writeFileSync(__dirname + '/d3-take-the-lane.svg',
  `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${s}</svg>`);
console.log('d3 ok');
