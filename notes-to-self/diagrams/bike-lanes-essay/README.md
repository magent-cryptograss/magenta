# Diagrams for User:JMyles/Why Car lanes Divide Us

Three figures drawn for Justin's bike-lane essay on PickiPedia, 2026-09-04
(Ethereum block ~25,902,740).

## Files

| script | output | on the wiki |
|---|---|---|
| `d1-door-zone.js` | `d1-door-zone.png` | `File:Painted bike lane door zone geometry.png` |
| `d2-ladder.js` | `d2-ladder.png` | `File:Street treatments separation versus traffic calming.png` |
| `d3-take-the-lane.js` | `d3-take-the-lane.png` | `File:Lane position and overtaking behaviour.png` |

`lib.js` holds the shared palette and SVG helpers. `render.js` rasterises with
`@resvg/resvg-js`.

## Rebuilding

PickiPedia does **not** accept SVG uploads — `svg` is absent from
`$wgFileExtensions`, and there is no Graph/Mermaid/SVGEdit extension. So these
are authored as SVG and shipped as PNG.

There is no `rsvg-convert` in the container and no sudo, and ImageMagick falls
back to its own MSVG renderer, which mangles text. Use resvg:

```sh
npm i @resvg/resvg-js
node d1-door-zone.js && node render.js d1-door-zone.svg 1800
```

Fonts: Liberation Sans is present and is metric-compatible with Arial.

## Drawing conventions

All three figures share one street, drawn to scale in plan view: 8 ft parking
lane, 5 ft bike lane (AASHTO minimum), 11 ft travel lane. Parked car 6 ft wide
set 6 in off the curb; door reach 3½ ft; rider envelope 2½ ft. Distances are
measured from the curb face.

Bicycles come from two helpers in `lib.js`, both plan-view and both drawn at
the host diagram's own px-per-foot so they stay honest about the space they use:

- `cityBike()` — an ordinary bike, 5.8 ft long, 700c wheels, bars 1.8 ft.
- `cargoBike()` — a front-loading cargo bike at Riese & Müller Load 75
  proportions: 8.4 ft long, 27.5 in rear wheel, 20 in front wheel ahead of the
  box, box 2.9 x 2.16 ft. Pass `{ kid: true }` for a child in the box.

**Roughly one bike in five is a cargo bike** — 3 of the 14 across the three
figures. A street where everyone rides a Load 75 reads as a brochure. Each
cargo bike earns its place: the door-zone figure (where the box, not the
handlebar, is what sits in the door's reach), the modal-filter panel of
figure 2, and the sheltered rider in panel 3 of figure 3. Everything else is
an ordinary bike.

Consequences that fall out of that geometry, and that the figures assert:

- door zone runs 6½ ft – 10 ft from the curb, so it covers the inner 2 ft of
  the painted lane
- usable lane is therefore 3 ft, against 2½ ft of rider plus 3 ft of legally
  required passing clearance — short by 2½ ft
- a rider centred in the paint has their kerb-side handlebar 9 in inside the
  door's reach

## Known limitation

The wiki skin's content column is roughly 640 px, so a 1800 px figure is
displayed at about 35%. The figures are click-to-enlarge rather than legible
inline. A lower-density variant would be needed for inline reading.
