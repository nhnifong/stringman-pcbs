# Helper scripts

Tooling for the read/render/verify loop this skill describes. Everything here is
read-only against the design — edits are still made directly to the
`.kicad_sch` s-expression.

## `schdump.py` — read a schematic as text

Prints placed symbols, wires, junctions and labels with their millimetre
coordinates, optionally filtered to a rectangle.

```bash
schdump.py board.kicad_sch
schdump.py board.kicad_sch --box 125 105 290 140
schdump.py board.kicad_sch --box 125 105 290 140 --what symbols junctions
```

Use it before placing anything: it tells you where the rails already run, which
grid points are free, and which junctions already exist.

## `schview.sh` — render and zoom

```bash
schview.sh render board.kicad_sch out/ 600   # -> out/full.png at 600 dpi
schview.sh crop   out/ buck 234 108 52 28    # x y w h in mm -> out/buck.png
schview.sh sheet  out/                       # whole sheet, downscaled
```

`crop` takes the same millimetre coordinates `schdump.py` prints, so inspecting
a subcircuit you just edited is a direct follow-on from reading it.

Requires `kicad-cli`, `inkscape` and ImageMagick.

## Coordinates

Sheet space is millimetres, x right and **y down**. Library symbol space has y
*up*, so an unrotated symbol at `(X, Y)` puts its library-space pin `(sx, sy)`
at `(X + sx, Y - sy)`.

Rotation is counter-clockwise on screen. A symbol at `rot 270` maps a pin at
library `(-3.81, 0)` — the left-hand pin, and pin 1 on KiCad's two-pin diodes —
to `(X, Y - 3.81)`, i.e. pointing **up**. That is the orientation you want for a
TVS or a diode clamping a positive rail to ground.

Field text angle is *added* to the symbol rotation at render time. A field
stored at angle `0` on a `rot 270` symbol renders vertically; store it at `90`
to get horizontal text back.

## Verifying an edit

```bash
kicad-cli sch erc --exit-code-violations -o erc.rpt board.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o net.net board.kicad_sch
```

Diff the ERC report against one generated from the pre-edit file — an unchanged
violation list is strong evidence you added connectivity without breaking any.
Read the netlist to confirm each new pin landed on the net you intended; a
missing `lib_symbol_mismatch` for a symbol you hand-wrote into `lib_symbols`
confirms your flattened copy matches the real library.
