#!/usr/bin/env bash
# Render a .kicad_sch to PNG and crop regions of it by millimetre coordinates.
#
# The skill says to iterate on the schematic using image input. This does the
# render once at high DPI, then lets you cut out subcircuits by the same mm
# coordinates that schdump.py reports, so "look at what I just placed at
# x=266 y=123" is one command instead of guessing at pixels.
#
#   schview.sh render board.kicad_sch [outdir] [dpi]   # -> outdir/full.png
#   schview.sh crop   outdir name X0 Y0 W H            # mm -> outdir/name.png
#   schview.sh sheet  outdir [width]                   # whole sheet, downscaled
#
# Requires: kicad-cli, inkscape, ImageMagick.
set -euo pipefail

cmd=${1:?usage: schview.sh render|crop|sheet ...}
shift

case "$cmd" in
render)
  sch=${1:?need a .kicad_sch}; out=${2:-./schview}; dpi=${3:-600}
  mkdir -p "$out"
  kicad-cli sch export svg --no-background-color -o "$out" "$sch" >/dev/null
  svg="$out/$(basename "${sch%.kicad_sch}").svg"
  inkscape --export-type=png --export-dpi="$dpi" --export-background=white \
           --export-filename="$out/full.png" "$svg" >/dev/null 2>&1
  echo "$dpi" > "$out/.dpi"
  identify "$out/full.png"
  ;;
crop)
  out=${1:?need outdir}; name=${2:?need name}
  x=${3:?X0 mm}; y=${4:?Y0 mm}; w=${5:?width mm}; h=${6:?height mm}
  dpi=$(cat "$out/.dpi"); s=$(python3 -c "print($dpi/25.4)")
  px=$(python3 -c "print(int($x*$s))"); py=$(python3 -c "print(int($y*$s))")
  pw=$(python3 -c "print(int($w*$s))"); ph=$(python3 -c "print(int($h*$s))")
  convert "$out/full.png" -crop "${pw}x${ph}+${px}+${py}" +repage \
          -resize 1500x "$out/$name.png"
  identify "$out/$name.png"
  ;;
sheet)
  out=${1:?need outdir}; width=${2:-1900}
  convert "$out/full.png" -resize "${width}x" "$out/sheet.png"
  identify "$out/sheet.png"
  ;;
*)
  echo "unknown command: $cmd" >&2; exit 2
  ;;
esac
