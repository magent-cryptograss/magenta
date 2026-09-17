const { P, FONT, text, rect, line, path, dimV, dimH, r, cargoBike } = require('./lib');

// ---- geometry -------------------------------------------------------------
const S = 22;                          // px per foot
const CURB = 626;                      // y of the curb face
const ftY  = ft => CURB - ft * S;      // feet from curb  ->  y
const X0 = 178, X1 = 1142;
const W = 1250, H = 960;

const PARK = [0, 8], BIKE = [8, 13], TRAV = [13, 24];
const CAR_W = 6, CAR_OFF = 0.5, DOOR = 3.5;
const DZ = [CAR_OFF + CAR_W, CAR_OFF + CAR_W + DOOR];   // 6.5 -> 10.0
const RW = 2.5;
const RC = (BIKE[0] + BIKE[1]) / 2;                      // 10.5, the centre of the paint
const RID = [RC - RW / 2, RC + RW / 2];                  // 9.25 -> 11.75
const MV = [13.5, 19.5];                                 // a driver who does not leave the lane

let s = '';
s += `<defs>
<pattern id="hatchRed" width="10" height="10" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
  <rect width="10" height="10" fill="${P.redFill}"/>
  <line x1="0" y1="0" x2="0" y2="10" stroke="${P.red}" stroke-width="1.5" opacity="0.34"/>
</pattern>
<pattern id="hatchWalk" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
  <rect width="7" height="7" fill="${P.sidewalk}"/>
  <line x1="0" y1="0" x2="0" y2="7" stroke="${P.curb}" stroke-width="0.8" opacity="0.45"/>
</pattern>
</defs>`;
s += rect(0, 0, W, H, { fill: P.paper });

s += text(W / 2, 44, 'What is actually left of a 5-foot painted bike lane', { size: 27, weight: 'bold', anchor: 'middle' });
s += text(W / 2, 70, 'Plan view, drawn to scale. Standard US dimensions: 8 ft parking lane, 5 ft bike lane (AASHTO minimum), 11 ft travel lane.',
  { size: 14, anchor: 'middle', fill: P.muted });

// ---- roadway --------------------------------------------------------------
const band = (a, b, fill) => rect(X0, ftY(b), X1 - X0, (b - a) * S, { fill });
s += band(TRAV[0], TRAV[1], P.asphalt);
s += band(BIKE[0], BIKE[1], P.greenFill);
s += band(PARK[0], PARK[1], P.asphalt2);
s += rect(X0, CURB, X1 - X0, 40, { fill: 'url(#hatchWalk)' });
s += line(X0, CURB, X1, CURB, { stroke: P.curb, sw: 3 });
s += text(X0 + 12, CURB + 26, 'SIDEWALK', { size: 11.5, fill: P.faint, weight: 'bold', spacing: '1.5' });

s += line(X0, ftY(BIKE[0]), X1, ftY(BIKE[0]), { stroke: P.stripe, sw: 4 });
s += line(X0, ftY(BIKE[1]), X1, ftY(BIKE[1]), { stroke: P.stripe, sw: 4 });
s += line(X0, ftY(TRAV[1]), X1, ftY(TRAV[1]), { stroke: '#e8c44a', sw: 3, dash: '26 18' });
s += text(X1, ftY(TRAV[1]) - 8, 'centre line', { size: 12, anchor: 'end', fill: P.faint });

// ---- parked cars ----------------------------------------------------------
function parkedCar(x, len, body) {
  const y = ftY(CAR_OFF + CAR_W), h = CAR_W * S, L = len * S;
  return rect(x, y, L, h, { fill: body, rx: 9 })
    + rect(x + L * 0.30, y + 5, L * 0.34, h - 10, { fill: P.carGlass, rx: 5, opacity: 0.85 })
    + line(x + L * 0.62, y + 3, x + L * 0.62, y + h - 3, { stroke: '#5a6672', sw: 1.2 })
    + line(x + L * 0.30, y + 3, x + L * 0.30, y + h - 3, { stroke: '#5a6672', sw: 1.2 });
}
const carA = { x: X0 + 30, len: 16 };
const carB = { x: X0 + 30 + 19 * S, len: 16 };
s += parkedCar(carA.x, carA.len, P.carBody);
s += parkedCar(carB.x, carB.len, P.carBody2);

// ---- the door zone, as a continuous band ---------------------------------
s += rect(X0, ftY(DZ[1]), X1 - X0, (DZ[1] - DZ[0]) * S, { fill: 'url(#hatchRed)' });
s += line(X0, ftY(DZ[1]), X1, ftY(DZ[1]), { stroke: P.red, sw: 2, dash: '8 5' });

// ---- one door actually open ----------------------------------------------
const hx = carB.x + carB.len * S - 5 * S;   // hinged toward the front of the car
const hy = ftY(CAR_OFF + CAR_W);
const OPEN = 72;                             // degrees; doors do not open square
const rad = OPEN * Math.PI / 180;
const tipX = hx - Math.cos(rad) * DOOR * S;
const tipY = hy - Math.sin(rad) * DOOR * S;
// swept wedge, from closed (pointing aft) to open
s += path(`M${r(hx)} ${r(hy)} L ${r(hx - DOOR*S)} ${r(hy)} A ${r(DOOR*S)} ${r(DOOR*S)} 0 0 1 ${r(tipX)} ${r(tipY)} Z`,
  { fill: P.red, opacity: 0.22, stroke: P.red, sw: 1.4, dash: '5 4' });
// the door panel itself
s += `<g transform="rotate(${OPEN} ${r(hx)} ${r(hy)})">`
   + rect(hx - DOOR * S, hy - 8, DOOR * S, 8, { fill: P.red, stroke: '#7d1414', sw: 1, rx: 2 })
   + `</g>`;
s += `<circle cx="${r(hx)}" cy="${r(hy)}" r="4.5" fill="${P.red}"/>`;

// ---- the rider's envelope, riding the centre of the paint as marked ------
s += rect(X0, ftY(RID[1]), X1 - X0, RW * S, { fill: P.blueFill, opacity: 0.78 });
s += line(X0, ftY(RID[0]), X1, ftY(RID[0]), { stroke: P.blue, sw: 1.6, dash: '6 4' });
s += line(X0, ftY(RID[1]), X1, ftY(RID[1]), { stroke: P.blue, sw: 1.6, dash: '6 4' });
// the overlap: 9.25 -> 10.0 ft, where the handlebar is inside the door's reach
s += rect(X0, ftY(DZ[1]), X1 - X0, (DZ[1] - RID[0]) * S, { fill: P.red, opacity: 0.42 });

// ---- the rider: a front-loading cargo bike, drawn to the same scale --------
const cx = carA.x + 190;
s += cargoBike(cx, ftY(RC), S);
// the 9-inch overlap, called out in the right-hand gutter
const ovY = ftY((RID[0] + DZ[1]) / 2);
s += line(X1, ovY, X1 + 22, ovY, { stroke: P.red, sw: 1.6 });
s += text(X1 + 28, ovY - 2, '9 in', { size: 15, weight: 'bold', fill: P.red });
s += text(X1 + 28, ovY + 15, 'cargo box', { size: 11.5, fill: P.red });
s += text(X1 + 28, ovY + 28, 'inside the', { size: 11.5, fill: P.red });
s += text(X1 + 28, ovY + 41, "door's reach", { size: 11.5, fill: P.red });

// ---- passing car ----------------------------------------------------------
const mvX = carA.x + 20, mvL = 17 * S;
s += rect(mvX, ftY(MV[1]), mvL, (MV[1] - MV[0]) * S, { fill: P.carBody, rx: 9 });
s += rect(mvX + mvL * 0.30, ftY(MV[1]) + 5, mvL * 0.34, (MV[1] - MV[0]) * S - 10, { fill: P.carGlass, rx: 5, opacity: 0.85 });
s += text(mvX + mvL / 2, ftY((MV[0] + MV[1]) / 2) + 5, 'passing without changing lanes', { size: 12.5, anchor: 'middle', fill: '#ffffff', weight: 'bold' });
const clrX = mvX + mvL + 48;
s += dimV(clrX, ftY(RID[1]), ftY(MV[0]), '', { stroke: P.red });
s += text(clrX + 10, ftY((RID[1] + MV[0]) / 2) + 5, '1¾ ft clearance', { size: 13.5, weight: 'bold', fill: P.red });

// ---- dimension stack ------------------------------------------------------
const DX = 128;
[[PARK, '8 ft', 'parking'], [BIKE, '5 ft', 'bike lane'], [TRAV, '11 ft', 'travel lane']].forEach(([b, lab, sub]) => {
  s += dimV(DX, ftY(b[0]), ftY(b[1]), lab, {});
  s += text(DX - 10, ftY((b[0] + b[1]) / 2) + 21, sub, { size: 12.5, anchor: 'end', fill: P.muted });
});

// ---- door callout ---------------------------------------------------------
function callout(x, y, w, lines, o = {}) {
  let g = rect(x, y, w, 20 + lines.length * 19, { fill: o.fill || '#ffffff', stroke: o.stroke || P.rule, sw: 1.2, rx: 4 });
  lines.forEach((L, i) => g += text(x + 13, y + 21 + i * 19, L, { size: 13.5, weight: i === 0 ? 'bold' : 'normal' }));
  return g;
}
const coX = tipX + 34, coY = ftY(23.4);
s += line(tipX, tipY, coX, coY + 46, { stroke: P.red, sw: 1.3, dash: '4 3' });
s += callout(coX, coY, 300, [
  'A door reaches 3½ ft from the car —',
  '2 ft into the bike lane, along the whole',
  'parking row, not only where a door',
  'happens to be open right now.',
], { fill: P.redFill, stroke: P.red });

// ---- footer ---------------------------------------------------------------
const LY = CURB + 66;
[['url(#hatchRed)', P.red, 'reach of an opening car door'],
 [P.blueFill, P.blue, 'where the rider actually is'],
 [P.greenFill, P.green, 'the painted bike lane']].forEach(([f, st, lab], i) => {
  const x = X0 + i * 348;
  s += rect(x, LY, 28, 16, { fill: f, stroke: st, sw: 1.2 });
  s += text(x + 37, LY + 13, lab, { size: 13.5, fill: P.muted });
});
s += line(X0, LY + 38, X1, LY + 38, { stroke: P.rule, sw: 1 });

const FY = LY + 72;
s += text(X0, FY, 'Measured from the curb face', { size: 16, weight: 'bold' });
[['painted lane', '8 ft – 13 ft'], ['door zone', '6½ ft – 10 ft'], ['usable lane', '10 ft – 13 ft  =  3 ft']].forEach(([k, v], i) => {
  s += text(X0, FY + 28 + i * 24, k, { size: 14, fill: P.muted });
  s += text(X0 + 116, FY + 28 + i * 24, v, { size: 14, weight: i === 2 ? 'bold' : 'normal', fill: i === 2 ? P.green : P.ink });
});

const BX = X0 + 470, BSC = 68;
s += text(BX, FY, 'What those 3 ft have to hold', { size: 16, weight: 'bold' });
s += line(BX + 3 * BSC, FY + 8, BX + 3 * BSC, FY + 100, { stroke: P.green, sw: 2, dash: '5 4' });
s += rect(BX, FY + 14, 3 * BSC, 30, { fill: P.greenFill, stroke: P.green, sw: 1.5, rx: 3 });
s += text(BX + 3 * BSC / 2, FY + 34, '3 ft available', { size: 13.5, anchor: 'middle', weight: 'bold', fill: P.green });
s += rect(BX, FY + 52, RW * BSC, 30, { fill: P.blueFill, stroke: P.blue, sw: 1.5, rx: 3 });
s += text(BX + RW * BSC / 2, FY + 72, '2½ ft rider', { size: 13.5, anchor: 'middle', weight: 'bold', fill: P.blue });
s += rect(BX + RW * BSC, FY + 52, 3 * BSC, 30, { fill: P.amberFill, stroke: P.amber, sw: 1.5, rx: 3 });
s += text(BX + RW * BSC + 3 * BSC / 2, FY + 72, '3 ft passing clearance', { size: 13.5, anchor: 'middle', weight: 'bold', fill: P.amber });
s += line(BX + 3 * BSC, FY + 96, BX + 5.5 * BSC, FY + 96, { stroke: P.red, sw: 2.5 });
s += text(BX + 4.25 * BSC, FY + 116, 'short by 2½ ft', { size: 14.5, anchor: 'middle', weight: 'bold', fill: P.red });

s += text(X0, H - 22, 'Door reach and rider envelope are typical values, not worst cases. Three feet is the passing clearance required by law in most US states.',
  { size: 12.5, fill: P.faint, style: 'italic' });

require('fs').writeFileSync(__dirname + '/d1-door-zone.svg',
  `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${s}</svg>`);
console.log('d1 ok');
