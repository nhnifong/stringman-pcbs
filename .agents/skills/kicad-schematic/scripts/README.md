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

## Gotchas that cost real time

**Split every wire run at each pin it touches.** A single long wire segment
drawn *through* an intermediate pin (even with a junction placed there) can fail
to connect at its far endpoint -- the netlist silently drops the far pin and the
render draws the wire short. Emit one segment per span between consecutive
connection points instead of one long segment.

**Field text angle is added to the symbol rotation.** A field stored at angle 0
on a `rot 90` or `rot 270` symbol renders *vertical*. Store the field at 90 to
get horizontal text on a rotated symbol; that is what KiCad itself writes.

**Pin mapping under rotation and mirroring is worth measuring, not deriving.**
Place the symbol in a scratch copy, run short stub wires to every candidate pin
coordinate with a distinct label on each, export the netlist, and read off which
pin landed where. For `Device`/`Transistor_FET` three-pin parts at `rot 90` with
`(mirror y)`, the result is pin 1 at `(X, Y+5.08)`, pin 2 at `(X+5.08, Y-2.54)`,
pin 3 at `(X-5.08, Y-2.54)`.

**Power symbols take their net name from the Value field**, not the pin name --
the pin is named `~`. Do not invent a `power:MY_RAIL` symbol just to get a new
rail: it is not in any installed library, so ERC reports `lib_symbol_issues` and
"Update Symbols from Library" cannot resolve it. Use a plain label instead.

**Copy a library symbol into `lib_symbols` verbatim, never reconstructed.** When
adding a symbol to a schematic's cache, take the whole `(symbol "Name" ...)`
block from the `.kicad_sym`, rename it to `"Lib:Name"`, and re-indent one level
deeper -- leave the inner `Name_0_1` / `Name_1_1` sub-symbols under their bare
name. Rebuilding the block from a whitelist of property names silently drops
entries such as `(property private "KLC_S3.3" ...)`, which ERC then reports as
`lib_symbol_mismatch`. Symbols that `extends` a parent are the one case needing
real work: the cache must be flattened, so splice in the parent's graphics and
pins while keeping the child's own properties.
