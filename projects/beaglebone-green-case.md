---
tags: [project, mechanical, cad, 3d-printing, beaglebone]
status: built
depends: []
repo: beaglebone-green-case
github: https://github.com/stradiot/beaglebone-green-case
created: 2026-08-09
---

# BeagleBone Green Case

## Now

Skeleton tray is printed and in use on the bench. The full case — walls,
lid, considered openings — is not started, and waits until the board has
a job that decides which connectors it must expose.

## Lessons

No session log yet — the tray was designed and printed before the vault
existed, so these come from the note itself rather than from dated entries.

- **The Fusion archive cannot be exported at all, and STEP is unaffected.**
  The `beaglebone-green-pcb` document holds an unresolved external reference
  to the vendor's original SolidWorks part, and the cloud translator fails
  on it, so there is no `.f3z`. STEP export goes through regardless, which
  is why `cad/*.step` is the geometry of record and the repo is a set of
  exports rather than the model. Breaking that external reference is the
  prerequisite if a full archive is ever wanted — it is the last item under
  [[#Plan]].
- **Building the open tray first deferred every connector decision instead
  of guessing at it.** A closed box designed before the board's use is known
  has to guess which connectors need openings; the skeleton solves the
  actual problem — a bare PCB sliding on the desk with header pins shorting
  on what is under it — while committing to none of them. The full case
  inherits the same parameter table and the skeleton stays a valid
  configuration of it, so nothing is thrown away by having started there.

## Goal

A printed enclosure for the BeagleBone Green, built in two stages. The
skeleton exists: an open mounting tray, board on four standoffs, every
connector and both P8/P9 headers reachable from all sides, no walls and no
lid. That is the shape a board still being probed needs. The full case —
walls, lid, considered openings — comes when the board stops being a
prototype and goes somewhere.

Deliberately out of scope: designing the board's mechanical drawing myself.
The BeagleBone Green's outline and hole pattern come from the vendor model,
and the case is built against it.

## Learning value

- Parametric CAD as a discipline: the model driven by named parameters, so
  a changed board dimension propagates instead of being re-drawn
- Print-tolerance work on parts that have to fit a real object — standoff
  heights, connector cutouts, the clearance a 0.4 nozzle actually holds
- Where the source of truth lives when the CAD tool is cloud-hosted and
  git only ever sees exports

## Practical value

Real and already collected. The tray is on the bench holding the board for
[[embedded-linux-course]], which is the whole of what a board being probed
daily needs — nothing shorts against the desk and every header stays
reachable.

The full case is worth less until the board stops being a prototype, which
is why it is not built yet. An enclosure designed around connectors whose
use has not been decided is an enclosure that gets reprinted.

## Architecture

The build-it/buy-it line here is unusual, because the interesting half is
the half that cannot be committed:

| Layer | Where it lives | Why |
| --- | --- | --- |
| Parametric model | Fusion 360, cloud — project `BeagleBone green case` | Feature history is the design; it has no useful file form |
| Exact geometry | `cad/*.step` in the repo | Opens in any CAD, survives Fusion |
| Print artefacts | `print/*.3mf`, plus the PrusaSlicer project | The mesh *and* the settings that produced it |
| Record | `doc/parameters.csv`, renders | The parameter table is the design intent in text |

So the repo is a set of exports and the reasoning behind them, not the
model. That split is deliberate and it is the part worth remembering: the
`.f3z` archive cannot be exported at all, because the `beaglebone-green-pcb`
document holds an unresolved external reference to the vendor's original
SolidWorks part and the cloud translator fails on it. STEP export is
unaffected. Breaking that link is the prerequisite if a full archive is ever
needed.

Binaries are tracked with Git LFS in that repo — which is exactly what this
vault refuses to do, and the reason the two stay separate repositories.

### Skeleton first, case second

Building the open tray first was not a shortcut. A closed box designed
before the board's real use is known guesses at which connectors need
openings; the skeleton defers every one of those decisions while still
solving the immediate problem, which is a bare PCB sliding around the desk
with header pins shorting on whatever is under it.

The full case inherits the same parameter table. Walls and a lid are added
to the existing model rather than started fresh, and the skeleton stays a
valid configuration of it — it remains the better thing to have on the bench
while pin work is happening.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| Model | Fusion 360 | Same tool as the enclosure in [[subghz-collar-remote-clone]] |
| Slicing | PrusaSlicer | Project file committed, not just the mesh |
| Printer | Prusa MK4IS, 0.4 nozzle, 0.2 mm PLA | Skeleton is a ~34 min print |
| Verification | The board itself | Fit is checked by seating it, not on screen |

## Budget

Mostly already spent.

| Item | Cost |
| --- | --- |
| Filament, skeleton print | ~1 € |
| Filament, full case | ~3 € |
| M3 standoffs and screws | ~5 € |
| BeagleBone Green | already owned |

## Software / firmware

No firmware. The pipeline is the software:

- Fusion parameters → `doc/parameters.csv`, exported when they change
- Fusion → STEP (`cad/`), the geometry of record
- Fusion → mesh, refinement High → `print/*.3mf`
- PrusaSlicer project committed alongside; sliced G-code is generated
  output and gitignored

## Plan

- [ ] Seat the board in the printed skeleton, record where the fit is tight
- [ ] Decide which connectors the full case must expose and which it may bury
- [ ] Walls and lid on the existing parameter table, skeleton kept as a configuration
- [ ] Print the full case, check thermals with the board under load
- [ ] Break the external reference in `beaglebone-green-pcb`, retry `.f3z` export

The board this holds is the candidate for
[[industrial-sensor-node-linux]], which is the note that decides what the
full case has to be: a node meant to end up mounted on a wall needs an
enclosure with a mounting face, and that requirement comes from there rather
than from here. [[beaglebone-pru-realtime]] wants the opposite and is the
argument for keeping the skeleton — cycle-counted pin work means a scope
probe on P8/P9, which a closed box prevents.

## Build log

Session entries live in [[beaglebone-green-case-log]].
