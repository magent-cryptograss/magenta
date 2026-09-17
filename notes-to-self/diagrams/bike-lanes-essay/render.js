const { Resvg } = require('@resvg/resvg-js');
const fs = require('fs');
const path = require('path');
const file = process.argv[2];
const width = parseInt(process.argv[3] || '1800', 10);
const svg = fs.readFileSync(file, 'utf8');
const resvg = new Resvg(svg, {
  fitTo: { mode: 'width', value: width },
  font: { loadSystemFonts: true, defaultFontFamily: 'Liberation Sans' },
  background: 'white',
});
const png = resvg.render().asPng();
const out = file.replace(/\.svg$/, '.png');
fs.writeFileSync(out, png);
console.log(path.basename(out), (png.length / 1024).toFixed(0) + ' KB');
