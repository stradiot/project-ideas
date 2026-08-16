---
tags: [project, rc, mechanical, cad, control, aerodynamics]
status: idea
depends: []
created: 2026-08-10
---

# Printed RC Plane

## Now

Not started. Nothing here is in progress — the plan below is the whole
of it.

## Goal

Design, print and fly a fixed-wing model — airframe first, electronics
second, and firmware not at all to begin with. The first version flies on
servos and a receiver, exactly as a model aircraft has for fifty years.

Deliberately out of scope for the first airframe: any autopilot, any
stabilisation, any telemetry. A plane that flies well on manual sticks is
the whole target, and adding electronics to an airframe that does not fly
well only hides the problem.

## Learning value

- Aerodynamics as something built rather than read: wing section, incidence,
  dihedral, control surface throw
- Centre of gravity, and why it is the one number that decides whether a
  plane is flyable
- Parametric CAD for parts that have to be light, stiff and printable
- Trimming an aircraft — reading what it does and changing the model

## Practical value

An aircraft that flies, which is worth having for its own sake and is the
one project here whose output is simply enjoyable. A printed airframe is
also genuinely cheaper to keep flying than a bought one — a broken wing is
a reprint rather than a replacement order.

It is the safe place to be wrong about a control loop, which is why it sits
ahead of [[custom-flight-controller-drone]]. A plane with a badly tuned
wing leveller glides; a quadcopter with a badly tuned attitude loop falls
out of the air and takes its motors with it.

## Architecture

The airframe is the project. Everything else is bought or reused.

| Block | Approach | Reasoning |
| --- | --- | --- |
| Airframe | Designed and printed by me | The subject |
| Motor, ESC, servos | Bought | Nothing to learn from winding a motor |
| Radio | Hobby TX/RX — the same set as [[rc-car-custom-controller]] | Bought once, used by three projects |
| Battery | 3S LiPo, bought | |
| Firmware | None, in version 1 | Deliberately |

### Why printed, and why a plane

Printing is what makes crashing acceptable. A broken wing is a reprint and
an evening, not a purchase and a week — which matters enormously for a
discipline learned entirely by crashing. It also puts the Prusa to work on
something structural rather than decorative: printed airframes live or die
on wall thickness, infill and print orientation, and getting a part light
enough to fly and stiff enough not to flutter is a real constraint that a
printed case never imposes.

A plane also fails gently. Lose control of a quadcopter and it falls; lose
control of a plane and it glides, usually into something soft. That
difference is why this comes before [[custom-flight-controller-drone]] and
not after.

### Where the flight controller arrives

Version 2, and as an *assistant* rather than a pilot: a wing leveller. One
IMU, a complementary filter, and two PID loops holding roll and pitch near
zero when the sticks are centred. That is the same attitude loop the drone
needs, on an airframe that stays airborne while the loop is being tuned and
glides down if it is switched off mid-air.

Learning to close that loop on something forgiving, then taking it to a
machine that hovers, is the right order. The drone note already says the
loop is most of a fixed-wing controller; this is that observation used
rather than noted.

## Tools

| Purpose | Tool | Note |
| --- | --- | --- |
| CAD | Fusion 360 | Same parametric workflow as [[beaglebone-green-case]] |
| Printing | Prusa MK4IS | Already owned |
| Filament | LW-PLA for the airframe, PETG for mounts | Foaming PLA is what makes a printed plane light enough |
| Radio | Hobby TX/RX set | Shared with [[rc-car-custom-controller]] |
| Field | An open field, and no people | Non-negotiable |
| Balance | A CG balance stand, printed | Two minutes to print, saves the first flight |

## Budget

Rough estimates. The radio line is zero if the car came first.

| Item | Cost |
| --- | --- |
| LW-PLA and PETG filament | 30–45 € |
| Brushless motor + ESC | 20–35 € |
| Servos, 4× 9 g | 10–15 € |
| Propellers and spinners, several | 10 € |
| 3S LiPo ×2 + charger | 35–55 € |
| Radio TX/RX set | 0–80 € |
| Pushrods, horns, hinges, hardware | ~15 € |

Around 120–175 € for the first aircraft, and every crash after that costs
filament. The second airframe is essentially free.

Sourcing: [[parts-sourcing]] — the airframe hardware and the radio set come
from AliExpress; LW-PLA and the 3S packs do not, for different reasons.

## Software / firmware

None in version 1 — the receiver drives the servos directly.

Version 2 adds a wing leveller: IMU driver and calibration, complementary
filter, roll and pitch PID, a mixer that adds correction to the pilot's
input rather than replacing it, and a hard switch on the transmitter that
returns full manual control. That switch is the entire safety design, and it
gets tested on the ground before it gets tested in the air.

## Plan

- [ ] Read enough aerodynamics to choose a wing section, span and area
- [ ] Model the airframe in Fusion — parametric, so span and chord move
- [ ] Print the wing in LW-PLA, weigh it, check stiffness by hand
- [ ] Fuselage, tail, control surfaces, hinges
- [ ] Fit motor, ESC, servos, receiver; set throws and directions
- [ ] Balance to the design CG on a printed stand, and record the number
- [ ] Range-check the radio on the ground before anything leaves it
- [ ] Glide test with no power, from hand, over grass
- [ ] First powered flight — trim it, land it, write down what it did
- [ ] Fix what the first flight found, print the replacement part
- [ ] Second airframe, applying everything learned
- [ ] Version 2: IMU on board, logging only, no control authority
- [ ] Wing leveller — roll and pitch, with a manual override switch
- [ ] Tune it in the air, and be able to explain each gain

This is the airframe half of the same problem [[custom-flight-controller-drone]]
solves in the air: both need an attitude loop, and this one survives having it
wrong. The radio link, servo signals and PID discipline come from
[[rc-car-custom-controller]], where the same mistakes cost nothing at all.
[[beaglebone-green-case]] is where the parametric CAD workflow was
established — same tool, same export discipline, a much less forgiving part.

## Build log

Session entries live in [[printed-rc-plane-log]].
